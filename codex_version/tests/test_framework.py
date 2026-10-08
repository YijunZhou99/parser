"""Focused Track A invariants, not parser-quality certification."""
import json
import pytest
from policy_parser.demo import demo_run, demo_pages
from policy_parser.pipeline import run_pages
from policy_parser.candidates import candidate_blocks
from policy_parser.resolver import validate_response
from policy_parser.providers import request, fingerprint
from policy_parser.reconciliation import reconcile
from policy_parser.validation import validate_tree
from policy_parser.evaluation import compare


def test_schema_ids_depths():
    tree = demo_run()['tree']
    assert not validate_tree(tree)
    tree['root']['children'][0]['depth']=9
    assert validate_tree(tree)
    tree['root']['children'][0]['id']='root'
    assert any('duplicate' in e for e in validate_tree(tree))


def test_deterministic_and_spans():
    a,b = demo_run(),demo_run()
    assert a['candidates']==b['candidates']
    for c in a['candidates']:
        s = c['ranges'][0]
        md=next(p['markdown'] for p in a['pages'] if p['page']==s['page'])
        assert md[s['start']:s['end']]==c['original_text']


def test_conflict_and_uncertain_roles():
    pages=demo_pages(); pages[0]['markdown']='## 1 Conflict\n\n**Formatting only**\n\n(i) Ambiguous'
    run=run_pages(pages)
    assert 'EVIDENCE_CONFLICT' in run['decisions'][0]['reasons']
    assert all(d['status']=='AMBIGUOUS' for d in run['decisions'])
    assert any(c['label_grammar']=='ambiguous' for c in run['candidates'])


def test_cross_page_and_unavailable():
    run=demo_run()
    assert any(r['pages']==[1,2] for r in run['regions'])
    assert all(p['status']=='unavailable' for p in run['structure_provider'])
    assert run['validation']['pending']


def test_replay_valid_invalid():
    good,bad=demo_run('valid_replay'),demo_run('invalid_replay')
    assert all(r['status']=='returned' for r in good['structure_provider'])
    assert not good['validation']['pending']
    assert all(r['status']=='rejected' for r in bad['structure_provider'])
    assert bad['validation']['pending']


def test_provider_atomic_validation():
    assert validate_response([{'candidate_id':'no','role':'body'}],['a'],[],{})
    assert validate_response([{'candidate_id':'a','role':'section','parent_id':'b'},
                              {'candidate_id':'b','role':'section','parent_id':'a'}],['a','b'],[],{})==['Cycle']
    assert request('structure',{'revision':'new'},{'kind':'structure','fingerprint':fingerprint({'revision':'old'})})['status']=='rejected'
    assert validate_response([{'candidate_id':[],'role':'body'}],['a'],[],{})


def test_body_conservation_nonduplication():
    run=demo_run()
    assert not run['validation']['source_errors']
    for page in run['pages']:
        parts=[b['text'] for b in run['body'] if b['ranges'][0]['page']==page['page']]
        assert ''.join(parts)==page['markdown']
    parent=run['tree']['root']['children'][0]
    assert 'Child body' not in parent['text']
    assert 'Child body' in parent['children'][0]['text']


def test_reconciliation_negation_order():
    assert not reconcile('Must not do X','Must do X',True)['adopted']
    assert reconcile('A B A','A A B',True)['adopted']
    assert not reconcile('A B A','A B',True)['adopted']


def test_visual_replay_revision_and_manual_override():
    pages=[{'page':1,'markdown':'A B A','plain_text':'','blocks':[], 'table_count':0}]
    first=run_pages(pages)
    payload=first['repairs'][0]['input']
    replay={1:{'kind':'visual','fingerprint':fingerprint(payload),
               'response':{'markdown':'A A B','synthetic_order_only':True}}}
    repaired=run_pages(pages,visual_replays=replay)
    assert repaired['canonical_revision']!=first['canonical_revision']
    assert repaired['repairs'][0]['reconciliation']['adopted']
    override=run_pages(pages,debug_overrides={1:'Changed text'})
    assert override['debug_overrides'][0]['origin']=='manual_debug_override'
    assert override['canonical_revision']!=first['canonical_revision']


def test_reference_repeated_titles_and_ai_label():
    run=demo_run(); ref=json.loads(json.dumps(run['tree']))
    ref['root']['children'].append(dict(ref['root']['children'][0],id='other'))
    # Avoid duplicate descendant editing IDs.
    ref['root']['children'][-1]['children']=[]
    result=compare(run,ref,{'annotation_status':'ai_unreviewed'})
    assert result['comparison']=='against AI draft reference'
    assert result['verified_parser_accuracy'] is False
    assert result['matches'][0]['prediction_id'] is None
    assert result['generator_recall'] is None


def test_inference_never_imports_reference_answers():
    import inspect
    from policy_parser import pipeline
    source=inspect.getsource(pipeline)
    assert 'silver' not in source and 'golden' not in source


