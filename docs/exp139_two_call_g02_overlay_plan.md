# EXP139 — original 24-item call plus G02 overlay

## Hypothesis

EXP135 showed a real gain for `v6`, `v7`, `v8`, `v9`, and `v19`, but reduced
the remaining 19 items because they were also asked in a narrowed response
scope. This experiment preserves the original full 24-item organizer-format
call, then asks exactly those five items in one second focused call. The
second response replaces those five keys only. This is fixed execution scope,
not a label rule, retrieval step, card, or Python interpretation.

## Controlled policy

Base: `configs/config.exp133-two-way-g02-fast-panel.yaml`.

- `G01_full_baseline`: ordered `v1`–`v24`, exact `official_baseline_v1`
  organizer prompt and V+E output contract.
- `G02_document_restrictions_override`: `v6`, `v7`, `v8`, `v9`, `v19`, same
  notice context and generation settings.
- The runner processes groups in this explicit order. The five named keys from
  G02 replace their first-call values; all other keys are retained unchanged.

Expected cost is 40 calls for fast-20 (two calls per notice), rather than the
baseline's 20. It is a quality diagnostic, not a submission candidate until
runtime and dev-200 are separately assessed.

## Mandatory pre-call review

Before remote calls, export and personally read both exact rendered messages
for each of:

1. `PPS-DEV-062` — short/complete notice;
2. `PPS-DEV-042` — 4,000-character overflow/truncation;
3. `PPS-DEV-01` — notice with attachments.

Acceptance criteria: both groups have the same actual user notice text and
 metadata; G01 names all 24 keys; G02 names only the five override keys; no
card, law/RAG, internal implementation vocabulary, or undeclared metadata is
injected. Record exported paths and review conclusion in the result document.

Then run preflight, exact-tokenizer admission over the frozen fast panel, and
mock execution. A paid run is allowed only if every check passes.

## Pre-call review record (2026-09-07)

Passed after one implementation correction. The first draft incorrectly used
the subset wording even for the full call; no provider call was made. The
final config declares `official_baseline_v1` for G01 and
`official_baseline_subset_v1` only for G02.

- Exact rendered inputs: `outputs/exp-139-two-call-g02-overlay-fast-panel/prompt_review_v2/`
  (`pps-dev-062`, `pps-dev-042`, `pps-dev-01`, each `.grouped.messages.md` and
  `.grouped.request.json`).
- Baseline parity exports: `outputs/exp-139-two-call-g02-overlay-fast-panel/baseline_parity/`.
  For all three notices, G01 system message, user message, and JSON schema are
  byte-identical to EXP125A. G01 has the ordered 24 keys; G02 has exactly
  `v6`, `v7`, `v8`, `v9`, `v19`.
- Human review: the two groups have identical user notice/metadata text;
  `PPS-DEV-062` is complete, while `PPS-DEV-042` and `PPS-DEV-01` visibly
  retain the organizer's 4,000-character truncation. No card, raw law/RAG,
  product index, internal group ID, or implementation-status text is present
  in either model message.
- Exact-tokenizer admission: `outputs/exp-139-two-call-g02-overlay-fast-panel/prompt_review_fast_panel_v2/admission.json`
  records 20 notices, 40 calls, and a maximum of 4,015 input tokens.
- Mock: `outputs/exp-139-two-call-g02-overlay-fast-panel/mock_after_prompt_fix/_mock/`;
  all 20 rows completed and submission validation passed.

## Decision rule

Compare with EXP125A and EXP133. Continue only if the 19 retained full-call
items avoid EXP133's G01 regression, G02 preserves its improvement, malformed
outputs remain acceptably low, and the resulting two-call runtime is viable.
