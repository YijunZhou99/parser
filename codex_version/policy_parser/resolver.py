"""Current: deterministic role/parent decisions and atomic provider decision application.
Limitations: sequence nesting assumptions need review; live provider unavailable.
TODO(B5/B7): improve contextual deterministic evidence, then live resolution.
Acceptance: uncertain-role, valid/invalid replay, IDs/cycles and fingerprint tests.
"""
from .evidence import build_evidence
from .providers import request
from copy import deepcopy
from .regions import input_characters

def validate_response(response, allowed, anchors, existing):
    if not isinstance(response, list): return ['Response must be a decision array']
    errors, seen, edges = [], set(), dict(existing)
    for item in response:
        if not isinstance(item, dict): errors.append('Invalid decision'); continue
        ident, parent = item.get('candidate_id'), item.get('parent_id')
        if not isinstance(ident, str) or (parent is not None and not isinstance(parent,str)):
            errors.append('Candidate and parent IDs must be strings'); continue
        if ident not in allowed or ident in seen: errors.append('Unknown/duplicate candidate ID')
        seen.add(ident)
        if item.get('role') not in ('section', 'body', 'abstain'): errors.append('Invalid role')
        if item.get('role') == 'section':
            if parent not in set(allowed) | set(anchors) | {'root'}: errors.append('Inadmissible parent')
            edges[ident] = parent
    for ident in edges:
        chain, current = set(), ident
        while current in edges:
            if current in chain: errors.append('Cycle'); break
            chain.add(current); current = edges[current]
    return sorted(set(errors))


def decide(candidates, evidence=None):
    decisions, stack = [], []
    evidence = deepcopy(build_evidence(candidates) if evidence is None else evidence)
    unresolved_before = []
    numeric_nodes = {}
    for c, observation in zip(candidates, evidence):
        option = observation['selected_label']
        level = observation['numeric_level'] or c['markdown_level']
        strong = bool(observation['support']) and not observation['conflicts']
        reasons = list(observation['conflicts'])
        if observation['support'] in (['EXPLICIT_BODY_SYNTAX'], ['REPEATED_PAGE_MARGIN']):
            decisions.append({'candidate_id':c['id'],'role':'body','parent_id':None,
                              'status':'RESOLVED','role_uncertain':False,'parent_uncertain':False,
                              'reasons':list(observation['support']),'origin':'deterministic'})
            continue
        if not strong: reasons.append('ROLE_UNCERTAIN')
        parent = None
        parent_supported=True
        if strong and option and option['family']=='numeric' and len(option['path'])==1:
            series_anchor=next((x for x in reversed(stack) if x['series']==option['series']),None)
            if series_anchor:
                level=series_anchor['level']
            elif (option['value']==1 and stack and stack[-1].get('family')=='alpha'
                  and c['markdown_level']):
                level=stack[-1]['level']+1
                reasons.append('NUMERIC_RESTART_UNDER_ALPHA_SECTION')
            else:
                level=c['markdown_level'] or 1
        if strong and option and option['family']!='numeric':
            series = option['series']
            series_anchor=next((x for x in reversed(stack) if x['series']==series),None)
            if series_anchor: level = series_anchor['level']
            elif option['value']==1 and stack and stack[-1]['series'] and stack[-1]['series']!=series:
                level = stack[-1]['level']+1
                reasons.append('LABEL_FAMILY_RESTART_UNDER_ACTIVE_SECTION')
            elif option['value']==1: level = level or 1
            else: reasons.append('SEQUENCE_START_UNANCHORED'); parent_supported=False
        if strong and level is None: level=1
        anchor_order = stack[-1]['order'] if stack else -1
        blockers = [u for u in unresolved_before if u['order']>anchor_order and
                    (u['level'] is None or level is None or u['level']<level)]
        if strong and level==1: blockers=[]
        possible = ['root'] + [x['id'] for x in stack[-3:]] + [u['id'] for u in blockers[-3:]]
        if strong:
            while stack and stack[-1]['level'] >= level: stack.pop()
            parent = stack[-1]['id'] if stack else 'root'
            if observation.get('context_anchor') and parent != observation['context_anchor']:
                reasons.append('CONTEXT_PARENT_NOT_ACTIVE'); parent=None
            if option and option['family']=='numeric' and len(option['path'])>1:
                parent=numeric_nodes.get(tuple(option['path'][:-1]))
                if parent is None: reasons.append('NUMBERED_PARENT_MISSING')
                elif not stack or stack[-1]['id']!=parent:
                    reasons.append('NUMBERED_SCOPE_CONFLICT'); parent=None
            if blockers: reasons.append('PARENT_UNCERTAIN'); parent = None
            elif level > (stack[-1]['level'] + 1 if stack else 1):
                reasons.append('SEQUENCE_ANOMALY'); parent = None
            if not parent_supported: parent=None; reasons.append('PARENT_UNCERTAIN')
        resolved = strong and parent is not None
        observation['possible_parents'] = possible
        decisions.append({'candidate_id': c['id'], 'role': 'section' if strong else 'unknown',
                          'parent_id': parent, 'status': 'RESOLVED' if resolved else 'AMBIGUOUS',
                          'role_uncertain': not strong, 'parent_uncertain': parent is None,
                          'reasons': reasons, 'origin': 'deterministic'})
        if resolved:
            stack.append({'id':c['id'],'level':level,'order':len(decisions)-1,
                          'series':option['series'] if option else None,
                          'family':option['family'] if option else None})
            if option:
                if option['family']=='numeric': numeric_nodes[tuple(option['path'])]=c['id']
            decisions[-1]['reasons'].extend(observation['support'])
        else: unresolved_before.append({'id':c['id'],'level':level,'order':len(decisions)-1})
    return evidence, decisions




