# Current no-API review packet

The original skeleton delivery overstated real-PDF usefulness. Its numeric-only
resolver and broad parent blocking have now been improved in the authorized
follow-up. The package follows the planned stage files, with real implementations
in each module and sequential orchestration in pipeline.py. No live model call or
reviewed benchmark was needed for this work.

The next generalized region-input checkpoint is also implemented: unrelated adjacent
ambiguities stay separate, overlapping source excerpts merge, and only relevant
anchors plus their ancestor chains enter the payload. Following anchors are
context-only. The configurable budget counts compact JSON characters including
document/revision envelope, not estimated tokens. Oversized connected components
are retained in full and skipped before any provider invocation; safe internal
splitting remains deferred. No corpus keywords or PDF-specific profiles were added.

## What to try now

The Body tab now provides a per-node inspector and body-provenance.json export.
Each span records its hierarchy scope and heading-driven closures, exact source
ranges and unresolved boundaries. Cross-page joins add a newline only to prevent
word gluing; generated whitespace is separate from source characters. Multi-page
heading fragments are excluded from own body. An unselected-page gap makes an
unheaded continuation provisional. Unheaded return to a parent is still not
guessed; the active-section assumption is explicit. These rules use source and
hierarchy, not document-specific prose. The synthetic reference was adjusted for
the documented page separator, independently of provider replay decisions.

Open http://localhost:8501, choose the M-24-08 packet or upload its PDF, select the
first six pages and click **Run / Re-run**. Cached older runs are not automatically
re-extracted. The Tree tab now renders:

```text
I. INTRODUCTION
II. SCOPE AND APPLICABILITY
III. BUILDING AND SUSTAINING ACCESSIBLE FEDERAL TECHNOLOGY
  A. Establish Digital Accessibility Programs and Policies
  B. Buy Accessible Products and Services
  C. Design and Develop Accessible Digital Experiences
```

This is a provisional automatic structure, not verified accuracy. Seven other
candidates remain unresolved, mostly in the opening material; the Tree tab shows
their text, decisions, evidence and source Markdown. Original page rendering is
available in Source. Unavailable visual recovery remains visible in Quality.

## Current sample status

Only original pages **1–6 of each test_docs PDF** were selected for packets/smoke.
No GPT credentials/integration were available. No GPT call was made and no real
silver.json was fabricated. All four packets remain `pending_external_generation`:
PDF SHA-256, selected pages, model null, explicit no-call generation method,
original PNGs, extracted text, an external-generation prompt and separate notes.
External draft import validates schema, IDs, depths, source hash and text-token
consistency, then records `ai_unreviewed` with importer-supplied actual model
provenance. Original silver is protected against overwrite. No human-reviewed
sample or real accuracy estimate exists.

| Six-page slice | Candidates | Accepted sections | Unresolved candidates | Regions |
|---|---:|---:|---:|---:|
| DKT Employee Handbook | 17 | 2 | 13 | 6 |
| Employee Handbook | 28 | 12 | 4 | 2 |
| Nonprofits and Small Businesses | 25 | 6 | 7 | 2 |
| M-24-08 Accessibility memorandum | 26 | 6 | 7 | 1 |

These are inspection counts, not accuracy. Every smoke run has zero canonical
source-accounting errors. This does not prove PDF extraction completeness.

## Stage behavior and remaining limits

| Planned module | Current behavior | Remaining limit |
|---|---|---|
| models.py | Shared TypedDict values and unchanged annotator tree contract. | Runtime checks remain in validation. |
| pipeline.py | Sequential stage calls, one run result, stage timings. No reference loading. | No production infrastructure. |
| extraction.py | Real p4l 1.28.2, per-page Markdown/observations, original PNGs, canonical revision. Page failures remain inspectable. | OCR disabled; automatic document-title inference deferred. |
| routing.py | Coverage/order/table/text-layer checks, replacement-character risk, automatic selective recovery requests. | Risk evidence requires calibration; ACCEPT means no detected issue. |
| reconciliation.py | Token occurrence omissions/additions/repetition/order, including negation. Synthetic order-only adoption; explicit manual debug acceptance. | Generic comparison cannot certify real repairs. |
| candidates.py | Deterministic IDs/spans; heading/numbered/bold/uppercase/isolated blocks, tight Markdown segmentation, wrapped bold headings. | General inline/multiline grammar remains limited. |
| labels.py | Numeric paths and bounded Roman/alphabetic alternatives. | Isolated `(i)` is deliberately ambiguous; mixed label grammars incomplete. |
| evidence.py | Contextual consecutive-label corroboration and repeated-heading/prose observations. Pure observations are not mutated by decisions. | Heuristic assumptions need reviewed evidence. |
| resolver.py | Separate role/parent uncertainty; contextual family nesting, local ancestor blocking, numeric scope conflicts; atomic provider validation. | Truncated/unanchored sequences remain unresolved; live model unavailable. |
| regions.py | Explicit dependency groups, merged cross-page excerpts, relevant section/ancestor anchors, compact outline and exact request-character budgets. | Discovery incomplete; indivisible oversized components remain unresolved without truncation. |
| providers.py | Unavailable transport and input-fingerprinted synthetic replay. | No live requests, fabricated responses or real-PDF dummy answers. |
| hierarchy.py | Accepted relationships only; cycles/unknown/duplicate/later parents quarantined. | No global structure LLM. |
| body.py | Exact source fragments, scope paths/heading closures, multi-page headings, gap uncertainty, recorded page separators and per-node own-text provenance. | Unheaded enclosing resumption requires authoritative closure evidence and is never guessed. |
| validation.py | Schema/IDs/depths, span bounds/revision/text, owner consistency, gap/overlap accounting, outstanding ambiguity and extraction failures. | Internal conservation does not establish content accuracy. |
| evaluation.py | Confirmed repeated-title alignment; extraction/candidate/resolver miss attribution; explicit generator denominator; guarded exact/whitespace own-text checks. | Unconfirmed alignment/presence/ownership produces N/A/unclassified results. |

