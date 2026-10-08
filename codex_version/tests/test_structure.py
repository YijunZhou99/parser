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
