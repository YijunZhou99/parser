"""
PDF（含扫描件）-> 章节树，骨架优先。

流程：
    PDF -> 逐页 markdown（扫描页走 OCR）-> 固定行号
        -> 标噪音（页眉页脚、TOC）-> 抽候选标题行
        -> 规则定层级，剩下的交给 LLM（只输出层级，不碰正文）
        -> 本地按行号切回正文 -> 组树 -> 校验

正文永远是本地按行号从原文切出来的，模型没有机会改写它。

用法：
    python pdf_tree.py doc.pdf --no-llm --outline      # 先看纯规则能到什么程度
    python pdf_tree.py doc.pdf --md-only               # 只看 markdown
    python pdf_tree.py doc.pdf --base-url http://localhost:8000/v1 \
                               --model llama-3.3-70b --out tree.json

依赖：
    pip install pymupdf4llm pytesseract openai pydantic
    OCR 还需要系统装 tesseract
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import fitz
import pymupdf4llm
from pydantic import BaseModel, Field

OCR_TEXT_THRESHOLD = 50       # 一页可提取字符少于这个数就当扫描页
OCR_DPI = 300
HEADER_PAGE_RATIO = 0.6       # 出现在六成以上页面的重复行判为页眉页脚
LLM_BATCH = 60                # 每次给模型多少个候选行
MAX_DEPTH = 6


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

class Node(BaseModel):
    id: str
    label: str
    title: str
    text: str
    depth: int = 0
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    from_ocr: bool = False
    children: List["Node"] = Field(default_factory=list)


class Flag(BaseModel):
    rule: str
    severity: str
    node_id: Optional[str] = None
    detail: str


class ParsedDocument(BaseModel):
    root: Node
    flags: List[Flag] = Field(default_factory=list)


Node.model_rebuild()


@dataclass
class Line:
    idx: int                  # 全局行号，一旦定下来就不能变
    text: str
    page: int
    from_ocr: bool = False
    noise: Optional[str] = None     # "header" | "toc" | "pageno"


@dataclass
class Candidate:
    line_idx: int
    text: str                 # 去掉编号和 markdown 井号后的标题
    label: str
    level: Optional[int]      # 规则能定就填，定不了留 None 给模型
    source: str               # "number" | "md" | "bold"


# ---------------------------------------------------------------------------
# 1. 读入：逐页 markdown，扫描页走 OCR
# ---------------------------------------------------------------------------

def page_needs_ocr(page: fitz.Page) -> bool:
    return len(page.get_text().strip()) < OCR_TEXT_THRESHOLD


def ocr_page(page: fitz.Page) -> str:
    """扫描页只能拿到纯文本，没有字号信息，层级只能靠编号推。"""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        raise RuntimeError("扫描页需要 pytesseract 和 Pillow：pip install pytesseract pillow")
    import io

    pix = page.get_pixmap(dpi=OCR_DPI)
    image = Image.open(io.BytesIO(pix.tobytes("png")))
    return pytesseract.image_to_string(image, config="--psm 1")


def load_pages(path: str) -> List[Tuple[int, str, bool]]:
    """返回 [(页码, markdown 或 OCR 文本, 是否 OCR)]。"""
    document = fitz.open(path)
    scanned = {i for i, page in enumerate(document) if page_needs_ocr(page)}

    digital: Dict[int, str] = {}
    if len(scanned) < document.page_count:
        chunks = pymupdf4llm.to_markdown(path, page_chunks=True)
        for chunk in chunks:
            number = chunk["metadata"].get("page_number")
            if number is None:
                continue
            digital[number - 1] = chunk["text"]

    pages: List[Tuple[int, str, bool]] = []
    for index in range(document.page_count):
        if index in scanned:
            pages.append((index + 1, ocr_page(document[index]), True))
        else:
            pages.append((index + 1, digital.get(index, ""), False))
    document.close()
    return pages


def build_lines(pages: List[Tuple[int, str, bool]]) -> List[Line]:
    """
    行号在这里一次性固定。后面所有清洗只允许"标记"，不允许删行，
    否则按行号切正文会整体错位。
    """
    lines: List[Line] = []
    for page_no, text, from_ocr in pages:
        for raw in text.split("\n"):
            stripped = raw.strip()
            if not stripped:
                continue
            lines.append(Line(idx=len(lines), text=stripped, page=page_no, from_ocr=from_ocr))
    return lines


# ---------------------------------------------------------------------------
# 2. 标噪音：页眉页脚、页码、目录
# ---------------------------------------------------------------------------

PAGENO_RE = re.compile(r"^(page\s+)?\d+(\s*/\s*\d+)?$", re.IGNORECASE)
DOT_LEADER_RE = re.compile(r"\.{3,}\s*\d+\s*$")
TRAILING_PAGENO_RE = re.compile(r"\S\s{2,}\d{1,4}\s*$")
TOC_TITLE_RE = re.compile(r"^(table of contents|contents|目\s*录)\s*$", re.IGNORECASE)


def _normalize_for_repeat(text: str) -> str:
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", text)).strip().lower()


def mark_noise(lines: List[Line], page_count: int) -> None:
    for line in lines:
        if PAGENO_RE.match(line.text):
            line.noise = "pageno"

    if page_count >= 3:
        pages_seen: Dict[str, set] = defaultdict(set)
        for line in lines:
            if line.noise:
                continue
            pages_seen[_normalize_for_repeat(line.text)].add(line.page)
        threshold = max(2, int(page_count * HEADER_PAGE_RATIO))
        repeated = {key for key, pgs in pages_seen.items() if len(pgs) >= threshold}
        for line in lines:
            if not line.noise and _normalize_for_repeat(line.text) in repeated:
                line.noise = "header"

    mark_toc(lines)


def mark_toc(lines: List[Line]) -> None:
    """
    目录和正文标题序列长得一模一样，不剔掉会多出一棵幽灵树。
    判据：带点引导线或行尾孤立页码，且连续出现三行以上。
    """
    run: List[int] = []

    def flush() -> None:
        if len(run) >= 3:
            for idx in run:
                lines[idx].noise = "toc"
            # 连同上面那行"目录 / Table of Contents"一起摘掉，
            # 否则它会变成首个标题之前的孤儿正文。
            for back in range(run[0] - 1, max(-1, run[0] - 4), -1):
                if lines[back].noise:
                    continue
                if TOC_TITLE_RE.match(strip_markdown(lines[back].text)):
                    lines[back].noise = "toc"
                break
        run.clear()

    for position, line in enumerate(lines):
        if line.noise:
            flush()
            continue
        looks_toc = bool(DOT_LEADER_RE.search(line.text) or TRAILING_PAGENO_RE.search(line.text))
        if looks_toc:
            run.append(position)
        else:
            flush()
    flush()


# ---------------------------------------------------------------------------
# 3. 抽候选标题行
# ---------------------------------------------------------------------------

MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
BOLD_ONLY_RE = re.compile(r"^\*\*(.+?)\*\*[\s:：]*$")

NUMBER_PATTERNS = [
    (re.compile(r"^(\d+(?:\.\d+)+)\.?\s+(?=\S)"), None),           # 1.2 / 1.2.3，层级看点数
    (re.compile(r"^(\d+)\.\s+(?=\S)"), 1),
    (re.compile(r"^(?:Section|SECTION|第)\s*(\d+(?:\.\d+)*)\s*[条节章]?\s*(?=\S)"), None),
    (re.compile(r"^(?:Article|ARTICLE)\s+([IVXLC]+|\d+)\s*\.?\s+(?=\S)"), 1),
    (re.compile(r"^(\([a-z]\))\s*(?=\S)"), None),
    (re.compile(r"^(\([ivx]+\))\s*(?=\S)"), None),
    (re.compile(r"^(\(\d+\))\s*(?=\S)"), None),
    (re.compile(r"^([A-Z])\.\s+(?=\S)"), None),
]


def strip_markdown(text: str) -> str:
    text = re.sub(r"^#{1,6}\s+", "", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    return text.strip()


def parse_label(text: str) -> Tuple[str, str, Optional[int]]:
    """返回 (编号, 去掉编号的标题, 规则推出的层级或 None)。"""
    for pattern, fixed_level in NUMBER_PATTERNS:
        match = pattern.match(text)
        if not match:
            continue
        label = match.group(1).rstrip(".")
        rest = text[match.end():].strip()
        if fixed_level is not None:
            return label, rest, fixed_level
        if re.fullmatch(r"\d+(\.\d+)*", label):
            return label, rest, label.count(".") + 1
        return label, rest, None      # (a) 这类是相对编号，层级看它挂在谁下面
    return "", text, None


def find_candidates(lines: List[Line]) -> List[Candidate]:
    """
    召回宁滥勿缺：漏一个候选等于永久丢一节，多给几个只是让模型说"不是标题"。
    """
    candidates: List[Candidate] = []
    for line in lines:
        if line.noise:
            continue

        md = MD_HEADING_RE.match(line.text)
        bold = BOLD_ONLY_RE.match(line.text)
        body = strip_markdown(line.text)
        label, title, level = parse_label(body)

        if md:
            # 有编号但层级要看上下文的（(a)、(i) 这类相对编号）一律留 None，
            # 不要拿 markdown 的井号个数顶上：pymupdf4llm 是按字号猜的，
            # 同级的 (a) 和 (b) 常常拿到不同井号数，直接用会把兄弟变成父子。
            if label:
                md_level = level
            else:
                md_level = len(md.group(1))
            candidates.append(Candidate(line.idx, title or strip_markdown(md.group(2)),
                                        label, md_level, "md"))
        elif label:
            candidates.append(Candidate(line.idx, title, label, level, "number"))
        elif bold and len(body) <= 80 and not body.endswith((".", "。")):
            candidates.append(Candidate(line.idx, body, "", None, "bold"))
    return candidates


# ---------------------------------------------------------------------------
# 4. 规则定不了的交给 LLM（只判层级，不碰正文）
# ---------------------------------------------------------------------------

SYSTEM = "你是文档结构分析器。只输出 JSON，不要任何解释。"

USER_TEMPLATE = """下面是一份政策文档里抽出来的候选标题行，每行带行号。
判断每一行是不是真正的章节标题，如果是，它是第几级（1 为最顶层）。

