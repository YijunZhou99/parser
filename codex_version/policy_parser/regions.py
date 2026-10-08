"""Current: dependency components, merged source context and bounded local anchors.
Limitations: indivisible oversized components are retained and skipped, not truncated.
TODO(B6): validate dependency discovery and safe splitting against reviewed cases.
Acceptance: unrelated adjacency, cross-page edges, exact budgets and full coverage tests.
"""
import json

DEFAULT_INPUT_CHARACTERS = 20000  # Resource limit, not a heading/ambiguity threshold.
CONTEXT_CHARACTERS = 200         # Local source context on each side of a candidate.


def input_characters(payload):
    """Exact size of compact JSON in Unicode characters; deliberately not token count."""
    return len(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')))


def source_context(component, byid, pages):
    intervals={}
    bypage={p['page']:p for p in pages}
    for ident in component:
        for span in byid[ident]['ranges']:
            md=bypage[span['page']]['markdown']
            intervals.setdefault(span['page'],[]).append(
                (max(0,span['start']-CONTEXT_CHARACTERS), min(len(md),span['end']+CONTEXT_CHARACTERS)))
    context=[]
    for page,spans in sorted(intervals.items()):
        merged=[]
        for start,end in sorted(spans):
            if merged and start<=merged[-1][1]: merged[-1][1]=max(merged[-1][1],end)
            else: merged.append([start,end])
        for start,end in merged:
            context.append({'page':page,'start':start,'end':end,
                            'text':bypage[page]['markdown'][start:end]})
    return context


def regions_for(candidates, evidence, decisions, pages,
                max_input_characters=DEFAULT_INPUT_CHARACTERS, document_hash=None, revision=None):
    if type(max_input_characters) is not int or max_input_characters<=0:
        raise ValueError('Region input budget must be a positive integer character count')
    byid={c['id']:c for c in candidates}
    order={c['id']:i for i,c in enumerate(candidates)}
    observations={e['candidate_id']:e for e in evidence}
    unresolved={d['candidate_id'] for d in decisions if d['status']=='AMBIGUOUS'}
    neighbors={c['id']:set() for c in candidates if c['id'] in unresolved}
    edges=[]
    for ident in neighbors:
        for parent in observations[ident]['possible_parents']:
            if parent in unresolved and parent!=ident:
                neighbors[ident].add(parent); neighbors[parent].add(ident)
                edges.append({'candidate_id':ident,'depends_on':parent,'reason':'POSSIBLE_UNRESOLVED_PARENT'})
    confirmed={d['candidate_id']:d for d in decisions if d['status']=='RESOLVED' and d['role']=='section'}
    groups,visited=[],set()
    for ident in neighbors:
        if ident in visited: continue
        component,pending=[],[ident]
        while pending:
            current=pending.pop()
            if current in visited: continue
            visited.add(current); component.append(current)
            pending.extend(sorted(neighbors[current]-visited,key=order.get,reverse=True))
        component.sort(key=order.get)
        # Only anchors relevant to this component and their confirmed ancestors.
        anchors=set()
        for candidate_id in component:
            anchors.update(x for x in observations[candidate_id]['possible_parents'] if x in confirmed)
        preceding=[x for x in confirmed if order[x]<order[component[0]]]
        following=[x for x in confirmed if order[x]>order[component[-1]]]
        if preceding: anchors.add(max(preceding,key=order.get))
        next_anchor=min(following,key=order.get) if following else None
        context_outline=set(anchors)
        if next_anchor: context_outline.add(next_anchor)
        todo=list(context_outline)
        while todo:
            parent=confirmed[todo.pop()]['parent_id']
            if parent in confirmed and parent not in context_outline:
                context_outline.add(parent); todo.append(parent)
        # A following anchor is context, not an admissible future parent.
        anchors.update(x for x in context_outline if order[x]<order[component[-1]])
        anchors=sorted(anchors,key=order.get)
        outline=[{'id':x,'parent_id':confirmed[x]['parent_id'], 'label':byid[x]['label'],
                  'title':byid[x]['title'], 'context_only':x not in anchors}
                 for x in sorted(context_outline,key=order.get)]
        context=source_context(component,byid,pages)
        payload={'candidate_ids':component, 'candidates':[byid[x] for x in component],
                 'evidence':[observations[x] for x in component], 'anchors':anchors,
                 'context':context, 'compressed_outline':outline}
        if document_hash is not None: payload['document_hash']=document_hash
        if revision is not None: payload['revision']=revision
        size=input_characters(payload)
        component_ids=set(component)
        component_edges=[edge for edge in edges if edge['candidate_id'] in component_ids]
        groups.append({'id':f'region-{len(groups)+1}','candidate_ids':component,
                       'pages':sorted({span['page'] for x in component for span in byid[x]['ranges']}),
                       'dependencies':{x:sorted(neighbors[x],key=order.get) for x in component},
                       'dependency_edges':component_edges,
                       'reason':'EXPLICIT_POSSIBLE_PARENT_DEPENDENCIES' if component_edges else 'ISOLATED_AMBIGUITY',
                       'budget_status':'oversized' if size>max_input_characters else 'within_budget',
                       'budget':{'unit':'json_characters','limit':max_input_characters,'actual':size},
                       'coverage':{'candidate_count':len(component),'context_characters':sum(len(x['text']) for x in context),
                                   'all_candidates_included':True,'truncated':False},
                       'split_status':'indivisible_dependency_component' if size>max_input_characters else 'not_needed',
                       'input':payload})
    return groups
