# Reference workflow

Each real sample selects only original pages 1–6 (or all pages of a shorter PDF).
The unchanged public tree schema is `{root: {id,label,title,text,depth,children}}`.
Metadata and uncertainty notes are separate. No reviewed samples are required to run.

`bootstrap.py prepare` creates original PNGs, p4l Markdown, source observations and
an external-generation prompt. Without GPT credentials it creates no silver.json.
`bootstrap.py import <folder> <draft.json> --model <actual-model> --notes <notes.md>`
checks schema, IDs, depths, source hash, page scope and token accounting, then saves
silver.json with annotation_status `ai_unreviewed`. Checks are not human review.
Token differences are warnings: extraction mistakes, excluded running matter and
formatting need review against the images. Never claim draft comparisons are accuracy.

Load silver.json into the existing annotator. Correct it against the PDF. Explicitly
check the manual-review declaration and download golden.json. Preserve silver.json.
For reviewed benchmark use, save separate golden metadata with status `reviewed`,
original hash/pages, reviewer and review date. Do not relabel the silver metadata.
Alignment maps reference IDs to `{pages:[1], heading_text:"original heading", confirmed:true}`.
Confirmation must come from a human; Markdown revision offsets must be versioned.
For reliable misses, additionally record `markdown_presence_confirmed: true` and
`markdown_presence: "present"` or `"absent"` after checking extraction. Generator
recall uses only confirmed-present headings; unconfirmed presence keeps it N/A.
Precise Markdown locations require `canonical_revision` and `start`. Stale revision
links are not confirmed. Own-text metrics additionally require `own_text_confirmed:
true` and parser ownership without unresolved boundaries. These confirmations must
not be inferred from candidate counts or AI draft self-assessment.

Source PDFs stay in test_docs; private PDFs and page images are ignored by git.
Resolver replay fixtures come from synthetic inputs and are never silver references.