def test_planned_stage_boundaries():
    import ast
    from pathlib import Path
    from policy_parser import pipeline
    import inspect
    package=Path(inspect.getfile(pipeline)).parent
    stages=('models','pipeline','extraction','routing','reconciliation','candidates',
            'labels','evidence','resolver','regions','providers','hierarchy','body',
            'validation','evaluation')
    assert all((package/f'{name}.py').exists() for name in stages)
    functions={n.name for n in ast.parse(inspect.getsource(pipeline)).body if isinstance(n,ast.FunctionDef)}
    assert functions=={'run_pages','run_pdf'}
    # References stay outside the orchestration/provider/decision stages.
    for name in ('pipeline','routing','providers','resolver','candidates','evidence','hierarchy','body'):
        imports=[n.module for n in ast.parse((package/f'{name}.py').read_text(encoding='utf-8')).body if isinstance(n,ast.ImportFrom)]
        assert 'evaluation' not in imports


def test_evidence_observations_and_separate_decisions():
    from policy_parser.evidence import build_evidence
    from policy_parser.resolver import decide
    candidates=candidate_blocks(demo_pages(),'test-revision')
    observations=build_evidence(candidates)
    assert all('role' not in e and 'status' not in e for e in observations)
    evidence,decisions=decide(candidates,observations)
    assert len(evidence)==len(decisions)==len(candidates)
    assert decisions[0]['status']=='RESOLVED'
    assert decisions[-1]['status']=='AMBIGUOUS'


def test_real_pdf_no_api():
    import pymupdf
    from policy_parser.pipeline import run_pdf
    doc=pymupdf.open(); p=doc.new_page(); p.insert_text((72,72),'1 Scope\nThis is synthetic PDF source.')
    result=run_pdf(doc.tobytes(),[1]); doc.close()
    assert result['pages'][0]['source_engine']=='pymupdf4llm'
    assert not result['validation']['schema_errors']


def test_streamlit_workflows():
    from streamlit.testing.v1 import AppTest
    from pathlib import Path
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    assert not app.exception
    assert len(app.tabs)==11
    app.sidebar.selectbox[1].select('valid_replay')
    app.sidebar.button[0].click().run(timeout=30)
    assert not app.exception
    assert not app.session_state['run']['validation']['pending']
    app.sidebar.selectbox[1].select('invalid_replay')
    app.sidebar.button[0].click().run(timeout=30)
    assert not app.exception
    assert app.session_state['run']['validation']['pending']
    app.sidebar.selectbox[1].select('abstain_replay')
    app.sidebar.button[0].click().run(timeout=30)
    assert not app.exception
    assert all(r['abstained'] for r in app.session_state['run']['structure_provider'])


def test_local_packet_reviewer_and_reference_import(tmp_path, monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    import bootstrap
    base=Path(__file__).parents[1]
    app=AppTest.from_file(str(base/'app.py')).run(timeout=30)
    app.sidebar.selectbox[0].select('Employee-Handbook')
    app.sidebar.button[0].click().run(timeout=60)
    assert not app.exception
    assert len(app.session_state['run']['pages'])==6
    # Test import using a synthetic source, never labeling an actual PDF as generated.
    import pymupdf
    from policy_parser.extraction import sha
    doc=pymupdf.open(); doc.new_page(); pdf=doc.tobytes(); doc.close()
    (tmp_path/'source.pdf').write_bytes(pdf)
    folder=tmp_path/'sample'; folder.mkdir()
    meta={'source_path':'source.pdf','source_sha256':sha(pdf),'selected_pages':[1], 'annotation_status':'pending_external_generation'}
    (folder/'metadata.json').write_text(json.dumps(meta))
    (folder/'source-text.json').write_text(json.dumps([{'plain_text':'Scope'}]))
    draft=tmp_path/'draft.json'; draft.write_text(json.dumps({'root':{'id':'root','label':'','title':'Scope','text':'','depth':0,'children':[]}}))
    note=tmp_path/'notes.md'; note.write_text('Synthetic import test; no live generation.')
    monkeypatch.setattr(bootstrap,'BASE',tmp_path/'code')
    bootstrap.import_silver(folder,draft,'synthetic-import-test',note)
    assert json.loads((folder/'metadata.json').read_text())['annotation_status']=='ai_unreviewed'
    assert (folder/'silver-checks.json').exists()
    with pytest.raises(ValueError,match='refusing overwrite'):
        bootstrap.import_silver(folder,draft,'synthetic-import-test',note)


def test_accessibility_reviewer_shows_resolved_outline():
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    sample=next(x for x in app.sidebar.selectbox[0].options if x.startswith('M-24'))
    app.sidebar.selectbox[0].select(sample)
    app.sidebar.button[0].click().run(timeout=60)
    assert not app.exception
    run=app.session_state['run']
    assert len(run['section_index'])==6
    assert [n['label'] for n in run['tree']['root']['children']]==['I.','II.','III.']
    assert any('INTRODUCTION' in item.value for item in app.text)
    assert run['timings']['extraction_seconds']>=0


def test_reviewer_region_budget_skips_provider_and_retains_uncertainty():
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    app.sidebar.number_input[1].set_value(1)
    app.sidebar.button[0].click().run(timeout=30)
    assert not app.exception
    run=app.session_state['run']
    assert run['validation']['pending']
    assert all(r['budget_status']=='oversized' and r['coverage']['all_candidates_included'] for r in run['regions'])
    assert all(p['status']=='skipped' for p in run['structure_provider'])