规则：
- 编号 1. 是 1 级，1.1 是 2 级，1.1.1 是 3 级，(a)(b) 通常是它上面那个编号的下一级。
- 没有编号但明显是标题的（比如"目的"、"适用范围"、"定义"），也算标题，层级按上下文判断。
- 正文段落、列表项、表格行不是标题，is_heading 填 false。
- 只输出下面这个 JSON 结构，数组长度必须和输入行数一致。

{{"decisions": [{{"line": 行号, "is_heading": true/false, "level": 层级数字}}]}}

候选行：
{items}"""


def llm_assign_levels(candidates: List[Candidate], base_url: str, model: str,
                      api_key: str, verbose: bool = False) -> Dict[int, Optional[int]]:
    """
    输出是扁平列表，不是嵌套树。
    嵌套结构对中小模型来说额外负担大，而且一处括号错会污染整棵子树；
    扁平列表错一行就只错一行，嵌套关系交给本地栈循环。
    """
    from openai import OpenAI

    client = OpenAI(base_url=base_url, api_key=api_key or "none")
    schema = {
        "type": "object",
        "properties": {
            "decisions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "line": {"type": "integer"},
                        "is_heading": {"type": "boolean"},
                        "level": {"type": "integer", "minimum": 1, "maximum": MAX_DEPTH},
                    },
                    "required": ["line", "is_heading", "level"],
                },
            }
        },
        "required": ["decisions"],
    }

    result: Dict[int, Optional[int]] = {}
    for start in range(0, len(candidates), LLM_BATCH):
        batch = candidates[start:start + LLM_BATCH]
        items = "\n".join(
            f"{c.line_idx}: {c.label + ' ' if c.label else ''}{c.text}" for c in batch
        )
        payload = USER_TEMPLATE.format(items=items)

        content = _chat(client, model, payload, schema)
        if verbose:
            print(f"[llm] 第 {start // LLM_BATCH + 1} 批，{len(batch)} 行", file=sys.stderr)

        for item in _extract_decisions(content):
            line = item.get("line")
            if not isinstance(line, int):
                continue
            result[line] = int(item["level"]) if item.get("is_heading") else None
    return result


def _chat(client, model: str, payload: str, schema: dict) -> str:
    """
    优先用约束解码。开源模型在这条路上最大的失败来源不是判断错，
    是 JSON 格式坏掉；约束解码直接消灭这类错误。
    vLLM 走 extra_body.guided_json，不支持就退回普通 json 模式。
    """
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": payload}]
    for kwargs in (
        {"extra_body": {"guided_json": schema}},
        {"response_format": {"type": "json_object"}},
        {},
    ):
        try:
            response = client.chat.completions.create(
                model=model, messages=messages, temperature=0, max_tokens=4096, **kwargs
            )
            return response.choices[0].message.content or ""
        except Exception:
            continue
    return ""


def _extract_decisions(content: str) -> List[dict]:
    if not content:
        return []
    match = re.search(r"\{.*\}", content, re.S)
    if not match:
        return []
    try:
        return json.loads(match.group(0)).get("decisions") or []
    except json.JSONDecodeError:
        return []


# ---------------------------------------------------------------------------
# 5. 定稿层级
# ---------------------------------------------------------------------------

def resolve_levels(candidates: List[Candidate],
                   llm_levels: Optional[Dict[int, Optional[int]]]) -> List[Candidate]:
    """规则优先，规则定不了才看模型；相对编号 (a) 挂在上一个绝对编号下面。"""
    resolved: List[Candidate] = []
    last_absolute = 0

    for candidate in candidates:
        level = candidate.level

        if level is None and llm_levels is not None and candidate.line_idx in llm_levels:
            level = llm_levels[candidate.line_idx]
            if level is None:
                continue                       # 模型说这不是标题

        if level is None:
            if candidate.label:                # (a) / (i) 这类相对编号
                level = last_absolute + 1
            elif candidate.source == "bold":
                continue                       # 没编号又没模型背书，不收
            else:
                level = last_absolute + 1

        level = max(1, min(MAX_DEPTH, level))
        if re.fullmatch(r"\d+(\.\d+)*", candidate.label):
            last_absolute = level
        candidate.level = level
        resolved.append(candidate)

    previous = 0
    for candidate in resolved:                  # 夹住跳级，否则栈循环会挂
        if candidate.level > previous + 1:
            candidate.level = previous + 1
        previous = candidate.level
    return resolved


# ---------------------------------------------------------------------------
# 6. 本地按行号切回正文，组树
# ---------------------------------------------------------------------------

@dataclass
class _Building:
    id: str
    label: str
    title: str
    level: int
    path: str
    line_start: int
    line_end: int = 0
    body: List[Line] = field(default_factory=list)
    children: List["_Building"] = field(default_factory=list)


def resolve_path(parent_path: str, label: str, fallback: int) -> str:
    label = label.strip().strip(".")
    if not label:
        return f"{parent_path}.n{fallback}" if parent_path else f"n{fallback}"
    if "." in label or (parent_path and label.startswith(parent_path + ".")):
        return label
    return f"{parent_path}.{label}" if parent_path else label


def make_id(path: str, title: str) -> str:
    digest = hashlib.sha1(" ".join(title.lower().split()).encode()).hexdigest()[:6]
    return f"{path}-{digest}"


def assemble(lines: List[Line], candidates: List[Candidate], doc_title: str) -> Node:
    heading_at = {c.line_idx: c for c in candidates}
    root = _Building(id="root", label="", title=doc_title, level=0, path="",
                     line_start=0)
    stack = [root]
    counter = 0

    for line in lines:
        if line.noise:
            continue
        candidate = heading_at.get(line.idx)
        if candidate is None:
            stack[-1].body.append(line)
            continue

        while len(stack) > 1 and stack[-1].level >= candidate.level:
            stack.pop()

        counter += 1
        path = resolve_path(stack[-1].path, candidate.label, counter)
        node = _Building(
            id=make_id(path, candidate.text),
            label=candidate.label,
            title=candidate.text,
            level=candidate.level,
            path=path,
            line_start=line.idx,
        )
        stack[-1].children.append(node)
        stack.append(node)

    return _finalize(root, 0)


def _finalize(building: _Building, depth: int) -> Node:
    body_lines = building.body
    covered = [building.line_start] + [ln.idx for ln in body_lines]
    pages = [ln.page for ln in body_lines]
    return Node(
        id=building.id,
        label=building.label,
        title=building.title,
        text="\n".join(ln.text for ln in body_lines).strip(),
        depth=depth,
        page_start=min(pages) if pages else None,
        page_end=max(pages) if pages else None,
        line_start=building.line_start,
        line_end=max(covered),
        from_ocr=any(ln.from_ocr for ln in body_lines),
        children=[_finalize(c, depth + 1) for c in building.children],
    )


# ---------------------------------------------------------------------------
# 7. 校验：把"解析对不对"从人工判断变成机器检查
# ---------------------------------------------------------------------------

def validate(root: Node) -> List[Flag]:
    flags: List[Flag] = []

    if not root.children:
        flags.append(Flag(rule="no_headings", severity="error",
                          detail="一个标题都没识别出来，先看 --md-only 的输出"))
    if root.text:
        flags.append(Flag(rule="orphan_body", severity="warning", node_id="root",
                          detail=f"首个标题之前有 {len(root.text)} 字正文"))

    def walk(node: Node) -> None:
        labels = [c.label for c in node.children if re.fullmatch(r"\d+(\.\d+)*", c.label)]
        numbers = []
        for label in labels:
            try:
                numbers.append(int(label.split(".")[-1]))
            except ValueError:
                pass
        for previous, current in zip(numbers, numbers[1:]):
            if current != previous + 1:
                flags.append(Flag(rule="numbering_gap", severity="error", node_id=node.id,
                                  detail=f"{node.title or '根'} 下编号从 {previous} 跳到 {current}"))

        seen = Counter(c.label for c in node.children if c.label)
        for label, count in seen.items():
            if count > 1:
                flags.append(Flag(rule="duplicate_label", severity="warning", node_id=node.id,
                                  detail=f"编号 {label} 在同一层出现 {count} 次"))

        for child in node.children:
            if not child.text and not child.children:
                flags.append(Flag(rule="empty_section", severity="warning", node_id=child.id,
                                  detail=f"{child.label} {child.title} 没有正文也没有子节"))
            if child.from_ocr:
                flags.append(Flag(rule="ocr_derived", severity="warning", node_id=child.id,
                                  detail="内容来自 OCR，必须人工复核"))
            walk(child)

    walk(root)
    return flags


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def parse_pdf(path: str, use_llm: bool, base_url: str, model: str,
              api_key: str, verbose: bool = False) -> ParsedDocument:
    pages = load_pages(path)
    lines = build_lines(pages)
    if not lines:
        raise RuntimeError("没提取到任何文字")

    mark_noise(lines, page_count=len(pages))
    candidates = find_candidates(lines)

    llm_levels = None
    if use_llm:
        pending = [c for c in candidates if c.level is None]
        if verbose:
            print(f"[规则] {len(candidates)} 个候选，其中 {len(pending)} 个需要模型判断",
                  file=sys.stderr)
        if pending:
            llm_levels = llm_assign_levels(pending, base_url, model, api_key, verbose)

    candidates = resolve_levels(candidates, llm_levels)

    # 文档第一行通常是标题本身。它既当根标题又当一级节点的话会重复一份，
    # 所以认出来就从候选里摘掉。
    first = next((ln for ln in lines if not ln.noise), None)
    title = os.path.basename(path)
    if first is not None:
        title = strip_markdown(first.text)
        if candidates and candidates[0].line_idx == first.idx and not candidates[0].label:
            title = candidates[0].text
            candidates = candidates[1:]
            first.noise = "title"      # 标记而不是删行，行号必须保持不变

    root = assemble(lines, candidates, title)
    return ParsedDocument(root=root, flags=validate(root))


def print_outline(node: Node, indent: int = 0) -> None:
    head = f"{node.label} {node.title}".strip()
    where = f"p{node.page_start}" if node.page_start else "-"
    mark = " [OCR]" if node.from_ocr else ""
    print(f"{'  ' * indent}{head}  [d{node.depth}, {len(node.text)}字, {where}]{mark}")
    for child in node.children:
        print_outline(child, indent + 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="PDF 转章节树")
    parser.add_argument("path")
    parser.add_argument("--out")
    parser.add_argument("--outline", action="store_true", help="打印大纲而不是 JSON")
    parser.add_argument("--md-only", action="store_true", help="只输出带行号的 markdown")
    parser.add_argument("--no-llm", action="store_true", help="纯规则，不调模型")
    parser.add_argument("--base-url", default=os.environ.get("LLM_BASE_URL",
                                                             "http://localhost:8000/v1"))
    parser.add_argument("--model", default=os.environ.get("LLM_MODEL", "llama-3.3-70b"))
    parser.add_argument("--api-key", default=os.environ.get("LLM_API_KEY", "none"))
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    if args.md_only:
        for line in build_lines(load_pages(args.path)):
            print(f"{line.idx:5d} p{line.page} {'OCR ' if line.from_ocr else ''}| {line.text}")
        return

    parsed = parse_pdf(args.path, not args.no_llm, args.base_url, args.model,
                       args.api_key, args.verbose)

    for flag in parsed.flags:
        print(f"[{flag.severity}] {flag.rule}: {flag.detail}", file=sys.stderr)

    if args.outline:
        print_outline(parsed.root)
        return

    payload = parsed.model_dump_json(indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(payload)
        print(f"已写入 {args.out}")
    else:
        print(payload)


if __name__ == "__main__":
    main()