def resolve_regions(regions, candidates, decisions, document_hash, revision, structure_replays=None):
    responses = []
    for r in regions:
        payload = dict(r['input'], document_hash=document_hash, revision=revision)
        actual=input_characters(payload)
        limit=r['budget']['limit']
        if actual>limit:
            result={'status':'skipped','mode':'unavailable','reason':'INPUT_BUDGET_EXCEEDED',
                    'input':payload,'budget':{'unit':'json_characters','actual':actual,'limit':limit},
                    'all_candidates_preserved':True}
        else:
            result = request('structure', payload, (structure_replays or {}).get(r['id']))
        if result['status']=='returned':
            existing = {d['candidate_id']:d['parent_id'] for d in decisions if d['status']=='RESOLVED' and d['role']=='section'}
            errors = validate_response(result['response'], r['candidate_ids'], r['input']['anchors'], existing)
            # Atomic application also rejects parents that abstain, are omitted, or remain unknown.
            proposed = {x['candidate_id']:x for x in result['response']} if not errors else {}
            for x in proposed.values():
                parent = x.get('parent_id')
                if x['role']=='section' and parent not in {'root', *existing} and proposed.get(parent, {}).get('role')!='section':
                    errors.append('Unresolved parent')
                order = {c['id']:i for i,c in enumerate(candidates)}
                if x['role']=='section' and parent in order and order[parent]>=order[x['candidate_id']]:
                    errors.append('Parent must precede child in source order')
            if errors: result['status']='rejected'; result['validation_errors']=errors
            else:
                for d in decisions:
                    item = proposed.get(d['candidate_id'])
                    if item and item['role']!='abstain':
                        d.update(role=item['role'], parent_id=item.get('parent_id'), status='RESOLVED',
                                 role_uncertain=False, parent_uncertain=False, origin='fixture_replay', reasons=['SYNTHETIC_REPLAY'])
        responses.append(dict(result, region_id=r['id']))
        if result['status']=='returned':
            answered={x['candidate_id'] for x in result['response']}
            responses[-1]['missing_decisions']=[ident for ident in r['candidate_ids'] if ident not in answered]
            responses[-1]['abstained']=[x['candidate_id'] for x in result['response'] if x['role']=='abstain']
    return responses
