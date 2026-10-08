"""Whole-run debugging comparisons do not establish correctness."""
from copy import deepcopy
from policy_parser.pipeline import run_pages
from policy_parser.evaluation import compare_runs
from test_structure import pages


def test_body_change_and_baseline_preserved():
    source = pages('# 1 Scope\n\nOriginal body.\n\n# 2 Duties\n\nOther body.')
    automatic = run_pages(source, document_hash='same-pdf')
    before = deepcopy(automatic)
    manual = run_pages(source, document_hash='same-pdf', debug_overrides={
        1: source[0]['markdown'].replace('Original body.', 'Changed body.')})
    result = compare_runs(automatic, manual)
    assert automatic == before
    assert result['verified_parser_accuracy'] is False
    assert any('own_text' in c['fields'] for c in result['changes'])
    assert result['page_changes'][0]['page'] == 1
    assert result['revisions']['automatic'] != result['revisions']['manual']


def test_changed_heading_unmatched_and_hash_guard():
    source = pages('# 1 Scope\n\nBody.\n\n# 2 Duties\n\nOther.')
    automatic = run_pages(source, document_hash='same')
    manual = run_pages(source, document_hash='same', debug_overrides={
        1: source[0]['markdown'].replace('Scope', 'Coverage')})
    assert compare_runs(automatic, manual)['unmatched']
    manual['document_hash'] = 'different'
    assert 'error' in compare_runs(automatic, manual)


def test_repeated_identity_is_not_aligned():
    run = run_pages(pages('# 1 Scope\n\nBody.\n\n# 2 Duties\n\nOther.'))
    duplicate = deepcopy(run['tree']['root']['children'][0])
    duplicate['id'] = 'duplicate'
    run['tree']['root']['children'].append(duplicate)
    run['candidates'].append(dict(run['candidates'][0], id='duplicate'))
    result = compare_runs(run, deepcopy(run))
    assert any(len(item['automatic']) == 2 for item in result['unmatched'])


def test_reviewer_preserves_and_switches_runs():
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    baseline = deepcopy(app.session_state['automatic_run'])
    app.text_area(key='debug_proposal').set_value(baseline['pages'][0]['markdown'] + '\nDebug text.')
    app.checkbox[0].check().run(timeout=30)
    next(b for b in app.button if b.label == 'Accept proposal and rebuild (debug)').click().run(timeout=30)
    assert not app.exception
    assert app.session_state['automatic_run'] == baseline
    assert app.session_state['manual_run']['canonical_revision'] != baseline['canonical_revision']
    next(b for b in app.button if b.label == 'Display automatic baseline').click().run(timeout=30)
    assert app.session_state['run'] == baseline
    next(b for b in app.button if b.label == 'Display manual debug run').click().run(timeout=30)
    assert app.session_state['run'] == app.session_state['manual_run']
