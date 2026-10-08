"""Current: reproducible no-API corpus smoke and synthetic replay reports.
Limitations: no accuracy claims; references are not read during inference.
TODO(B1): reviewed benchmark evaluation after manual correction.
Acceptance: valid exported trees, text accounting and explicit unavailable providers.
"""
import json
from pathlib import Path
from policy_parser.pipeline import run_pages
from policy_parser.demo import demo_run

base=Path(__file__).parent
(base/'runs').mkdir(exist_ok=True)
reports=[]
for folder in sorted((base/'benchmarks').iterdir()):
    if not folder.is_dir(): continue
    pages=json.loads((folder/'source-text.json').read_text(encoding='utf-8'))
    metadata=json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
    run=run_pages(pages,metadata['source_sha256'])
    assert not run['validation']['schema_errors'] and not run['validation']['source_errors']
    (base/'runs'/f'{folder.name}.json').write_text(json.dumps(run,ensure_ascii=False,indent=2),encoding='utf-8')
    reports.append({'sample':folder.name,'pages':[p['page'] for p in pages],
                    'candidates':len(run['candidates']), 'accepted_sections':len(run['section_index']),
                    'ambiguous_candidates':len(run['validation']['pending']),
                    'regions':len(run['regions']), 'assessments':[a['status'] for a in run['assessments']],
                    'source_accounting_errors':run['validation']['source_errors'],
                    'annotation_status':metadata['annotation_status'],'verified_accuracy':None})
for mode in ('unavailable','valid_replay','invalid_replay'):
    (base/'runs'/f'synthetic-{mode}.json').write_text(json.dumps(demo_run(mode),indent=2),encoding='utf-8')
(base/'smoke-results.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
print(json.dumps(reports,indent=2))
