# INC-088/090 — high-reasoning gain and input-error diagnosis

## Verified result

Using the same full notice, metadata, decision-card v6, model, and dev-200 as
INC-084, only increasing Luna's explicit reasoning effort to `high` improved
macro positive-F1 from **0.328732** to **0.360726** (+0.031994).

The completed run is 200/200 successful. A first 4,096-output-token pass left
18 reasoning-heavy requests incomplete; those requests alone were resumed at
8,192 (and one at 16,384) tokens. This is transport/output recovery, not a
prediction merge. Final result artifacts contain the exact checkpoint history.

## Was missing input the dominant cause?

No. INC-090 analyzed all 179 high-reasoning errors without a new model call.
It records the original document set, `input_completeness`, dropped-document
counts, metadata, card, and deterministic representative dossiers.

- The major FN groups (`v6`, `v7`, `v10`--`v12`, `v14`, `v16`--`v18`) are
  overwhelmingly `무탈락`/`완전관측`; most have only one complete source
  document. Their failure is not caused by an omitted attachment.
- Absence items account for a substantial FN block. They require first proving
  applicability and then confirming a missing condition, a different operation
  from retrieving a positive phrase.
- `v24` contributes 40 of 179 errors, all FP. The source is usually complete;
  the model is comparing non-corresponding statements or treating a contextual
  region/description as a contradictory field. The card already says not to do
  this, so extra generic reasoning alone is insufficient.

## Representative source finding

In `PPS-DEV-061` (a v24 false positive), the announcement explicitly gives
80,000,000 won, negotiated contract, and a Gyeonggi participation restriction;
the metadata gives the corresponding budget, negotiated method, and restricted
industry/region fields. It is a complete one-document record, not a missing
input. This is a same-field alignment error.

## Decision

Stop scaling generic reasoning effort (the xhigh run was stopped after the
user correctly identified it as a cost-only branch). The next Luna branch must
keep full source context and make **operation types explicit**, without
inventing label-specific thresholds:

1. **Field-alignment operation for v24:** construct a fixed source-vs-metadata
   table only for corresponding budget/contract method/region/industry fields;
   unknown source values remain unknown, never mismatch.
2. **Applicability-then-absence operation:** for absence items, require an
   explicit applicability verdict before a whole-notice absence check.
3. **Predicate operation for positive restrictions:** distinguish a literal
   observed restriction from the legal conditions needed to make it a violation.

These are semantic operations derived from the item definitions, not
dev-selected thresholds or a post-hoc label merge. They will first be tested in
one full-context Luna call against the fixed dev-200 control.
