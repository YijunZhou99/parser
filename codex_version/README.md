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

Body now records heading-driven scope paths/closures and a separate per-node
provenance index. The Body tab inspects own text, original ranges and uncertainty,
and downloads body-provenance.json. Cross-page fragments remain exact; a joining
newline is inserted only when needed to avoid gluing words, and is recorded as
generated whitespace outside source accounting. Missing selected pages make
unheaded continuation ownership provisional. Unheaded ancestor resumption is
never inferred from prose or document-specific words.

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
### Whole-run debugging comparison

Run / Re-run preserves an automatic baseline and resets previous manual debug runs.
Accept an explicit Markdown proposal in Extraction/Router to rebuild all downstream
stages. Evaluation then shows the automatic/manual comparison, with downloads for
the comparison and complete automatic baseline, and buttons to inspect either run.
Comparisons include page changes, section hierarchy and own-text differences,
unresolved items and validation. Across revisions, unique page/label/title matches
are provisional suggestions; repeated or renamed headings remain unmatched.
Manual overrides are not reviewed golden annotations and these differences are
not accuracy scores. Rebuilds use unavailable providers; baseline replay responses
are never reused against a changed canonical revision.
Repeated unformatted first/last source blocks on at least three selected pages
are recorded as page-margin evidence and do not block section parenting. Explicit,
bold or numbered headings are excluded from this rule; source text is retained.
Trailing HTML superscript footnotes are separated for heading-label parsing while
original heading spans preserve their complete markup. Re-run the nonprofit
handbook's first six pages to see A, B and C as siblings under II.
Single `A.` subsections can use a confirmed Roman-section context plus an explicit
heading followed by prose; an active matching parent is still required. Numeric
headings `1` through `9` (and larger values), `1.`, `1)` and `(1)` retain their
labels. Supported plain numeric sequences can nest under an active alphabetic
section when they restart at 1, even when extraction flattens Markdown levels.
Bare page numbers remain body; dotted numeric paths retain parent/conflict checks.
Numeric paths resolve from active prefix parents: `I → A → 1 → 1.1 → 1.1.1`.
Both flattened and full-depth Markdown are supported when an active numbering
relationship explains the levels. A new alphabetic scope permits a restart at 1;
duplicate/backward numbering within the same parent remains unresolved. Closed
numeric parents cannot be reused. Ordinary unformatted numbered lists do not
corroborate section headings, and their original text remains in body output.
