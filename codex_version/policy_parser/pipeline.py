"""Current: sequential orchestration of independently implemented parser stages.
Limitations: provisional structural assumptions; no reference answers in inference.
TODO(B5): improve resolver evidence within its own stage.
Acceptance: no-API/replay integration and behavior-preserving refactor tests.
"""
import time
from .models import PageExtraction, RunResult
from .extraction import extract, sha
from .routing import route_pages
from .candidates import candidate_blocks
from .evidence import build_evidence
from .resolver import decide, resolve_regions
from .regions import regions_for, DEFAULT_INPUT_CHARACTERS
from .hierarchy import assemble_hierarchy
from .body import attach_body
from .validation import validate_run

def run_pages(pages: list[PageExtraction], document_hash='synthetic', visual_replays=None, structure_replays=None, debug_overrides=None, region_input_characters=DEFAULT_INPUT_CHARACTERS) -> RunResult:
    started = time.perf_counter()
    timings={}
    def stage(name,fn,*args,**kwargs):
        before=time.perf_counter()
        result=fn(*args,**kwargs)
        timings[name+'_seconds']=time.perf_counter()-before
        return result
    pages, assessments, repairs, override_records, original_revision, revision = stage('routing',route_pages,
        pages, document_hash, visual_replays, debug_overrides)
    candidates = stage('candidates',candidate_blocks,pages, revision)
    evidence = stage('evidence',build_evidence,candidates)
    evidence, decisions = stage('deterministic_resolver',decide,candidates, evidence)
    regions = stage('regions',regions_for,candidates, evidence, decisions, pages,
                    region_input_characters,document_hash,revision)
    responses = stage('structure_provider',resolve_regions,regions, candidates, decisions, document_hash, revision, structure_replays)
    tree, created, hierarchy_errors, missing = stage('hierarchy',assemble_hierarchy,candidates, decisions)
    body = stage('body',attach_body,pages, candidates, decisions, revision, created)
    validation = stage('validation',validate_run,tree, pages, body, decisions, hierarchy_errors, missing, revision)
    validation['structural_complete']=validation['complete']
    validation['unresolved_extraction']=[{'page':a['page'],'reasons':a['reasons'],
                                         'provider_status':repair['status']}
                                        for a,repair in zip(assessments,repairs)
                                        if a['status']!='ACCEPT' and repair['adopted_source']=='p4l']
    validation['complete']=validation['complete'] and not validation['unresolved_extraction']
    timings['total_seconds']=time.perf_counter()-started
    return {'document_hash': document_hash, 'canonical_revision': revision, 'original_revision': original_revision,
            'pages': pages, 'assessments': assessments, 'repairs': repairs, 'debug_overrides':override_records, 'candidates': candidates,
            'evidence': evidence, 'regions': regions, 'decisions': decisions, 'structure_provider': responses,
            'section_index': [d for d in decisions if d['status']=='RESOLVED' and d['role']=='section' and d['candidate_id'] in created],
            'tree': tree, 'body': body, 'validation': validation,
            'timings':timings,
            'limitations': ['Provisional hierarchy/body', 'Incomplete dependency discovery', 'No live inference providers',
                            'No reviewed accuracy claims', 'No confirmed noise removal',
                            'Root document title unresolved; source title retained in preamble',
                            'Enclosing own-text scope resumption unsupported without an explicit boundary']}


def run_pdf(pdf, selected=None, region_input_characters=DEFAULT_INPUT_CHARACTERS):
    started=time.perf_counter()
    pages=extract(pdf, selected)
    elapsed=time.perf_counter()-started
    result=run_pages(pages, sha(pdf), region_input_characters=region_input_characters)
    result['timings']['extraction_seconds']=elapsed
    result['timings']['total_seconds']+=elapsed
    return result
