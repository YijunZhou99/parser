"""Contextual resolver checks; no human-reference accuracy claims."""
import json
from pathlib import Path
from policy_parser.pipeline import run_pages
from policy_parser.labels import interpretations, roman_value
from policy_parser.evidence import build_evidence
from policy_parser.candidates import candidate_blocks


def pages(*texts):
    return [{'page':i+1,'markdown':text,'plain_text':text,'blocks':[], 'table_count':0}
            for i,text in enumerate(texts)]


def test_cross_page_roman_alpha_tree():
    run=run_pages(pages('Letterhead\n\n## Decorative title\n\n# **I. Scope**\n\nScope body.\n\n# **II. Requirements**\n\nParent own text.',
                        '# **A. First child**\n\nFirst child body.\n\n# **B. Second child**\n\nSecond child body.'))
    root=run['tree']['root']
    assert [n['label'] for n in root['children']]==['I.','II.']
    parent=root['children'][1]
    assert [n['label'] for n in parent['children']]==['A.','B.']
    assert 'First child body' not in parent['text']
    assert not run['validation']['source_errors']


def test_single_alpha_child_under_confirmed_roman_context():
    prose = 'This paragraph supplies ordinary explanatory text following the subsection heading for this document.'
    run = run_pages(pages(f'# I. Overview\n\n# A. Single child\n\n{prose}\n\n# II. Rules'))
    first = run['tree']['root']['children'][0]
    assert first['children'][0]['label']=='A.'
    assert first['children'][0]['text'].strip()==prose


def test_single_alpha_requires_context_and_prose():
    for text in ('# A. Isolated\n\nSome text.', '# I. Overview\n\n# A. Single\n\n# II. Rules'):
        run = run_pages(pages(text))
        candidate = next(c for c in run['candidates'] if c['label']=='A.')
        decision = next(d for d in run['decisions'] if d['candidate_id']==candidate['id'])
        assert decision['role_uncertain']


def test_numeric_one_to_nine_top_level_and_nested():
    for delimiter in ('bare', '.', ')', 'parenthesized'):
        def label(n):
            return f'({n})' if delimiter=='parenthesized' else str(n)+(delimiter if delimiter!='bare' else '')
        numbers = '\n\n'.join(f'# {label(n)} Item {n}\n\nBody for item {n}.' for n in range(1,10))
        root = run_pages(pages(numbers))['tree']['root']
        assert [c['label'] for c in root['children']]==[label(n) for n in range(1,10)]
        run = run_pages(pages('# I. Part\n\n# A. Topic\n\n'+numbers+'\n\n# B. Next topic\n\n# II. Next part'))
        parent = run['tree']['root']['children'][0]
        assert [c['label'] for c in parent['children']]==['A.', 'B.']
        assert [c['label'] for c in parent['children'][0]['children']]==[label(n) for n in range(1,10)]
        assert not run['validation']['source_errors']


def test_page_numbers_are_not_numeric_sections():
    run = run_pages(pages('1\n\nText.', '2\n\nText.', '9\n\nText.'))
    assert not run['section_index']
    assert all(d['role']=='body' for d in run['decisions'] if 'EXPLICIT_BODY_SYNTAX' in d['reasons'])


def test_isolated_i_and_dual_interpretation_remain_unresolved():
    assert len(interpretations('(i)'))==2
    run=run_pages(pages('## (i) Isolated heading\n\nSome body.'))
    assert not run['section_index']
    assert run['decisions'][0]['role_uncertain']
    assert roman_value('IIII') is None


def test_unknown_intervening_ancestor_is_not_deleted():
    run=run_pages(pages('# 1 Parent\n\n**Possible enclosing section**\n\n### 1.1.1 Child'))
    child=run['decisions'][-1]
    assert child['status']=='AMBIGUOUS'
    assert 'PARENT_UNCERTAIN' in child['reasons']
    assert len(run['tree']['root']['children'])==1


def test_numbering_closed_scope_conflict():
    run=run_pages(pages('# 1 First\n\n# 2 Second\n\n## 1.1 Late child of first'))
    assert run['decisions'][-1]['status']=='AMBIGUOUS'
    assert 'NUMBERED_SCOPE_CONFLICT' in run['decisions'][-1]['reasons']


