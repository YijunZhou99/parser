# Track A parser and Reviewer

Parser stage files now follow the planned layout under `policy_parser/`:

```text
models.py          # shared typed values and annotator tree contract
pipeline.py        # sequential orchestration only
extraction.py      # p4l, source observations, rendering, canonical revision
routing.py         # assessment and selective recovery orchestration
reconciliation.py  # proposal text/order comparison and adoption
candidates.py      # deterministic block candidates and source spans
labels.py          # label grammar observations
evidence.py        # observed structural support/conflict
resolver.py        # deterministic decisions and atomic provider application
regions.py         # dependency components and provider context
providers.py       # unavailable/replay transport and fingerprints
hierarchy.py       # accepted parent relationships into global tree
body.py            # source-based own-text attachment
validation.py      # tree/schema/source accounting and text consistency
evaluation.py      # reference matching, diffs and measurement
```

These contain the actual stage implementations, not wrappers around pipeline.py.
`reference.py` has been removed; evaluation and validation have separate owners.
The no-API resolver now supports contextual Roman/alphabetic sequences and repeated
Markdown headings followed by prose. M-24-08 pages 1–6 produce I/II/III, with A/B/C
under III. Isolated ambiguous labels and unsupported parents remain unresolved.
Live providers are still unavailable; the synthetic demo supports valid, rejected
and abstaining replay. Click Run / Re-run to replace any cached older root-only result.

Regions use explicit dependency groups, merged source excerpts and local anchor
chains. The sidebar region budget measures compact JSON characters (not model
tokens), including the request envelope. Oversized connected components are kept
intact and skipped before provider invocation; no candidates are silently truncated.

Run from `F:\Projects\parser` in PowerShell:

```powershell
python -m venv .venv
./.venv/Scripts/python -m pip install -r codex_version/requirements.lock.txt --index-url https://pypi.org/simple
./.venv/Scripts/python -m streamlit run codex_version/app.py --server.headless true --server.port 8501
./.venv/Scripts/python -m pytest codex_version/tests -q
./.venv/Scripts/python codex_version/bootstrap.py prepare
./.venv/Scripts/python codex_version/smoke.py
```

Open http://localhost:8501. Select a local review packet or upload a PDF, then click
Run / Re-run. Extraction runs only on explicit rerun or initial session setup.
All eleven tabs inspect the same run result. Source shows original page PNGs.
Tree exports unchanged annotator JSON; Evaluation exports the debug report.
Debug repair acceptance is a manual override, rebuilds all downstream decisions,
and cannot be interpreted as automatic repair success or human annotation review.

No GPT key was available. Four six-page external-generation packets are under
`benchmarks`. These contain images, extracted text, metadata and a prompt, but no
silver answers. Generate drafts externally, then import:

```powershell
./.venv/Scripts/python codex_version/bootstrap.py import codex_version/benchmarks/Employee-Handbook path/to/draft.json --model actual-model-name --notes path/to/notes.md
```

Load silver.json plus metadata.json in Reviewer. Comparisons are explicitly
“against AI draft reference”, never verified parser accuracy. Token accounting
checks are not human review. The parser never reads references. Synthetic resolver
replay decisions are separate from evaluation references.

Annotator remains in `document-outline-annotator`; its scripts are `dev`, `lint`
and `build`. With standard Node/pnpm on PATH:

```powershell
Set-Location codex_version/document-outline-annotator
pnpm install
pnpm lint
pnpm build
pnpm dev
```

For this machine the bundled runtime is usable without changing system PATH:

```powershell
$taskNode = 'C:/Users/jiaqi/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
& $taskNode codex_version/document-outline-annotator/node_modules/typescript/bin/tsc --noEmit -p codex_version/document-outline-annotator/tsconfig.json
# Run Vite from the annotator directory:
Set-Location codex_version/document-outline-annotator
& $taskNode node_modules/vite/bin/vite.js --port 3000 --host 127.0.0.1
```

The annotator strictly checks imported schema/IDs/depths. Correct silver against
the original PDF, then explicitly check the manual-review declaration and download
golden.json. Preserve original silver and record reviewed provenance separately.

See `REVIEW_PACKET.md` for verified commands, stage limitations and test evidence.
