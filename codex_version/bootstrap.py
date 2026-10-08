"""Current: prepare first-six-page external silver packets; strictly validate imports.
Limitations: no GPT credentials/integration; preparation does not create silver.
TODO(B1): reviewed golden with source alignment, preserving original silver.
Acceptance: packet hashes/pages and external-import validation tests.
"""
import argparse
import json
from pathlib import Path
from policy_parser.extraction import extract, render, sha
from policy_parser.validation import validate_tree, text_consistency

BASE = Path(__file__).parent
PROMPT = '''Create an AI draft outline for ONLY original pages 1–6 (or fewer if the PDF is shorter).
Inspect original page images alongside extracted text; extraction is not ground truth.
Return exactly {"root": {"id":"root","label":"","title":"...","text":"...","depth":0,"children":[]}}.
Each child has exactly id,label,title,text,depth,children. IDs unique; depths derived from parentage.
Preserve original labels, hierarchy, source order and own text. Do not summarize, invent missing content,
or duplicate descendant text into parents. Keep tables faithful. Exclude running headers/footers and TOC
from heading targets, but record exclusions and uncertainty in a separate notes file.
Root represents this six-page slice, not content beyond it. Unheaded continuation belongs to its section.
Return uncertainties separately. This is ai_unreviewed, never reviewed golden.
'''


def prepare(source_dir):
    for source in sorted(source_dir.glob('*.pdf')):
        import pymupdf
        pdf = source.read_bytes()
        with pymupdf.open(stream=pdf,filetype='pdf') as doc: selected = list(range(1,min(6,len(doc))+1))
        folder = BASE/'benchmarks'/source.stem
        folder.mkdir(parents=True,exist_ok=True)
        if (folder/'silver.json').exists() or (folder/'golden.json').exists():
            print(f'Preserving existing annotations: {source.name}'); continue
        pages = extract(pdf, selected)
        (folder/'pages').mkdir(exist_ok=True)
        for p in pages:
            (folder/'pages'/f'{p["page"]}.png').write_bytes(render(pdf,p['page']))
            (folder/'pages'/f'{p["page"]}.md').write_text(p['markdown'],encoding='utf-8')
        (folder/'source-text.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf-8')
        metadata = {'sample_id':source.stem,'source_path':source.relative_to(BASE.parent).as_posix(),
                    'source_sha256':sha(pdf),'selected_pages':selected,'annotation_status':'pending_external_generation',
                    'model':None,'generation_method':'external_image_and_text_packet; no GPT call executed',
                    'root_convention':'Artificial root for original pages 1–6 only'}
        (folder/'metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
        (folder/'prompt.txt').write_text(PROMPT,encoding='utf-8')
        (folder/'notes.md').write_text('No draft generated: no GPT credentials or usable live integration.\nRecord annotation uncertainties here when importing silver.\n',encoding='utf-8')
        print(f'Prepared {source.name}: {selected}; no silver generated')


def import_silver(folder, draft, model, notes):
    data = json.loads(draft.read_text(encoding='utf-8'))
    errors = validate_tree(data)
    if errors: raise ValueError(errors)
    metadata = json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
    source = BASE.parent/metadata['source_path']
    if sha(source.read_bytes()) != metadata['source_sha256']: raise ValueError('Source hash changed')
    if metadata['selected_pages'] != list(range(1,len(metadata['selected_pages'])+1)) or len(metadata['selected_pages'])>6:
        raise ValueError('Only first-six-page packets supported')
    if (folder/'silver.json').exists(): raise ValueError('Original silver exists; refusing overwrite')
    if not model or not notes.exists(): raise ValueError('Model provenance and separate notes required')
    pages = json.loads((folder/'source-text.json').read_text(encoding='utf-8'))
    checks = text_consistency(data,'\n'.join(p['plain_text'] for p in pages))
    metadata.update(annotation_status='ai_unreviewed',model=model,generation_method='external AI draft using page-image/text packet')
    (folder/'silver.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    (folder/'metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    (folder/'notes.md').write_text(notes.read_text(encoding='utf-8'),encoding='utf-8')
    (folder/'silver-checks.json').write_text(json.dumps({'schema_errors':errors,'text_consistency':checks,'human_review':False},ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command',required=True)
    p = sub.add_parser('prepare'); p.add_argument('--source-dir',type=Path,default=BASE.parent/'test_docs')
    p = sub.add_parser('import'); p.add_argument('folder',type=Path); p.add_argument('draft',type=Path)
    p.add_argument('--model',required=True); p.add_argument('--notes',type=Path,required=True)
    args = parser.parse_args()
    if args.command=='prepare': prepare(args.source_dir.resolve())
    else: import_silver(args.folder,args.draft,args.model,args.notes)
