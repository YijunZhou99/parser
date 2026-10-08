"""Current: label/style evidence, conservative numeric-list and Roman/alpha context.
Limitations: these mechanisms remain assumptions awaiting reviewed benchmarks.
TODO(B5): measure false confident decisions and improve bounded relationship evidence.
Acceptance: cross-page Roman/alpha, conflicts and unnumbered heading fixtures.
"""
from collections import defaultdict
from .labels import numeric_depth, interpretations
from .models import Candidate, Evidence

def build_evidence(candidates: list[Candidate]) -> list[Evidence]:
    options = {c['id']: interpretations(c['label']) for c in candidates}
    series = defaultdict(list)
    for c in candidates:
        if 'body_markup' in c['signals']: continue
        if c['markdown_level'] or 'standalone_bold' in c['signals'] or 'isolated_short_block' in c['signals']:
            for opt in options[c['id']]:
                if opt['family']=='numeric' and not c['markdown_level'] and not (
                        'standalone_bold' in c['signals'] and 'following_prose' in c['signals']):
                    continue
                series[opt['series']].append((c,opt))
    corroboration = defaultdict(list)
    for members in series.values():
        for (a,oa),(b,ob) in zip(members,members[1:]):
            if ob['value']==oa['value']+1 and a['markdown_level']==b['markdown_level']:
                corroboration[(a['id'],oa['series'])].append(b['id'])
                corroboration[(b['id'],ob['series'])].append(a['id'])
    styles = defaultdict(list)
    for c in candidates:
        if c['markdown_level'] and 'following_prose' in c['signals'] and not c['label']:
            styles[c['markdown_level']].append(c['id'])
    observations = []
    for c in candidates:
        level = c['markdown_level']
        numeric_level = numeric_depth(c['label'])
        support, conflicts = [], []
        corroborated = [o for o in options[c['id']] if corroboration[(c['id'],o['series'])]]
        chosen = corroborated[0] if len(corroborated)==1 else None
        if len(corroborated)>1: conflicts.append('LABEL_INTERPRETATION_CONFLICT')
        if numeric_level and level and numeric_level!=level: conflicts.append('EVIDENCE_CONFLICT')
        if numeric_level and level and not conflicts:
            support.append('CONSISTENT_MARKDOWN_NUMBERING'); chosen=options[c['id']][0]
        elif chosen and not conflicts: support.append('CONSISTENT_LABEL_SEQUENCE')
        elif not c['label'] and c['id'] in styles[level] and len(styles[level])>=2:
            support.append('REPEATED_HEADING_STYLE_WITH_PROSE')
        if 'body_markup' in c['signals'] or 'bare_number' in c['signals']:
            support = ['EXPLICIT_BODY_SYNTAX']; chosen = None
        elif 'repeated_page_margin' in c['signals']:
            support = ['REPEATED_PAGE_MARGIN']; chosen = None
        elif chosen and chosen['family']=='numeric' and not level and not (
                'standalone_bold' in c['signals'] and 'following_prose' in c['signals']):
            # Label succession alone does not distinguish prose lists from sections.
            support = []; chosen = None
        observations.append({'candidate_id': c['id'], 'signals': list(c['signals']),
                             'numeric_level': numeric_level, 'markdown_level': level,
                             'possible_parents': [],
                             'support': support, 'conflicts': conflicts,
                             'label_interpretations':options[c['id']], 'selected_label':chosen,
                             'sequence_peers':corroboration[(c['id'],chosen['series'])] if chosen else []})
    # A single first alphabetic subsection needs an established Roman context
    # plus an explicit heading followed by prose, rather than a fabricated peer.
    roman_context = None
    for c, observation in zip(candidates, observations):
        selected = observation['selected_label']
        if selected and selected['family']=='roman' and observation['support'] and not observation['conflicts']:
            roman_context = c['id']
        elif (not observation['support'] and not observation['conflicts'] and roman_context
              and c['markdown_level'] and 'following_prose' in c['signals']
              and 'body_markup' not in c['signals'] and len(options[c['id']])==1
              and options[c['id']][0]['family']=='alpha' and options[c['id']][0]['value']==1):
            observation['selected_label'] = options[c['id']][0]
            observation['support'] = ['FIRST_ALPHA_HEADING_IN_ROMAN_CONTEXT']
            observation['context_anchor'] = roman_context
        elif selected and selected['family']=='numeric' and observation['support']:
            roman_context = None
    return observations
