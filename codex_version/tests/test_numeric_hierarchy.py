"""Numeric scope regressions use arbitrary titles, without reference answers."""
from policy_parser.pipeline import run_pages
from test_structure import pages


def test_nested_numeric_paths_with_flattened_and_absolute_markdown():
    for levels in ((1,1,1,1,1), (1,2,3,4,5)):
        roman,alpha,one,child,grandchild = levels
        text = '\n\n'.join([
            '#' * roman+' I. Part', '#' * alpha+' A. Topic',
            '#' * one+' 1 First', 'First own body.',
            '#' * child+' 1.1 Detail', 'Detail own body.',
            '#' * grandchild+' 1.1.1 Deep', 'Deep body.',
            '#' * child+' 1.2 Other detail', 'Other detail body.',
            '#' * one+' 2 Second', 'Second body.',
            '#' * alpha+' B. Next topic', '#' * roman+' II. Next part'])
        run = run_pages(pages(text))
        a = run['tree']['root']['children'][0]['children'][0]
        assert [n['label'] for n in a['children']]==['1','2']
        one_node = a['children'][0]
        assert [n['label'] for n in one_node['children']]==['1.1','1.2']
        assert one_node['children'][0]['children'][0]['label']=='1.1.1'
        assert 'Deep body.' not in one_node['text']
        assert 'First own body.' in one_node['text']
        assert not run['validation']['schema_errors']
        assert not run['validation']['source_errors']


def test_numeric_restart_in_new_alpha_scope_cross_page():
    run = run_pages(pages('# I. Part\n\n# A. One\n\n# 1 First\n\n# 1.1 Detail\n\n# 2 Second',
                          '# B. Two\n\n# 1 Restart\n\n# 1.1 New detail\n\n# II. Next'))
    a,b = run['tree']['root']['children'][0]['children']
    assert [n['label'] for n in a['children']]==['1','2']
    assert b['children'][0]['children'][0]['title']=='New detail'
    assert not run['validation']['source_errors']


def test_closed_prefix_cannot_be_reused_in_new_scope():
    run = run_pages(pages('# I. Part\n\n# A. One\n\n# 1 First\n\n# 2 Second\n\n# B. Two\n\n## 1.1 Orphan\n\n# II. Next'))
    orphan = next(c for c in run['candidates'] if c['title']=='Orphan')
    decision = next(d for d in run['decisions'] if d['candidate_id']==orphan['id'])
    assert decision['parent_uncertain']
    assert 'NUMBERED_SCOPE_CONFLICT' in decision['reasons']


def test_restart_in_same_scope_is_uncertain():
    run = run_pages(pages('# 1 First\n\n# 2 Second\n\n# 1 Restart'))
    assert run['decisions'][-1]['status']=='AMBIGUOUS'
    assert 'NUMERIC_RESTART_WITHOUT_NEW_SCOPE' in run['decisions'][-1]['reasons']
    nested = run_pages(pages('# 1 First\n\n## 1.1 Detail\n\n## 1.2 Other\n\n## 1.1 Repeated'))
    assert 'NUMERIC_RESTART_WITHOUT_NEW_SCOPE' in nested['decisions'][-1]['reasons']
    truncated = run_pages(pages('# I. Part\n\n# A. One\n\n# 1 First\n\n# B. Two\n\n# 2 Missing restart\n\n# II. Next'))
    decision = next(d for c,d in zip(truncated['candidates'],truncated['decisions']) if c['title']=='Missing restart')
    assert 'NUMERIC_START_UNANCHORED' in decision['reasons'] and decision['parent_uncertain']


def test_numbered_lists_do_not_supply_sections_or_heading_peers():
    run = run_pages(pages('# 1 Scope\n\n1. First task\n2. Second task\n\n# 2 Duties\n\n1. Separate task\n\n2. Another task'))
    assert [n['title'] for n in run['tree']['root']['children']]==['Scope','Duties']
    assert all(d['role']!='section' for c,d in zip(run['candidates'],run['decisions']) if not c['markdown_level'])
    assert '1. First task' in run['tree']['root']['children'][0]['text']
    assert not run['validation']['source_errors']
