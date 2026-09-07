# EXP131 — independent confirmation of organizer four-group output scope

EXP131 is a direct confirmation of EXP130 on the pre-existing, label-blind
`dev_prompt_holdout_v1` cohort. Its effective inference policy must be
identical: same 4,000-character context, organizer-style metadata/user
renderer, V/E contract, four fixed groups, no cards, no retrieval, no product
facts, no merge rule, and identical decoding. Only the selected 20 IDs differ.

The control already exists as EXP128A: exact 24-item organizer baseline,
macro positive-F1 .125 on this cohort. Compare EXP131 against it, but assess
per-item TP/FP/FN and parse errors before interpreting macro movement.

Before provider calls, inspect grouped messages for:

- `PPS-DEV-062` — previously audited complete short-reference fixture under
  the same policy;
- `PPS-DEV-094` — shortest holdout announcement (4,257 chars; expected
  announcement-tail truncation);
- `PPS-DEV-046` — holdout attachment notice (announcement plus specification);
- `PPS-DEV-082` — long holdout proposal/specification attachment notice.

For the three holdout notices, verify each group's user text is byte-identical
within notice, system/schema keys are group-local, and visible omission markers
are factual. Run preflight, mock, and tokenizer admission for all 80 calls.
Do not alter the grouping or any card after seeing holdout inputs or results.

Reject EXP130's apparent gain if holdout macro falls at or below EXP128A, if
source-visible recall broadly collapses, or if malformed outputs/runtime make
the four-call design unsafe. Even a pass remains diagnostic until dev-200 and
runtime projection.
