"""Current: automatic page assessment and selective recovery orchestration.
Limitations: geometry is risk evidence; unavailable recovery preserves p4l.
TODO(B2/B3): measure routing defects and recovery impact against reviewed PDFs.
Acceptance: unavailable recovery, replay adoption and revision-change tests.
"""
from collections import Counter
from .extraction import canonical_revision
from .providers import request
from .reconciliation import tokens, reconcile

def assess(page):
    reasons, checks = [], {}
    plain, md = Counter(tokens(page.get('plain_text', ''))), Counter(tokens(page['markdown']))
    checks['text_layer'] = bool(plain)
    checks['coverage_missing'] = dict(plain - md)
    checks['replacement_characters']=page['markdown'].count('\ufffd')
    if checks['replacement_characters']: reasons.append('UNDECODABLE_CHARACTERS')
    if page.get('extraction_status')=='failed': reasons.append('EXTRACTION_FAILED')
    # Broad missing coverage, not a semantic score. Formatting differences are tolerated.
    if plain and sum((plain-md).values()) > max(20, sum(plain.values()) // 5):
        reasons.append('BROAD_TEXT_COVERAGE_DISAGREEMENT')
    boxes = page.get('blocks')
    checks['reading_order'] = 'available' if boxes is not None else 'unavailable'
    if boxes and any(a[1] > b[1] + 20 for a, b in zip(boxes, boxes[1:])):
        reasons.append('READING_ORDER_RISK')
    tables = page.get('table_count')
    checks['table_preservation'] = 'available' if tables is not None else 'unavailable'
    if tables and '|' not in page['markdown']: reasons.append('TABLE_STRUCTURE_RISK')
    status = 'NEEDS_VISUAL' if reasons else 'ACCEPT'
    if not plain or boxes is None or tables is None:
        status = 'UNVERIFIABLE'; reasons.append('CHECK_EVIDENCE_UNAVAILABLE')
    return {'page': page['page'], 'status': status, 'reasons': reasons,
            'checks': checks, 'meaning': 'ACCEPT means no issue found by available checks'}


def route_pages(pages, document_hash, visual_replays=None, debug_overrides=None):
    original_revision = canonical_revision(pages, document_hash)
    pages = [dict(p) for p in pages]
    assessments, repairs = [], []
    for p in pages:
        a = assess(p); assessments.append(a)
        if a['status'] == 'ACCEPT':
            repairs.append({'page': p['page'], 'status': 'skipped', 'reason': 'ACCEPT', 'adopted_source': 'p4l'}); continue
        payload = {'document_hash': document_hash, 'page': p['page'], 'revision': original_revision, 'markdown': p['markdown']}
        result = request('visual', payload, (visual_replays or {}).get(p['page']))
        result['page'], result['adopted_source'] = p['page'], 'p4l'
        if result['status'] == 'returned':
            response = result['response']
            if not isinstance(response, dict) or not isinstance(response.get('markdown'), str):
                result['status'] = 'rejected'; result['reason'] = 'Invalid repair response'
            else:
                comparison = reconcile(p['markdown'], response['markdown'], response.get('synthetic_order_only') is True and document_hash == 'synthetic')
                result['reconciliation'] = comparison
                if comparison['adopted']:
                    p['markdown'] = response['markdown']; result['adopted_source'] = 'synthetic_replay'
        repairs.append(result)
    override_records = []
    for p in pages:
        if p['page'] in (debug_overrides or {}):
            proposed = debug_overrides[p['page']]
            comparison = reconcile(p['markdown'], proposed)
            override_records.append({'page':p['page'], 'origin':'manual_debug_override',
                                     'reconciliation':comparison, 'automatic_adoption':False,
                                     'reason':'Explicit user debug acceptance; not verified extraction'})
            p['markdown'] = proposed
    revision = canonical_revision(pages, document_hash)
    return pages, assessments, repairs, override_records, original_revision, revision
