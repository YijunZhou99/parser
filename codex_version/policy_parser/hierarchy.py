"""Current: builds a global tree from accepted parent relationships.
Limitations: unknown and later parents remain outstanding; no global LLM.
TODO(B8): improve global consistency before adding any model architecture.
Acceptance: parent existence/order and exported tree invariants.
"""


def assemble_hierarchy(candidates, decisions):
    root = {'id': 'root', 'label': '', 'title': '', 'text': '', 'depth': 0, 'children': []}
    byid, created, pending = {c['id']: c for c in candidates}, {'root': root}, []
    errors = []
    accepted = [d for d in decisions if d['status'] == 'RESOLVED' and d['role'] == 'section']
    edges={d['candidate_id']:d['parent_id'] for d in accepted}
    cycles=set()
    for ident in edges:
        chain=set(); current=ident
        while current in edges:
            if current in chain: cycles.update(chain); break
            chain.add(current); current=edges[current]
    seen=set()
    for d in accepted:
        ident=d['candidate_id']
        if ident not in byid or ident in seen or ident in cycles or ident=='root':
            reason='CYCLE' if ident in cycles else 'UNKNOWN_OR_DUPLICATE_SECTION_ID'
            errors.append({'id':ident,'reason':reason}); pending.append(ident); continue
        seen.add(ident)
        c = byid[d['candidate_id']]; parent = created.get(d['parent_id'])
        if parent is None:
            errors.append({'id': c['id'], 'reason': 'MISSING_OR_LATER_PARENT'}); pending.append(c['id']); continue
        n = {'id': c['id'], 'label': c['label'], 'title': c['title'], 'text': '',
             'depth': parent['depth']+1, 'children': []}
        parent['children'].append(n); created[c['id']] = n
    return {'root': root}, created, errors, pending
