"""Current: minimal shared dictionary contracts matching inspectable JSON outputs.
Limitations: typing is static; reference/runtime invariants are validated separately.
TODO(B1): extend contracts with confirmed source alignment when reviewed data exists.
Acceptance: existing annotator schema and stage integration checks.
"""
from typing import TypedDict, Any


class SourceRange(TypedDict):
    revision: str
    page: int
    start: int
    end: int


class PageExtraction(TypedDict, total=False):
    document_hash: str
    page: int
    markdown: str
    source_engine: str
    plain_text: str
    blocks: list[list[float]]
    width: float
    table_count: int | None
    table_check_error: str | None
    extraction_status: str
    extraction_error: str | None


class Candidate(TypedDict):
    id: str
    original_text: str
    label: str
    title: str
    markdown_level: int | None
    page: int
    ranges: list[SourceRange]
    signals: list[str]
    label_grammar: str


class Evidence(TypedDict):
    candidate_id: str
    signals: list[str]
    numeric_level: int | None
    markdown_level: int | None
    possible_parents: list[str]
    support: list[str]
    conflicts: list[str]
    label_interpretations: list[dict[str, Any]]
    selected_label: dict[str, Any] | None
    sequence_peers: list[str]


class Decision(TypedDict):
    candidate_id: str
    role: str
    parent_id: str | None
    status: str
    role_uncertain: bool
    parent_uncertain: bool
    reasons: list[str]
    origin: str


class OutlineNode(TypedDict):
    id: str
    label: str
    title: str
    text: str
    depth: int
    children: list['OutlineNode']


class DocumentData(TypedDict):
    root: OutlineNode


class RunResult(TypedDict):
    document_hash: str
    canonical_revision: str
    original_revision: str
    pages: list[PageExtraction]
    assessments: list[dict[str, Any]]
    repairs: list[dict[str, Any]]
    debug_overrides: list[dict[str, Any]]
    candidates: list[Candidate]
    evidence: list[Evidence]
    regions: list[dict[str, Any]]
    decisions: list[Decision]
    structure_provider: list[dict[str, Any]]
    section_index: list[Decision]
    tree: DocumentData
    body: list[dict[str, Any]]
    validation: dict[str, Any]
    timings: dict[str, float]
    limitations: list[str]


def nodes(tree: DocumentData) -> list[OutlineNode]:
    def walk(node):
        yield node
        for child in node['children']:
            yield from walk(child)
    return list(walk(tree['root']))
