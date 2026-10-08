"""Current: cached-run Streamlit Reviewer for all Track A stage outputs.
Limitations: comparisons require manual alignment; no verified real accuracy.
TODO(B1/B11): reviewed benchmark alignment and integrated PDF annotation.
Acceptance: Streamlit AppTest upload-independent demo, replay and stage rendering.
"""
import json
from pathlib import Path
import streamlit as st
from policy_parser.pipeline import run_pdf, run_pages
from policy_parser.demo import demo_run
from policy_parser.extraction import render, sha
from policy_parser.evaluation import compare
from policy_parser.validation import validate_tree

BASE = Path(__file__).parent
st.set_page_config(page_title='Policy Parser Reviewer', layout='wide')
st.title('Policy Parser Reviewer — Track A')
st.caption('Provisional output. AI drafts and synthetic fixtures do not establish verified parser accuracy.')
pdf_upload = st.sidebar.file_uploader('PDF', type=['pdf'])
local = st.sidebar.selectbox('Local review packet', ['None'] + [p.name for p in sorted((BASE/'benchmarks').glob('*')) if p.is_dir()])
reference_upload = st.sidebar.file_uploader('Silver / golden JSON', type=['json'])
metadata_upload = st.sidebar.file_uploader('Reference metadata JSON', type=['json'])
alignment_upload = st.sidebar.file_uploader('Confirmed alignment JSON (optional)', type=['json'])
mode = st.sidebar.selectbox('Synthetic demo provider', ['unavailable', 'valid_replay', 'invalid_replay', 'abstain_replay'])
limit = st.sidebar.number_input('Selected first pages', 1, 5000, 6)
region_budget=st.sidebar.number_input('Region input budget (JSON characters, not tokens)',1,1000000,20000)
reference, metadata, alignment, pdf = None, {}, None, None
input_errors = []
def load(upload):
    if upload is None: return None
    try: return json.loads(upload.getvalue())
    except (ValueError, UnicodeError) as exc: input_errors.append(str(exc)); return None
if pdf_upload: pdf = pdf_upload.getvalue()
if local != 'None' and not pdf_upload:
    folder = BASE/'benchmarks'/local
    metadata = json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
    path = BASE.parent/metadata['source_path']
    if path.exists(): pdf = path.read_bytes()
    for name in ('silver.json', 'golden.json'):
        if (folder/name).exists():
            reference = json.loads((folder/name).read_text(encoding='utf-8'))
            if name == 'golden.json':
                reviewed_metadata = folder/'golden.metadata.json'
                metadata = json.loads(reviewed_metadata.read_text(encoding='utf-8')) if reviewed_metadata.exists() else dict(metadata, annotation_status='unreviewed')
            break
    if (folder/'alignment.json').exists(): alignment = json.loads((folder/'alignment.json').read_text(encoding='utf-8'))
if reference_upload: reference = load(reference_upload)
if metadata_upload: metadata = load(metadata_upload) or {}
if alignment_upload: alignment = load(alignment_upload)
if not isinstance(metadata, dict): input_errors.append('Metadata must be a JSON object'); metadata = {}
if alignment is not None and (not isinstance(alignment, dict) or any(not isinstance(v,dict) for v in alignment.values())):
    input_errors.append('Alignment must map node IDs to JSON objects'); alignment = None
for error in input_errors: st.error(error)
st.sidebar.json({'annotation_status': metadata.get('annotation_status', 'no reference'),
                 'provider': 'unavailable for real PDFs', 'reference_generation': 'separate import command'})
signature = (sha(pdf) if pdf else 'synthetic', int(limit), mode,int(region_budget))
if st.sidebar.button('Run / Re-run', type='primary') or 'run' not in st.session_state:
    try:
        if pdf:
            import pymupdf
            with pymupdf.open(stream=pdf, filetype='pdf') as doc: selected = list(range(1,min(len(doc),int(limit))+1))
            st.session_state.run = run_pdf(pdf, selected,region_input_characters=int(region_budget))
        else: st.session_state.run = demo_run(mode,region_input_characters=int(region_budget))
        st.session_state.signature = signature
        st.session_state.debug_base_pages=st.session_state.run['pages']
        st.session_state.debug_overrides={}
    except Exception as exc: st.error(f'Run failed: {exc}')
if 'run' not in st.session_state: st.stop()
run = st.session_state.run
if signature != st.session_state.signature:
    st.warning('Inputs changed. Click Run / Re-run. Displayed results belong to the previous run.')
if not pdf: st.info('Synthetic Markdown demo. This is not a real-document accuracy benchmark.')
if reference:
    for problem in validate_tree(reference): st.error(problem)
    if metadata.get('source_sha256') != run['document_hash']:
        st.warning('Reference hash does not match this run; comparison disabled.')
    if metadata.get('selected_pages') != [p['page'] for p in run['pages']]:
        st.warning('Reference page selection does not match this run; comparison disabled.')
