"""Current: reference comparisons and alignment-dependent measurement.
Limitations: measurement requires separately confirmed alignment/presence/ownership.
TODO(B1): confirm extraction presence, alignment and ownership before scoring.
Acceptance: repeated titles, AI-draft labels and conservative denominators.
"""
import difflib
from .models import nodes
from .validation import validate_tree

def compare_runs(automatic, manual):
    """Post-inference debugging differences; neither run is a reference answer."""
    report = {'comparison': 'automatic vs manual debug run',
              'verified_parser_accuracy': False, 'changes': [], 'unmatched': []}
    if (automatic['document_hash'] != manual['document_hash'] or
            [p['page'] for p in automatic['pages']] != [p['page'] for p in manual['pages']]):
        return dict(report, error='Runs must use the same PDF hash and selected pages')
    report['revisions'] = {name: run['canonical_revision'] for name, run in
                           [('automatic', automatic), ('manual', manual)]}
    def index(run):
        candidates = {c['id']: c for c in run['candidates']}
        result = {}
        parents = {}
        def walk(node, parent=None):
            parents[node['id']] = parent
            for child in node['children']: walk(child, node)
        walk(run['tree']['root'])
        for node in nodes(run['tree']):
            candidate = candidates.get(node['id'])
            key = ('root',) if candidate is None and node is run['tree']['root'] else (
                candidate['page'] if candidate else None, node['label'], node['title'])
            parent = parents[node['id']]
            result.setdefault(key, []).append({'id': node['id'], 'label': node['label'],
                'title': node['title'], 'depth': node['depth'],
                'parent': None if parent is None else (parent['label'], parent['title']),
                'own_text': node['text']})
        return result
    left, right = index(automatic), index(manual)
    for key in sorted(set(left) | set(right), key=str):
        a, b = left.get(key, []), right.get(key, [])
        if len(a) != 1 or len(b) != 1:
            report['unmatched'].append({'identity': key, 'automatic': a, 'manual': b,
                'reason': 'missing or repeated identity; alignment not inferred'})
            continue
        changed = [field for field in ('label', 'title', 'depth', 'parent', 'own_text') if a[0][field] != b[0][field]]
        if changed:
            report['changes'].append({'identity': key, 'fields': changed,
                                     'automatic': a[0], 'manual': b[0]})
    report['alignment_method'] = 'unique original page + exact label/title; suggestions across revisions'
    report['summaries'] = {name: {'accepted_sections': len(run['section_index']),
        'unresolved': run['validation']['pending'], 'validation': run['validation'],
        'debug_overrides': run['debug_overrides']} for name, run in
        [('automatic', automatic), ('manual', manual)]}
    report['page_changes'] = [{'page': a['page'], 'automatic': a['markdown'], 'manual': b['markdown']}
        for a, b in zip(automatic['pages'], manual['pages']) if a['markdown'] != b['markdown']]
    return report

