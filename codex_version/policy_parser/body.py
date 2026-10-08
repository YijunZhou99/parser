"""Current: attaches own text by canonical source heading boundaries.
Limitations: enclosing scope resumption unsupported; uncertain ownership is provisional.
TODO(B9): add confirmed scope closure and source-faithful table handling.
Acceptance: body nonduplication, cross-page spans and conservation tests.
"""


def attach_body(pages, candidates, decisions, revision, created):
    body, active = [], 'root'
    ambiguous = [c for c in candidates if next(d for d in decisions if d['candidate_id']==c['id'])['status']=='AMBIGUOUS']
    accepted = [c for c in candidates if c['id'] in created]
    uncertainty_intervals=[]
    for c in ambiguous:
        start=(c['page'],c['ranges'][0]['start'])
        end=next(((a['page'],a['ranges'][0]['start']) for a in accepted
                  if (a['page'],a['ranges'][0]['start'])>start),None)
        uncertainty_intervals.append((start,end,c['id']))
    for p in pages:
        boundaries = [c for c in candidates if c['page'] == p['page'] and c['id'] in created]
        cursor = 0
        def assign(start, end, owner, status='ASSIGNED'):
            if end <= start: return
            cuts={start,end}
            for lo,hi,_ in uncertainty_intervals:
                if lo[0]==p['page'] and start<lo[1]<end: cuts.add(lo[1])
                if hi and hi[0]==p['page'] and start<hi[1]<end: cuts.add(hi[1])
            ordered=sorted(cuts)
            for lo,hi in zip(ordered,ordered[1:]): append_span(lo,hi,owner,status)
        def append_span(start,end,owner,status):
            value = p['markdown'][start:end]
            if status == 'ASSIGNED': created[owner]['text'] += value
            position=(p['page'],start)
            dependencies=[ident for lo,hi,ident in uncertainty_intervals if lo<=position and (hi is None or position<hi)]
            body.append({'owner': owner, 'status': status, 'ownership': 'provisional' if dependencies else 'source_sliced',
                         'uncertain_boundaries':dependencies,
                         'ranges': [{'revision': revision, 'page': p['page'], 'start': start, 'end': end}], 'text': value})
        for c in boundaries:
            span = c['ranges'][0]; assign(cursor, span['start'], active)
            assign(span['start'], span['end'], c['id'], 'HEADING')
            active, cursor = c['id'], span['end']
        assign(cursor, len(p['markdown']), active)
    return body
