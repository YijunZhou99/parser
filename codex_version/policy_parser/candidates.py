"""Current: source candidates, trailing footnote parsing and repeated edge-block signals.
Limitations: exact unformatted edge repetition requires three pages; no noise deletion.
TODO(B4): improve segmentation using reviewed misses.
Acceptance: candidate determinism and source-span tests.
"""
import re
from .extraction import sha
from .labels import match_label, label_grammar
from .models import Candidate, PageExtraction
from collections import defaultdict


def block_spans(markdown):
    """Separate explicit headings from adjacent prose without inventing source text."""
    fenced=[(m.start(),m.end()) for m in re.finditer(r'(?ms)^(```|~~~)[^\n]*\n.*?^\1[^\n]*',markdown)]
    def emit(start,end):
        value=markdown[start:end]
        left=len(value)-len(value.lstrip()); right=len(value.rstrip())
        if right>left: return (start+left,start+right)
        return None
    for block in re.finditer(r'\S[^\n]*(?:\n(?!\s*\n)[^\n]+)*',markdown):
        headings=[m for m in re.finditer(r'(?m)^#{1,6}\s+[^\n]+',block.group())
                  if not any(lo<=block.start()+m.start()<hi for lo,hi in fenced)]
        cursor=block.start()
        for heading in headings:
            start=block.start()+heading.start()
            if start<cursor: continue
            preceding=emit(cursor,start)
            if preceding: yield preceding
            end=block.start()+heading.end()
            # Only a visibly unfinished bold heading can consume continuation lines.
            if heading.group().count('**')%2:
                tail=markdown[end:block.end()]
                continuation=re.match(r'\n(?!#)[^\n]*\*\*',tail)
                if continuation and len(heading.group()+continuation.group())<=180:
                    end+=continuation.end()
            span=emit(start,end)
            if span: yield span
            cursor=end
        trailing=emit(cursor,block.end())
        if trailing: yield trailing

def candidate_blocks(pages: list[PageExtraction], revision: str) -> list[Candidate]:
    result = []
    margins = defaultdict(set)
    for page in pages:
        spans = list(block_spans(page['markdown']))
        for position, span in [('first', spans[0] if spans else None),
                               ('last', spans[-1] if spans else None)]:
            if span:
                raw = page['markdown'][span[0]:span[1]]
                margins[(position, raw)].add(page['page'])
    for page in pages:
        md = page['markdown']
        spans = list(block_spans(md))
        for start,end in spans:
            raw = md[start:end]
            level = len(re.match(r'^#+', raw).group()) if raw.startswith('#') else None
            clean = re.sub(r'^#{1,6}\s+', '', raw)
            # Parse the visible heading independently of trailing footnote markup.
            # The original text and spans retain the marker verbatim.
            if level:
                clean = re.sub(r'(?:\s*<sup\b[^>]*>.*?</sup>)+\s*$', '', clean,
                               flags=re.IGNORECASE | re.DOTALL)
            bold = clean.startswith('**') and clean.endswith('**')
            if bold: clean = clean[2:-2]
            clean = clean.strip()
            numbered = match_label(clean)
            signals = []
            if level: signals.append('markdown_heading')
            if numbered and len(clean) < 180: signals.append('numbered_title_like')
            if bold and len(clean) < 180: signals.append('standalone_bold')
            if clean.isupper() and len(clean) < 100: signals.append('uppercase')
            if len(clean) < 100 and len(clean.splitlines()) <= 2 and not clean.endswith(('.', ':', ';')):
                signals.append('isolated_short_block')
            if not signals: continue
            table=bool(re.search(r'(?m)^[ \t]*\|?[ \t]*:?-{3,}:?[ \t]*(?:\|[ \t]*:?-{3,}:?[ \t]*)+\|?[ \t]*$',raw))
            if raw.lstrip().startswith(('>', '- ', '* ', '+ ', '```', '~~~')) or table:
                signals.append('body_markup')
            if not level and not numbered and re.fullmatch(r'\d+', clean): signals.append('bare_number')
            if not level and not numbered and not bold and len(raw) <= 180:
                edge = 'first' if (start,end) == spans[0] else 'last' if (start,end) == spans[-1] else None
                if edge and len(margins[(edge,raw)]) >= 3:
                    signals.append('repeated_page_margin')
            label, title = (numbered.group(1), numbered.group(2)) if numbered else ('', clean)
            following = md[end:]
            if not following.strip():
                next_page = next((p for p in pages if p['page']>page['page']),None)
                following = next_page['markdown'] if next_page else ''
            first_block = re.split(r'\n\s*\n', following.lstrip(), maxsplit=1)[0]
            if (len(first_block.split())>=12 and not first_block.startswith(('#','>','- ','* '))
                    and not match_label(first_block) and not first_block.startswith('**')):
                signals.append('following_prose')
            ident = 'c-' + sha(f'{revision}:{page["page"]}:{start}:{end}'.encode())[:16]
            result.append({'id': ident, 'original_text': raw, 'label': label, 'title': title,
                           'markdown_level': level, 'page': page['page'],
                           'ranges': [{'revision': revision, 'page': page['page'],
                                       'start': start, 'end': end}],
                           'signals': signals,
                           'label_grammar': label_grammar(label)})
    return result