def compare(run, reference, metadata=None, alignment=None):
    errors = validate_tree(reference)
    if errors: return {'schema_errors': errors, 'scores': None}
    status = (metadata or {}).get('annotation_status', 'unreviewed')
    label = ('against AI draft reference' if status == 'ai_unreviewed' else
             'against synthetic reference' if status == 'synthetic' else
             'against reviewed golden' if status == 'reviewed' else 'against unreviewed reference')
    refs, preds = nodes(reference)[1:], nodes(run['tree'])[1:]
    suggestions, used = [], set()
    for n in refs:
        link = (alignment or {}).get(n['id'], {})
        source_candidates=[c for c in run['candidates'] if c['page'] in link.get('pages',[]) and
                           c['original_text']==link.get('heading_text')]
        if link.get('canonical_revision') is not None:
            source_candidates=[c for c in source_candidates if
                               link['canonical_revision']==run['canonical_revision'] and
                               c['ranges'][0]['start']==link.get('start')]
        aligned_id=source_candidates[0]['id'] if link.get('confirmed') is True and len(source_candidates)==1 else None
        matches = [p for p in preds if p['id'] not in used and
                   (p['label'], p['title'].strip()) == (n['label'], n['title'].strip())]
        # Repeated titles cannot be automatically confirmed, even with matching order.
        unique = len(matches) == 1 and sum((x['label'], x['title'].strip()) ==
                                          (n['label'], n['title'].strip()) for x in refs) == 1
        p = next((p for p in preds if p['id']==aligned_id and p['id'] not in used),None) if aligned_id else matches[0] if unique else None
        if p: used.add(p['id'])
        candidate = next((c for c in run['candidates'] if c['id'] == (p or {}).get('id')), None)
        confirmed = bool(p and aligned_id==p['id'] and link.get('confirmed') is True and candidate and
                         candidate['page'] in link.get('pages', []) and
                         link.get('heading_text') == candidate['original_text'])
        suggestions.append({'reference_id': n['id'], 'prediction_id': p['id'] if p else None,
                            'status': 'confirmed' if confirmed else 'needs_manual_alignment',
                            'reference': n, 'prediction': p,
                            'body_diff': '\n'.join(difflib.unified_diff(n['text'].splitlines(),
                                            (p or {}).get('text', '').splitlines(), lineterm=''))})
    confirmed = [m for m in suggestions if m['status'] == 'confirmed']
    captured = sum(any((c['label'], c['title'].strip()) == (n['label'], n['title'].strip())
                       for c in run['candidates']) for n in refs)
    confirmed_candidates, uncertain_refs, used_candidates, confirmed_misses = {}, [], set(), {}
    for n in refs:
        link = (alignment or {}).get(n['id'], {})
        eligible = [c for c in run['candidates'] if c['page'] in link.get('pages', []) and
                    c['original_text']==link.get('heading_text')]
        if link.get('canonical_revision') is not None:
            eligible=[c for c in eligible if link['canonical_revision']==run['canonical_revision'] and c['ranges'][0]['start']==link.get('start')]
        if link.get('confirmed') is True and len(eligible)==1 and eligible[0]['id'] not in used_candidates:
            confirmed_candidates[n['id']] = eligible[0]['id']
            used_candidates.add(eligible[0]['id'])
        elif (not eligible and link.get('confirmed') is True and link.get('markdown_presence_confirmed') is True
              and link.get('markdown_presence') in ('present','absent')
              and link.get('pages') and all(p in [page['page'] for page in run['pages']] for p in link['pages'])
              and link.get('canonical_revision',run['canonical_revision'])==run['canonical_revision']):
            confirmed_misses[n['id']]='candidate_generation' if link['markdown_presence']=='present' else 'extraction'
        else: uncertain_refs.append(n['id'])
    def parents(tree):
        mapping = {}
        def walk(n):
            for c in n['children']: mapping[c['id']]=n['id']; walk(c)
        walk(tree['root']); return mapping
    rp, pp = parents(reference), parents(run['tree'])
    ref_to_pred = {m['reference_id']:m['prediction_id'] for m in confirmed}
    parent_checks = []
    for rid, pid in ref_to_pred.items():
        expected_parent = 'root' if rp[rid]==reference['root']['id'] else ref_to_pred.get(rp[rid])
        if expected_parent is not None: parent_checks.append(pp.get(pid)==expected_parent)
    present = [n for n in refs if (alignment or {}).get(n['id'],{}).get('markdown_presence_confirmed') is True and
               (alignment or {}).get(n['id'],{}).get('markdown_presence','present')=='present']
    presence_known=all((alignment or {}).get(n['id'],{}).get('markdown_presence_confirmed') is True for n in refs)
    fully_aligned = not uncertain_refs and bool(refs)
    counts = {'candidate_recall': {'captured':len(confirmed_candidates), 'eligible':len(refs)},
              'candidate_precision': {'confirmed_matches':len(confirmed_candidates),'candidates':len(run['candidates'])},
              'section_recall': {'confirmed_matches':len(confirmed),'eligible':len(refs)},
              'section_precision': {'confirmed_matches':len(confirmed),'sections':len(preds)},
              'parent': {'correct':sum(parent_checks),'evaluated':len(parent_checks)},
              'missing_sections':len(refs)-len(confirmed)}
    def ratio(a,b): return a/b if b else None
    body_checks=[]
    for match in confirmed:
        link=(alignment or {}).get(match['reference_id'],{})
        own_spans=[b for b in run['body'] if b['owner']==match['prediction_id'] and b['status']=='ASSIGNED']
        if link.get('own_text_confirmed') is True and all(b['ownership']=='source_sliced' for b in own_spans):
            expected,actual=match['reference']['text'],match['prediction']['text']
            body_checks.append({'reference_id':match['reference_id'], 'exact':expected==actual,
                                'whitespace_normalized':' '.join(expected.split())==' '.join(actual.split())})
    attribution=[]
    for n in refs:
        if n['id'] in ref_to_pred: continue
        attribution.append({'reference_id':n['id'], 'stage':confirmed_misses.get(n['id'],
                            'resolver' if n['id'] in confirmed_candidates else 'unclassified')})
    return {'comparison': label, 'annotation_status': status,
            'verified_parser_accuracy': False,
            'candidate_capture_suggestions': {'captured': captured, 'eligible': len(refs)},
            'confirmed_matches': len(confirmed), 'alignment_coverage': [len(confirmed), len(refs)],
            'counts':counts, 'confirmed_candidate_matches':confirmed_candidates,
            'uncertain_alignment':uncertain_refs,
            'end_to_end_candidate_recall':ratio(len(confirmed_candidates),len(refs)) if fully_aligned else None,
            'generator_recall': ratio(sum(n['id'] in confirmed_candidates for n in present),len(present)) if presence_known and fully_aligned else None,
            'generator_denominator':len(present) if presence_known else None,
            'candidate_precision':ratio(len(confirmed_candidates),len(run['candidates'])) if fully_aligned else None,
            'section_precision_recall':{'precision':ratio(len(confirmed),len(preds)), 'recall':ratio(len(confirmed),len(refs))} if fully_aligned else None,
            'parent_accuracy':ratio(sum(parent_checks),len(parent_checks)) if fully_aligned else None,
            'own_text_accuracy':{'exact':ratio(sum(b['exact'] for b in body_checks),len(body_checks)),
                                 'whitespace_normalized':ratio(sum(b['whitespace_normalized'] for b in body_checks),len(body_checks)),
                                 'evaluated':len(body_checks), 'checks':body_checks} if body_checks else None,
            'ambiguity':{'role':sum(d['role_uncertain'] for d in run['decisions']),
                         'parent':sum(d['parent_uncertain'] for d in run['decisions']),
                         'regions':len(run['regions']), 'region_sizes':[len(r['candidate_ids']) for r in run['regions']]},
            'reason': 'N/A until alignment, extraction presence and ownership are confirmed',
            'matches': suggestions, 'root_diff': {'reference': reference['root']['text'],
                                                  'prediction': run['tree']['root']['text']},
            'root_title_diff':{'reference':reference['root']['title'],'prediction':run['tree']['root']['title']},
            'miss_attribution':attribution}
