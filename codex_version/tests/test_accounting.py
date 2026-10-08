"""No-API recovery, accounting and alignment edge cases."""
import copy
import json
import pytest
from policy_parser.pipeline import run_pages
from policy_parser.demo import demo_run
from policy_parser.validation import validate_run
from policy_parser.evaluation import compare
from policy_parser.hierarchy import assemble_hierarchy
from policy_parser.routing import assess
from policy_parser.models import nodes
from test_structure import pages


def test_tight_headings_and_wrapped_title_keep_body():
    run=run_pages(pages('# 1 Scope\nOwn body text on next line.\n## **1.1 Wrapped\nheading**\nChild body on next line.'))
    parent=run['tree']['root']['children'][0]
    assert parent['title']=='Scope'
    assert parent['children'][0]['title']=='Wrapped\nheading'
    assert 'Own body text' in parent['text']
    assert 'Child body' in parent['children'][0]['text']
    assert not run['validation']['source_errors']


def test_fenced_code_headings_not_sections():
    run=run_pages(pages('```text\n# 1 Code example\n## 1.1 Code child\n```'))
    assert not run['section_index']


def test_uncertainty_stops_at_supported_scope_boundary():
    run=run_pages(pages('Possible preamble heading\n\n# 1 Scope\n\nDefinite body after scope.'))
    assert run['validation']['outstanding_ownership']
    assert all(b['ownership']=='source_sliced' for b in run['body'] if b['owner']!='root')
    assert ''.join(b['text'] for b in run['body'])==run['pages'][0]['markdown']


def test_source_revision_text_and_own_text_validation():
    run=demo_run()
    changed=copy.deepcopy(run['body'])
    item=next(b for b in changed if b['status']=='ASSIGNED')
    item['ranges'][0]['revision']='stale'
    item['text']='invented'
    result=validate_run(run['tree'],run['pages'],changed,run['decisions'],[],[],run['canonical_revision'])
    assert {'STALE_SOURCE_REVISION','SOURCE_TEXT_MISMATCH','OWN_TEXT_MISMATCH'} <= {e['reason'] for e in result['source_errors']}
    assert not result['complete']


def test_failed_extraction_is_visible_and_not_complete(monkeypatch):
    import pymupdf
    import policy_parser.extraction as extraction
    from policy_parser.pipeline import run_pdf
    doc=pymupdf.open(); p=doc.new_page(); p.insert_text((72,72),'Real text layer remains available.')
    data=doc.tobytes(); doc.close()
    def fail(*args,**kwargs): raise RuntimeError('synthetic extraction failure')
    monkeypatch.setattr(extraction.pymupdf4llm,'to_markdown',fail)
    run=run_pdf(data,[1])
    assert run['pages'][0]['extraction_status']=='failed'
    assert 'EXTRACTION_FAILED' in run['assessments'][0]['reasons']
    assert run['repairs'][0]['status']=='unavailable'
    assert not run['validation']['complete']
    assert run['validation']['extraction_failures']==[1]


def test_replacement_characters_are_recovery_evidence():
    result=assess(pages('Some \ufffd corrupted text')[0])
    assert result['status']=='NEEDS_VISUAL'
    assert 'UNDECODABLE_CHARACTERS' in result['reasons']


def test_empty_scan_is_not_reported_complete_when_provider_unavailable():
    run=run_pages([{'page':1,'markdown':'','plain_text':'','blocks':[],'table_count':0}])
    assert run['assessments'][0]['status']=='UNVERIFIABLE'
    assert run['validation']['structural_complete']
    assert not run['validation']['complete']
    assert run['validation']['unresolved_extraction'][0]['provider_status']=='unavailable'


def test_global_hierarchy_quarantines_cycles():
    run=demo_run(); candidates=run['candidates'][:2]; a,b=[c['id'] for c in candidates]
    decisions=[{'candidate_id':a,'role':'section','status':'RESOLVED','parent_id':b},
               {'candidate_id':b,'role':'section','status':'RESOLVED','parent_id':a}]
    tree,created,errors,pending=assemble_hierarchy(candidates,decisions)
    assert not tree['root']['children']
    assert set(pending)=={a,b}
    assert all(e['reason']=='CYCLE' for e in errors)


def test_repeated_titles_use_confirmed_pdf_alignment():
    prose=' '.join(['body']*15)+'.'
    run=run_pages(pages(f'# Scope\n\n{prose}', f'# Scope\n\n{prose}'))
    reference=copy.deepcopy(run['tree'])
    alignment={}
    for i,(n,c) in enumerate(zip(reference['root']['children'],run['candidates'])):
        n['id']=f'ref-{i}'
        alignment[n['id']]={'pages':[c['page']],'heading_text':c['original_text'],'confirmed':True}
    unaligned=compare(run,reference,{'annotation_status':'ai_unreviewed'})
    assert unaligned['confirmed_matches']==0
    aligned=compare(run,reference,{'annotation_status':'ai_unreviewed'},alignment)
    assert aligned['confirmed_matches']==2
    assert aligned['parent_accuracy']==1
    assert aligned['verified_parser_accuracy'] is False
    assert aligned['own_text_accuracy'] is None
    for link in alignment.values(): link.update(canonical_revision='stale',start=0)
    stale=compare(run,reference,{},alignment)
    assert stale['confirmed_matches']==0 and stale['end_to_end_candidate_recall'] is None


def test_abstention_and_deterministic_region_order():
    run=demo_run('abstain_replay')
    assert run['validation']['pending']
    assert all(r['status']=='returned' and r['abstained'] for r in run['structure_provider'])
    assert demo_run()['regions']==demo_run()['regions']


def test_evaluation_confirmed_missing_and_generator_denominator():
    run=run_pages(pages('# 1 Scope\n\nOwn body.'))
    reference=copy.deepcopy(run['tree'])
    reference['root']['children'][0]['id']='ref-scope'
    reference['root']['children'].append({'id':'missing','label':'2','title':'Lost heading','text':'','depth':1,'children':[]})
    alignment={'ref-scope':{'pages':[1],'heading_text':'# 1 Scope','confirmed':True,'markdown_presence_confirmed':True,'markdown_presence':'present','own_text_confirmed':True},
               'missing':{'pages':[1],'heading_text':'2 Lost heading','confirmed':True,'markdown_presence_confirmed':True,'markdown_presence':'absent'}}
    result=compare(run,reference,{'annotation_status':'ai_unreviewed'},alignment)
    assert result['end_to_end_candidate_recall']==0.5
    assert result['generator_recall']==1 and result['generator_denominator']==1
    assert result['miss_attribution']==[{'reference_id':'missing','stage':'extraction'}]
    assert result['own_text_accuracy']['exact']==1
    assert result['verified_parser_accuracy'] is False
    alignment['missing']['markdown_presence']='present'
    result=compare(run,reference,{},alignment)
    assert result['generator_recall']==0.5
    assert result['miss_attribution'][0]['stage']=='candidate_generation'
