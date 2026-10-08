"""Current: strict tree checks, source accounting and reference text consistency.
Limitations: conservation does not certify extraction or ownership accuracy.
TODO(B9): validate scope and source accounting against reviewed PDF alignments.
Acceptance: schema, duplicate IDs/depths and nonoverlapping source coverage tests.
"""
from collections import Counter
from .models import nodes
from .reconciliation import tokens

def validate_tree(data):
    errors, seen = [], set()
    if not isinstance(data, dict) or set(data) != {'root'}:
        return ['Expected exactly {root}']
    def walk(n, depth):
        if not isinstance(n, dict):
            errors.append('Node must be an object'); return
        if set(n) != {'id', 'label', 'title', 'text', 'depth', 'children'}:
            errors.append('Unexpected/missing node fields')
        for field in ('id', 'label', 'title', 'text'):
            if not isinstance(n.get(field), str): errors.append(f'{field} must be string')
        ident = n.get('id')
        if not isinstance(ident, str) or not ident or ident in seen:
            errors.append('Empty, invalid or duplicate ID')
        if isinstance(ident, str): seen.add(ident)
        if type(n.get('depth')) is not int or n.get('depth') != depth:
            errors.append(f'Invalid depth at {ident}')
        if not isinstance(n.get('children'), list):
            errors.append('children must be array'); return
        for c in n['children']: walk(c, depth + 1)
    walk(data['root'], 0)
    return errors




def text_consistency(tree, source):
    actual = Counter(tokens('\n'.join(' '.join([n['label'], n['title'], n['text']]) for n in nodes(tree))))
    expected = Counter(tokens(source))
    return {'missing_tokens': dict(expected - actual), 'added_tokens': dict(actual - expected),
            'meaning': 'Basic token accounting only; no human review or layout verification'}




def validate_run(tree, pages, body, decisions, hierarchy_errors, pending, revision=None):
    errors = list(hierarchy_errors)
    by_page={p['page']:p for p in pages}
    by_node={n['id']:n for n in nodes(tree)}
    assigned={ident:[] for ident in by_node}
    for item in body:
        owner=item['owner']
        if owner not in by_node: errors.append({'reason':'UNKNOWN_BODY_OWNER','id':owner})
        for span in item['ranges']:
            page=by_page.get(span['page'])
            if page is None or type(span['start']) is not int or type(span['end']) is not int or not 0<=span['start']<span['end']<=len(page['markdown']):
                errors.append({'reason':'INVALID_SOURCE_SPAN','span':span}); continue
            if revision is not None and span['revision']!=revision:
                errors.append({'reason':'STALE_SOURCE_REVISION','span':span})
            if item['text']!=page['markdown'][span['start']:span['end']]:
                errors.append({'reason':'SOURCE_TEXT_MISMATCH','span':span})
        if item['status']=='ASSIGNED' and owner in assigned: assigned[owner].append(item['text'])
    for ident,parts in assigned.items():
        if ''.join(parts)!=by_node[ident]['text']: errors.append({'reason':'OWN_TEXT_MISMATCH','id':ident})
    accounting = []
    for p in pages:
        spans = [b['ranges'][0] for b in body if b['ranges'][0]['page']==p['page']]
        spans.sort(key=lambda s:s['start']); cursor = 0
        for s in spans:
            if s['start'] != cursor: errors.append({'page': p['page'], 'reason': 'GAP_OR_DUPLICATE_ASSIGNMENT'})
            cursor = s['end']
        if cursor != len(p['markdown']): errors.append({'page': p['page'], 'reason': 'UNCOVERED_TEXT'})
        accounting.append({'page': p['page'], 'covered_characters': cursor, 'canonical_characters': len(p['markdown'])})
    schema_errors=validate_tree(tree)
    extraction_failures=[p['page'] for p in pages if p.get('extraction_status')=='failed']
    return {'schema_errors': schema_errors, 'source_errors': errors,
                        'accounting': accounting, 'pending': [d for d in decisions if d['status']=='AMBIGUOUS'],
                        'outstanding_ownership': [b['ranges'] for b in body if b['ownership']=='provisional'],
                        'complete': not schema_errors and not errors and not extraction_failures and not any(d['status']=='AMBIGUOUS' for d in decisions) and not pending,
                        'extraction_failures':extraction_failures,
                        'body_verified': False, 'scope_closure': 'Next accepted heading changes active owner; enclosing resumption unsupported'}