tabs = st.tabs(['Source','Markdown','Extraction/Router','Candidates','Evidence','Regions','Decisions','Tree','Body','Quality','Evaluation'])
with tabs[0]:
    st.json(metadata)
    selected_page = st.selectbox('Original page', [p['page'] for p in run['pages']])
    if pdf and st.session_state.signature == signature: st.image(render(pdf, selected_page))
    else: st.caption('Original PDF unavailable for this displayed synthetic/stale run.')
with tabs[1]:
    st.caption(f'Canonical revision: {run["canonical_revision"]}')
    for p in run['pages']:
        st.subheader(f'Original page {p["page"]}'); st.code(p['markdown'], language='markdown')
with tabs[2]:
    st.json({'assessments':run['assessments'], 'recovery':run['repairs'], 'debug_overrides':run['debug_overrides']})
    st.caption('Debug overrides are explicit manual actions, not automatic repair or reviewed annotations.')
    debug_page = st.selectbox('Debug repair original page', [p['page'] for p in run['pages']])
    if st.button('Request repair (debug)'):
        st.warning('Visual provider unavailable. Original extraction retained.')
    proposal = st.text_area('Debug repair proposal Markdown', key='debug_proposal')
    accept_debug = st.checkbox('Accept this proposal as a manual debug override, including any text changes')
    if st.button('Accept proposal and rebuild (debug)', disabled=not accept_debug):
        overrides=dict(st.session_state.get('debug_overrides',{}))
        overrides[debug_page]=proposal
        st.session_state.debug_overrides=overrides
        st.session_state.run = run_pages(st.session_state.get('debug_base_pages',run['pages']), run['document_hash'], debug_overrides=overrides,region_input_characters=int(region_budget))
        st.rerun()
with tabs[3]: st.json(run['candidates'])
with tabs[4]: st.json(run['evidence'])
with tabs[5]:
    st.caption('Regions group explicit dependencies, not adjacency. Overlapping excerpts are merged; disconnected groups have separate inputs. Oversized connected groups remain unresolved with all candidates retained.')
    st.json({'regions':run['regions'], 'provider':run['structure_provider']})
with tabs[6]: st.json({'decisions':run['decisions'], 'section_index':run['section_index']})
with tabs[7]:
    st.warning('Provisional parser tree; unresolved boundaries remain in debug output.')
    pending=run['validation']['pending']
    st.write(f"Accepted sections: {len(run['section_index'])} · Unresolved candidates: {len(pending)}")
    if not run['section_index']:
        st.info('No sections were accepted. Text was extracted, but the resolver left heading/parent decisions unresolved. Inspect the candidates below; the unavailable model provider retains those uncertainties.')
    def show_outline(node):
        for child in node['children']:
            st.text('  '*(child['depth']-1)+f"{child['label']} {child['title']}".strip())
            show_outline(child)
    show_outline(run['tree']['root'])
    if pending:
        byid={c['id']:c for c in run['candidates']}
        choice=st.selectbox('Inspect unresolved heading / parent', [d['candidate_id'] for d in pending],
                            format_func=lambda ident:f"Page {byid[ident]['page']}: {byid[ident]['original_text'][:100]}")
        st.json({'candidate':byid[choice], 'decision':next(d for d in pending if d['candidate_id']==choice),
                 'evidence':next(e for e in run['evidence'] if e['candidate_id']==choice)})
        st.code(next(p['markdown'] for p in run['pages'] if p['page']==byid[choice]['page']),language='markdown')
    st.json(run['tree'])
    st.download_button('Download prediction JSON', json.dumps(run['tree'],ensure_ascii=False,indent=2), 'prediction.json')
with tabs[8]: st.json(run['body'])
with tabs[9]: st.json({'validation':run['validation'], 'limitations':run['limitations'], 'timings':run['timings']})
with tabs[10]:
    if reference and signature==st.session_state.signature and metadata.get('source_sha256')==run['document_hash'] and metadata.get('selected_pages')==[p['page'] for p in run['pages']]:
        evaluation = compare(run, reference, metadata, alignment)
        st.subheader(evaluation.get('comparison','Invalid reference'))
        st.json(evaluation)
        matches = evaluation.get('matches', [])
        if matches:
            selected_match = st.selectbox('Inspect reference heading disagreement', list(range(len(matches))),
                                          format_func=lambda i: matches[i]['reference']['title'])
            item = matches[selected_match]; st.json(item)
            candidate = next((c for c in run['candidates'] if c['id']==item['prediction_id']),None)
            st.json({'candidate':candidate,'decisions':[d for d in run['decisions'] if d['candidate_id']==item['prediction_id']]})
            st.caption('Consult Source and Markdown tabs for the original page; unmatched headings need manual alignment.')
    else: st.info('Load a matching reference and metadata. Evaluation is optional and never feeds inference.')
    st.download_button('Download debug report', json.dumps(run,ensure_ascii=False,indent=2), 'debug.json')