Unresolved recovery prevents a fully complete result even when the tree is
structurally complete. Running matter is retained in body; nothing is silently
discarded as noise. Root title remains blank when unsupported, with its original
source material retained in the preamble.

## Dummy/skip model paths

Real PDFs always use the unavailable provider until a live integration is added.
Synthetic demo options exercise unavailable, valid replay, rejected replay and
abstention. Provider outputs only choose existing IDs/roles/parents. Missing or
abstaining outputs stay unresolved; invalid batches are rejected atomically.
Resolver fixtures are separate from evaluation references. AI-draft comparisons
say **against AI draft reference**, never verified parser accuracy.

## Verification

The current suite passes **75 tests**, including stage boundaries, deterministic
candidates, Roman/alpha sequences across pages, isolated ambiguous labels,
truncated supported roles with unknown parents, conflicting numbering, unknown
ancestors, closed scopes, wrapped/tight headings, code fences, replay ID/cycle/
fingerprint/abstention checks, failed extraction, empty scan, source revision/text/
own-text checks, body nonduplication and localized uncertainty, repeated-title
alignment, confirmed miss attribution and explicit denominators.

Streamlit AppTest covers all eleven tabs, unavailable/valid/invalid/abstaining
demo paths, a real handbook and the real six-page M-24-08 outline. The HTTP health
endpoint returns 200/ok. Four real-PDF source-accounting smoke runs pass. Module
compilation and whitespace checks pass. Native-browser visual layout and manual
file-upload/download clicks have not been visually exercised.

New synthetic region checks vary numeric, Roman, alphabetic and unnumbered labels,
rename arbitrary title words, distinguish adjacency from shared-parent dependencies,
exercise cross-page grouping/ancestor context, verify exact payload-budget boundaries,
and confirm oversized inputs never call a provider or lose a candidate. Streamlit
AppTest also exercises the budget control and skipped-provider state. Corpus smoke
counts and structures are unchanged by this region-only checkpoint.

Body checkpoint tests additionally vary title wording and scope depth, assert
sibling/ancestor closure events, preserve cross-page fragments without word gluing,
handle selected-page gaps and multi-page heading ranges, retain Markdown tables,
reject invented separators, and exercise the Body provenance inspector. All four
real-PDF canonical-accounting smoke runs still have zero errors; heading counts
are unchanged. Tree JSON keeps the original annotator schema; provenance is separate.

The existing annotator previously passed TypeScript and Vite production build and
start checks; no annotator source changed in this follow-up. Imports remain strict;
manual PDF-review declaration is required before downloading reviewed golden.json.
The machine's bundled Node is usable even though system PATH lacks Node. pnpm
dependency installation reported ignored build scripts; direct build checks passed
after permitting Vite helper processes in this sandbox.

## Verified commands

From `F:\Projects\parser`:

```powershell
./.venv/Scripts/python -m pytest codex_version/tests -q
./.venv/Scripts/python codex_version/smoke.py
./.venv/Scripts/python -m streamlit run codex_version/app.py --server.headless true --server.port 8501
./.venv/Scripts/python codex_version/bootstrap.py prepare
```

Dependency setup: requirements.lock.txt and README.md. External silver import:

```powershell
./.venv/Scripts/python codex_version/bootstrap.py import codex_version/benchmarks/Employee-Handbook path/to/draft.json --model actual-model --notes path/to/notes.md
```

Annotator commands, with bundled Node:

```powershell
$taskNode = 'C:/Users/jiaqi/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
& $taskNode codex_version/document-outline-annotator/node_modules/typescript/bin/tsc --noEmit -p codex_version/document-outline-annotator/tsconfig.json
Set-Location codex_version/document-outline-annotator
& $taskNode node_modules/vite/bin/vite.js build
& $taskNode node_modules/vite/bin/vite.js --port 3000 --host 127.0.0.1
```

Review silver against the original PDF later; save golden.json and separate
golden.metadata.json with reviewer/date/status `reviewed`, preserving silver.
Confirm source alignment, extraction presence and own-text ownership before
interpreting metrics. Private PDFs/extracted pages/reference answers stay ignored
by git. Debug runs are under ignored runs/; counts are in smoke-results.json.

Next evidence-dependent work: reviewed measurement/calibration, followed by any
required grammar/dependency/scope improvements. Live model integration remains
explicitly deferred until credentials exist.
### Automatic/manual run debugging checkpoint

The Reviewer preserves the automatic run before explicit Markdown debug overrides,
rebuilds through the same sequential pipeline, and permits switching between both
full runs. Evaluation exports page, structure, own-text, unresolved-item and validation
differences without correctness scores. Cross-revision alignment uses unique exact
page/label/title suggestions; repeated and renamed headings require later alignment.
No reference answers feed inference, and no API calls or human review are implied.
Candidate role/parent editing and live providers remain future work.
