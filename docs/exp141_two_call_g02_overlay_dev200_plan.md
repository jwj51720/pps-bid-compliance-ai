# EXP141 — dev-200 confirmation of original-call plus G02 overlay

EXP141 is policy-identical to EXP139/140; it only evaluates all dev records.
The policy passed its frozen fast panel and independent holdout, so this is the
first full-dev assessment. It remains diagnostic rather than a submission
candidate because its two calls per notice have not been measured under offline
vLLM runtime.

Mandatory pre-call work: re-export and read the final config's actual messages
for `PPS-DEV-062` (complete), `PPS-DEV-042` (overflow), and `PPS-DEV-01`
(attachments); run preflight, dev-200 tokenizer admission, and clean mock.
Expected remote call count: 400. Compare macro F1, every item F1, parse errors,
evidence validity, and summed provider latency with EXP109 and EXP135.

## Pre-call review record (2026-09-07)

Passed. Exact rendered messages for the three required notice shapes are in
`outputs/exp-141-two-call-g02-overlay-dev200/prompt_review/`. G01 has 24
output keys under `official_baseline_v1`; G02 has exactly `v6`, `v7`, `v8`,
`v9`, `v19` under the subset profile. In every reviewed pair the user message
is identical; `062` is complete and `042`/`01` show the organizer truncation.
The model sees no cards, law/RAG, product index, or implementation vocabulary.

`outputs/exp-141-two-call-g02-overlay-dev200/prompt_review_dev200/admission.json`
records exact tokenizer admission for all 200 notices: 400 calls and a maximum
of 4,206 input tokens. The clean mock artifact is
`outputs/exp-141-two-call-g02-overlay-dev200/mock/_mock/`.
