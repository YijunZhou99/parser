"""General source/hierarchy ownership checks independent of real PDF wording."""
import copy
import pytest
from policy_parser.pipeline import run_pages
from policy_parser.body import attach_body, body_index
from policy_parser.hierarchy import assemble_hierarchy
from policy_parser.validation import validate_run
from policy_parser.candidates import candidate_blocks
from test_structure import pages


@pytest.mark.parametrize('titles',[('Outer','Inner','Peer','Next'),('Alpha','Beta','Gamma','Delta')])
def test_heading_scope_events_close_children_without_duplicating_body(titles):
    a,b,c,d=titles
    run=run_pages(pages(f'# 1 {a}\n\nParent own prose.\n\n## 1.1 {b}\n\nFirst child prose.\n\n## 1.2 {c}\n\nSecond child prose.\n\n# 2 {d}\n\nNext own prose.'))
    outer,next_node=run['tree']['root']['children']
    first,second=outer['children']
    assert 'child prose' not in outer['text']
    event=next(b['boundary'] for b in run['body'] if b['owner']==second['id'] and b['status']=='HEADING')
    assert event['closed_sections']==[first['id']]
    final=next(b['boundary'] for b in run['body'] if b['owner']==next_node['id'] and b['status']=='HEADING')
    assert final['closed_sections']==[second['id'],outer['id']]
    assert not run['validation']['source_errors']


def test_unheaded_prose_does_not_silently_resume_parent():
    run=run_pages(pages('# 1 Parent\n\nOwn parent prose.\n\n## 1.1 Child\n\nChild prose.\n\nUnheaded paragraph with unknown scope intent.'))
    parent=run['tree']['root']['children'][0]; child=parent['children'][0]
    assert 'Unheaded paragraph' not in parent['text'] and 'Unheaded paragraph' in child['text']
    record=next(b for b in run['body'] if 'Unheaded paragraph' in b['text'])
    assert record['scope_path']==['root',parent['id'],child['id']]
    assert record['ancestor_resumption']=='not_inferred'


@pytest.mark.parametrize('before,after,separator',[('word','continuation','\n'),('word\n','continuation',''),('word','\ncontinuation','')])
def test_cross_page_join_is_recorded_without_changing_source(before,after,separator):
    source=pages('# 1 Scope\n\n'+before,after)
    run=run_pages(source)
    own=run['tree']['root']['children'][0]
    record=next(b for b in run['body'] if b['ranges'][0]['page']==2)
    assert record['separator_before']==separator
    assert own['text']=='\n\n'+before+separator+after
    for i,page in enumerate(source):
        assert ''.join(b['text'] for b in run['body'] if b['ranges'][0]['page']==i+1)==page['markdown']
    index=run['body_index'][own['id']]
    assert index['export_characters']==index['source_characters']+index['generated_page_separators']
    assert not run['validation']['source_errors']


def test_skipped_page_does_not_certify_continuation_ownership():
    source=pages('# 1 Scope\n\nInitial body.','Continuation after missing original page.')
    source[1]['page']=3
    run=run_pages(source)
    continued=next(b for b in run['body'] if b['ranges'][0]['page']==3)
    assert continued['ownership']=='provisional'
    assert continued['ownership_reasons']==['UNSELECTED_PAGE_GAP']
    assert not run['validation']['structural_complete']
    assert not run['validation']['source_errors']


def test_supported_heading_after_page_gap_has_known_own_scope():
    source=pages('# 1 First\n\nFirst body.','# 2 Second\n\nSecond body.')
    source[1]['page']=3
    run=run_pages(source)
    assert all(b['ownership']=='source_sliced' for b in run['body'] if b['ranges'][0]['page']==3)


def test_multirange_heading_excludes_both_source_fragments_from_own_text():
    source=pages('## 1.1 Wrapped','heading\n\nOwn prose after heading.')
    c=candidate_blocks(source,'rev')[0]
    c.update(label='1',title='Wrapped heading',original_text='## 1.1 Wrapped\nheading')
    c['ranges'].append({'revision':'rev','page':2,'start':0,'end':len('heading')})
    decision={'candidate_id':c['id'],'role':'section','parent_id':'root','status':'RESOLVED'}
    tree,created,errors,pending=assemble_hierarchy([c],[decision])
    body=attach_body(source,[c],[decision],'rev',created)
    node=tree['root']['children'][0]
    assert node['text']=='\n\nOwn prose after heading.'
    index=body_index(tree,body)[c['id']]
    assert len(index['heading_ranges'])==2
    assert any(b['boundary'] and b['boundary']['reason']=='HEADING_CONTINUATION' for b in body)
    assert not validate_run(tree,source,body,[decision],errors,pending,'rev')['source_errors']


def test_markdown_table_stays_exact_own_text():
    table='| Field | Value |\n| --- | --- |\n| item | 17 |'
    run=run_pages(pages('# 1 Scope\n\n'+table))
    node=run['tree']['root']['children'][0]
    assert table in node['text']
    assert run['body_index'][node['id']]['ownership']=='source_sliced'
    assert not run['validation']['source_errors']


def test_invented_joiner_is_rejected():
    run=run_pages(pages('# 1 Scope\n\nBody.'))
    body=copy.deepcopy(run['body'])
    item=next(b for b in body if b['status']=='ASSIGNED')
    item['separator_before']='invented substantive words'
    result=validate_run(run['tree'],run['pages'],body,run['decisions'],[],[],run['canonical_revision'])
    assert any(e['reason']=='INVALID_GENERATED_SEPARATOR' for e in result['source_errors'])


def test_export_schema_does_not_contain_debug_provenance():
    run=run_pages(pages('# 1 Scope\n\nOwn prose.'))
    assert set(run['tree'])=={'root'}
    assert set(run['tree']['root'])=={'id','label','title','text','depth','children'}
    assert 'body_index' in run and not run['body_index']['root']['verified']
