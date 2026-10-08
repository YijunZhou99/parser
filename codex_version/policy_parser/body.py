"""Current: source span accounting, hierarchy scope paths and cross-page own text.
Limitations: unheaded ancestor resumption is never inferred from arbitrary prose.
TODO(B9): add source-supported scope closure when authoritative evidence is available.
Acceptance: generic nested/sibling scopes, page gaps, tables and multi-page headings.
"""


def attach_body(pages, candidates, decisions, revision, created):
    body=[]
    by_decision={d['candidate_id']:d for d in decisions}
    accepted=[c for c in candidates if c['id'] in created]
    parents={child['id']:node['id'] for node in created.values() for child in node['children']}
    parents['root']=None
    def path(owner):
        chain=[]
        while owner is not None:
            chain.append(owner); owner=parents[owner]
        return list(reversed(chain))
    starts=sorted((c['ranges'][0]['page'],c['ranges'][0]['start']) for c in accepted)
    intervals=[]
    for c in candidates:
        if by_decision[c['id']]['status']=='AMBIGUOUS':
            start=(c['ranges'][0]['page'],c['ranges'][0]['start'])
            end=next((point for point in starts if point>start),None)
            intervals.append((start,end,c['id'],'AMBIGUOUS_HEADING_BOUNDARY'))
    # A skipped source page breaks evidence for an unheaded continuation.
    for previous,current in zip(pages,pages[1:]):
        if current['page']>previous['page']+1:
            start=(current['page'],0)
            end=next((point for point in starts if point>=start),None)
            intervals.append((start,end,None,'UNSELECTED_PAGE_GAP'))
    headings={}
    for c in accepted:
        for index,span in enumerate(c['ranges']):
            headings.setdefault(span['page'],[]).append((span,c['id'],index==0))
    active='root'
    last_assigned={}
    opened_by=None
    for page in pages:
        number=page['page']; markdown=page['markdown']; cursor=0
        def append_span(start,end,owner,status,boundary=None):
            value=markdown[start:end]
            position=(number,start)
            dependencies=[ident for lo,hi,ident,_ in intervals if lo<=position and (hi is None or position<hi) and ident]
            reasons=sorted({reason for lo,hi,_,reason in intervals if lo<=position and (hi is None or position<hi)})
            scope=path(owner)
            separator=''
            if status=='ASSIGNED':
                previous=last_assigned.get(owner)
                if previous and previous[0]!=number and previous[1] and value and not previous[1][-1].isspace() and not value[0].isspace():
                    separator='\n'  # A visible page boundary, not invented substantive text.
                created[owner]['text']+=separator+value
                last_assigned[owner]=(number,value)
            body.append({'owner':owner,'status':status,'ownership':'provisional' if reasons else 'source_sliced',
                         'uncertain_boundaries':dependencies, 'ownership_reasons':reasons,
                         'scope_path':scope, 'opened_by':opened_by,
                         'scope_assumption':'Active section continues until a supported heading changes scope',
                         'ancestor_resumption':'not_inferred',
                         'separator_before':separator, 'separator_reason':'PAGE_BOUNDARY_SEPARATOR' if separator else None,
                         'boundary':boundary,
                         'ranges':[{'revision':revision,'page':number,'start':start,'end':end}], 'text':value})
        def assign(start,end,owner,status='ASSIGNED',boundary=None):
            if end<=start: return
            cuts={start,end}
            for lo,hi,_,_ in intervals:
                if lo[0]==number and start<lo[1]<end: cuts.add(lo[1])
                if hi and hi[0]==number and start<hi[1]<end: cuts.add(hi[1])
            points=sorted(cuts)
            for lo,hi in zip(points,points[1:]): append_span(lo,hi,owner,status,boundary)
        for span,owner,first in sorted(headings.get(number,[]),key=lambda x:x[0]['start']):
            assign(cursor,span['start'],active)
            boundary=None
            if first:
                old_path,new_path=path(active),path(owner)
                common=0
                while common<min(len(old_path),len(new_path)) and old_path[common]==new_path[common]: common+=1
                boundary={'reason':'SUPPORTED_HEADING','closed_sections':list(reversed(old_path[common:])),
                          'opened_sections':new_path[common:]}
                active=owner; opened_by=owner
            else:
                boundary={'reason':'HEADING_CONTINUATION','closed_sections':[],'opened_sections':[]}
            assign(span['start'],span['end'],owner,'HEADING',boundary)
            cursor=span['end']
        assign(cursor,len(markdown),active)
    return body


def body_index(tree, body):
    """Export own-text provenance separately, leaving the annotator schema unchanged."""
    result={}
    def walk(node):
        own=[b for b in body if b['owner']==node['id'] and b['status']=='ASSIGNED']
        heading=[b for b in body if b['owner']==node['id'] and b['status']=='HEADING']
        result[node['id']]={'label':node['label'],'title':node['title'],
                            'own_ranges':[span for b in own for span in b['ranges']],
                            'heading_ranges':[span for b in heading for span in b['ranges']],
                            'source_characters':sum(len(b['text']) for b in own),
                            'export_characters':len(node['text']),
                            'generated_page_separators':sum(len(b['separator_before']) for b in own),
                            'ownership':'provisional' if any(b['ownership']=='provisional' for b in own) else 'source_sliced',
                            'own_text':node['text'], 'verified':False}
        for child in node['children']: walk(child)
    walk(tree['root'])
    return result
