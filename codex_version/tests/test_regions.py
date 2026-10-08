"""Generic dependency/budget fixtures; no corpus keywords or reference answers."""
import copy
import pytest
from policy_parser.candidates import candidate_blocks
from policy_parser.regions import regions_for, input_characters
from policy_parser.resolver import resolve_regions
from policy_parser.pipeline import run_pages
from test_structure import pages


def fixture(texts):
    source=pages(*texts)
    candidates=candidate_blocks(source,'revision')
    evidence=[{'candidate_id':c['id'],'possible_parents':['root'],'signals':c['signals'],
               'support':[],'conflicts':[]} for c in candidates]
    decisions=[{'candidate_id':c['id'],'status':'AMBIGUOUS','role':'unknown','parent_id':None}
               for c in candidates]
    return candidates,evidence,decisions,source


@pytest.mark.parametrize('label',['(i)','(a)','7.4',''])
def test_adjacent_ambiguities_without_dependency_stay_separate(label):
    args=fixture([f'## {label} First arbitrary heading\n\n## {label} Second arbitrary heading'])
    groups=regions_for(*args)
    assert len(groups)==2
    assert all(len(g['candidate_ids'])==1 for g in groups)
    assert all(g['reason']=='ISOLATED_AMBIGUITY' for g in groups)


def test_shared_unknown_parent_groups_cross_page_siblings():
    candidates,evidence,decisions,source=fixture(['## Unknown enclosing heading',
                                                '### First possible child\n\n### Second possible child'])
    parent=candidates[0]['id']
    for e in evidence[1:]: e['possible_parents']=[parent,'root']
    groups=regions_for(candidates,evidence,decisions,source)
    assert len(groups)==1 and groups[0]['pages']==[1,2]
    assert len(groups[0]['dependency_edges'])==2
    assert groups[0]['coverage']['candidate_count']==3


def test_context_union_preserves_exact_source_and_all_headings():
    candidates,evidence,decisions,source=fixture(['## Arbitrary first\n\n## Arbitrary second\n\n## Arbitrary third'])
    for e in evidence[1:]: e['possible_parents']=[candidates[0]['id']]
    group=regions_for(candidates,evidence,decisions,source)[0]
    assert len(group['input']['context'])==1
    excerpt=group['input']['context'][0]
    assert excerpt['text']==source[0]['markdown'][excerpt['start']:excerpt['end']]
    assert all(excerpt['start']<=c['ranges'][0]['start']<c['ranges'][0]['end']<=excerpt['end'] for c in candidates)
    assert group['coverage']['truncated'] is False


def test_local_anchor_outline_does_not_include_entire_document():
    text='\n\n'.join(f'## {i} Unrelated title {i}' for i in range(1,81))+'\n\n### Ambiguous final child'
    candidates,evidence,decisions,source=fixture([text])
    for d in decisions[:-1]: d.update(status='RESOLVED',role='section',parent_id='root')
    evidence[-1]['possible_parents']=[candidates[-2]['id'],'root']
    group=regions_for(candidates,evidence,decisions,source)[0]
    assert group['input']['anchors']==[candidates[-2]['id']]
    assert len(group['input']['compressed_outline'])==1


def test_ancestor_chain_and_following_anchor_context_only():
    candidates,evidence,decisions,source=fixture(['# Outer\n\n## Inner\n\n### Unknown child\n\n# Following boundary'])
    ids=[c['id'] for c in candidates]
    for index,parent in [(0,'root'),(1,ids[0]),(3,'root')]:
        decisions[index].update(status='RESOLVED',role='section',parent_id=parent)
    evidence[2]['possible_parents']=[ids[1]]
    group=regions_for(candidates,evidence,decisions,source)[0]
    assert group['input']['anchors']==ids[:2]
    following=next(n for n in group['input']['compressed_outline'] if n['id']==ids[3])
    assert following['context_only'] and ids[3] not in group['input']['anchors']


def test_budget_is_exact_including_request_envelope():
    args=fixture(['## An arbitrary ambiguous heading'])
    original=regions_for(*args,document_hash='a'*64,revision='b'*64)[0]
    size=input_characters(original['input'])
    assert original['budget']['actual']==size
    fits=regions_for(*args,max_input_characters=size,document_hash='a'*64,revision='b'*64)[0]
    too_small=regions_for(*args,max_input_characters=size-1,document_hash='a'*64,revision='b'*64)[0]
    assert fits['budget_status']=='within_budget'
    assert too_small['budget_status']=='oversized'
    assert fits['input']==too_small['input']


def test_oversized_component_skips_provider_without_losing_candidates(monkeypatch):
    import policy_parser.resolver as resolver
    candidates,evidence,decisions,source=fixture(['## First unknown','## Dependent unknown'])
    evidence[1]['possible_parents']=[candidates[0]['id']]
    groups=regions_for(candidates,evidence,decisions,source,1,'hash','revision')
    before=copy.deepcopy(decisions)
    def fail(*args,**kwargs): raise AssertionError('Oversized input must not call provider')
    monkeypatch.setattr(resolver,'request',fail)
    response=resolve_regions(groups,candidates,decisions,'hash','revision')[0]
    assert response['status']=='skipped' and response['reason']=='INPUT_BUDGET_EXCEEDED'
    assert response['all_candidates_preserved'] and decisions==before
    assert groups[0]['candidate_ids']==[c['id'] for c in candidates]
    assert groups[0]['split_status']=='indivisible_dependency_component'


def test_region_shape_independent_of_document_wording():
    def shape(text):
        run=run_pages(pages(text))
        return [(len(r['candidate_ids']),len(r['dependency_edges']),r['pages']) for r in run['regions']]
    assert shape('## Unknown compass\n\n### Unknown galaxy')==shape('## Other heading\n\n### Other wording')


def test_nonpositive_budget_is_rejected():
    with pytest.raises(ValueError): regions_for(*fixture(['## Unknown']),max_input_characters=0)


def test_single_candidate_with_cross_page_ranges_keeps_both_pages():
    candidates,evidence,decisions,source=fixture(['## Beginning of wrapped title','Continuation of wrapped title'])
    first=candidates[0]
    first['ranges'].append({'revision':'revision','page':2,'start':0,'end':len(source[1]['markdown'])})
    first['original_text']+='\n'+source[1]['markdown']
    group=regions_for([first],evidence[:1],decisions[:1],source)[0]
    assert group['pages']==[1,2]
    assert [x['page'] for x in group['input']['context']]==[1,2]