def test_unheaded_repeated_markdown_with_prose_and_body_syntax():
    paragraph=' '.join(['ordinary']*15)+'.'
    run=run_pages(pages(f'# Scope\n\n{paragraph}\n\n# Requirements\n\n{paragraph}\n\n> Short quoted text'))
    assert [n['title'] for n in run['tree']['root']['children']]==['Scope','Requirements']
    quote=run['decisions'][-1]
    assert quote['role']=='body' and quote['status']=='RESOLVED'


def test_evidence_not_mutated_by_resolver():
    from copy import deepcopy
    from policy_parser.resolver import decide
    candidates=candidate_blocks(pages('# I. First\n\n# II. Second'),'revision')
    evidence=build_evidence(candidates); before=deepcopy(evidence)
    decide(candidates,evidence)
    assert evidence==before


def test_truncated_sequence_preserves_supported_role_and_unknown_parent():
    run=run_pages(pages('# IV. Fourth\n\n# V. Fifth'))
    assert all(d['role']=='section' and not d['role_uncertain'] and d['parent_uncertain'] for d in run['decisions'])
    assert not run['section_index']


def test_accessibility_slice_structure_without_reference_answers():
    base=Path(__file__).parents[1]
    packet=next((base/'benchmarks').glob('M-24*/source-text.json'))
    source=json.loads(packet.read_text(encoding='utf-8'))
    run=run_pages(source,'real-source-test')
    root=run['tree']['root']
    assert [n['label'] for n in root['children']]==['I.','II.','III.']
    assert [n['label'] for n in root['children'][-1]['children']]==['A.','B.','C.']
    assert len(run['section_index'])==6
    assert not run['validation']['source_errors']


def test_repeated_margin_does_not_block_cross_page_siblings():
    margin = 'EXAMPLE ORGANIZATION | DOCUMENT SERIES'
    run = run_pages(pages(f'{margin}\n\n# I. Overview\n\n# II. Rules\n\n# A. First\n\nFirst body.',
                          f'{margin}\n\n# B. Second\n\nSecond body.',
                          f'{margin}\n\n# **C. Third**<sup>**<u>iv</u>**</sup>\n\nThird body.'))
    parent = run['tree']['root']['children'][-1]
    assert [c['label'] for c in parent['children']] == ['A.', 'B.', 'C.']
    assert 'Second body.' not in parent['children'][0]['text']
    assert 'Second body.' in parent['children'][1]['text']
    assert parent['children'][2]['title'] == 'Third'
    assert any('<sup>' in c['original_text'] for c in run['candidates'])
    assert not run['validation']['source_errors']


def test_repetition_inside_pages_is_not_margin_evidence():
    run = run_pages(pages(*['Opening paragraph.\n\nPossible enclosing heading\n\n## 1.1 Detail']*3))
    middle = [c for c in run['candidates'] if c['title']=='Possible enclosing heading']
    assert middle and all('repeated_page_margin' not in c['signals'] for c in middle)
    assert any(d['parent_uncertain'] for d in run['decisions'] if d['role']=='section')


def test_explicit_repeated_headings_not_suppressed_and_two_pages_insufficient():
    source = pages(*['# A. Scope\n\nBody.']*3)
    assert all('repeated_page_margin' not in c['signals'] for c in candidate_blocks(source, 'r'))
    source = pages(*['Possible heading\n\n# 1 Scope\n\nBody.']*2)
    assert all('repeated_page_margin' not in c['signals'] for c in candidate_blocks(source, 'r'))


def test_nonprofit_slice_has_separate_b_and_c_own_text():
    packet = Path(__file__).parents[1]/'benchmarks/Employee-Handbook-for-Nonprofits-and-Small-Businesses/source-text.json'
    run = run_pages(json.loads(packet.read_text(encoding='utf-8')))
    first = next(n for n in run['tree']['root']['children'] if n['label']=='I.')
    assert first['children'][0]['title']=='The Organization'
    parent = next(n for n in run['tree']['root']['children'] if n['label']=='II.')
    a,b,c = parent['children']
    assert [n['label'] for n in (a,b,c)] == ['A.', 'B.', 'C.']
    assert 'is an equal opportunity employer' in b['text']
    assert 'is an equal opportunity employer' not in a['text']
    assert 'committed to maintaining an environment' in c['text']
    assert 'committed to maintaining an environment' not in b['text']
    assert not run['validation']['source_errors']
