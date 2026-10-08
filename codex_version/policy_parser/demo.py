"""Current: independent synthetic inputs and replay examples.
Limitations: synthetic data measures invariants, never PDF accuracy.
TODO(B1): replace demonstration evidence with reviewed benchmarks.
Acceptance: no-API and replay integration checks.
"""
from .pipeline import run_pages
from .providers import fingerprint
from .regions import DEFAULT_INPUT_CHARACTERS


def demo_pages():
    return [{'page': 1, 'markdown': '# 1 Scope\n\nOwn parent text.\n\n## 1.1 Detail\n\nChild body.\n\nPossible heading',
             'plain_text': '1 Scope Own parent text. 1.1 Detail Child body. Possible heading', 'blocks': [], 'table_count': 0},
            {'page': 2, 'markdown': 'Continuation.\n\nAnother possible heading\n\nMore body.',
             'plain_text': 'Continuation. Another possible heading More body.', 'blocks': [], 'table_count': 0}]


def demo_run(mode='unavailable', region_input_characters=DEFAULT_INPUT_CHARACTERS):
    pages = demo_pages()
    first = run_pages(pages,region_input_characters=region_input_characters)
    if mode == 'unavailable': return first
    replays = {}
    for response in first['structure_provider']:
        payload = response['input']
        decisions = [{'candidate_id': ident, 'role': 'abstain' if mode=='abstain_replay' else 'body', 'parent_id': None} for ident in payload['candidate_ids']]
        if mode == 'invalid_replay': decisions[0]['candidate_id'] = 'invented-id'
        replays[response['region_id']] = {'kind': 'structure', 'fingerprint': fingerprint(payload), 'response': decisions}
    return run_pages(pages, structure_replays=replays,region_input_characters=region_input_characters)
