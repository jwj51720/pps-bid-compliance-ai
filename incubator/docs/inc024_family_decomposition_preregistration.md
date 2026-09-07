# INC-024: Task-Decomposition Mechanism Pilot (Pre-registered)

## Why this experiment exists

INC-018 (one 24-item call) had low recall and INC-021 (four family calls)
had higher precision/evidence validity but a severe recall loss. INC-021
changed several variables at once: family decomposition, retrieved law text,
and a dev-length-derived legal excerpt. Its score therefore cannot establish
whether decomposition itself helped or hurt.

INC-024 isolates only the output-task decomposition mechanism. It is not a
law-RAG experiment and it must not use a character-derived legal context limit.

## Frozen comparison

Each selected notice receives the same ordered, complete source-document input
and the same metadata, model, decoding settings, JSON parser, evidence
validator, and conservative output merge policy.

| Arm | Calls/notice | Output |
|---|---:|---|
| Joint control | 1 | `v1`--`v24` in one call |
| Family treatment | 4 | `v1`--`v9`, `v10`--`v18`, `v19,v21,v22,v23`, `v20,v24` in separate calls |

No legal excerpt, decision card, product fact, candidate-window selector,
threshold, prediction-derived routing, or post-hoc per-item correction is
allowed in either arm. Families are the already documented legal/task-shape
partition from INC-021, fixed before looking at INC-024 outputs. Both arms see
the whole notice so that a family call cannot lose a document merely because
it belongs to another category.

Non-absence labels use OR merge only across their sole family output; absence
labels retain the single full-notice coverage semantics. Every positive
non-absence evidence span is validated against the complete original document.

## Cohort and spend contract

The cohort is 12 notices selected by a deterministic label-stratified rule,
not by historical model errors or document length:

1. Split the 24 labels into the four frozen families above.
2. For each family choose the lowest stable ID whose gold row has a positive in
   that family, then repeat without replacement until each family contributes
   two notices or its positives are exhausted.
3. Fill remaining slots with the lowest stable IDs from the all-negative rows.
4. Save the ordered IDs, selection algorithm version, source hashes, and ID
   hash before the first request.

This is a *mechanism pilot*, not a selection-score claim. It uses exactly
`12 × (1 + 4) = 60` maximum Gemma calls, with an OpenRouter ceiling of $0.50.
It stops immediately on a malformed-response rate above 5%, a cost ceiling,
or any request whose full complete-document prompt is rejected by the provider.
No retry changes a prompt or input length.

## Measurements and decision rules

Primary outcome is the paired cell-level change on the 12-notice cohort:
corrected FP/FN versus introduced FP/FN, overall and by family. Secondary
outcomes are positive-class Macro F1, precision, recall, evidence validity,
input/output tokens, request failures, and per-notice disagreement patterns.

The treatment earns **success** only if all conditions hold:

1. at least four net corrected cells;
2. no family loses more than two recall cells;
3. non-absence evidence validity remains 100%; and
4. no all-negative notice gains more than one positive label.

It is **partial success** if evidence/transport gates hold and the error ledger
shows one coherent family-specific advantage but the primary gate does not.
Then, and only then, the next experiment is a 24-notice confirmation with the
same frozen policy. It is a **failure** if recall broadly drops, all-negative
FP rises, or the effect has no coherent family pattern. In that case family
decomposition is frozen as rejected and no prompt repair is allowed; the next
branch is typed metadata reconciliation or product exact-lookup, not another
decomposition prompt.

## Generalization safeguards

- No result may choose an excerpt length, a document prefix, a token reserve,
  a label threshold, or a family-specific phrase list.
- The selected IDs are diagnostic only; any promotion requires a separately
  predeclared full-dev confirmation.
- The production-compatible continuation uses only the submission-defined
  context reserve and complete-document overflow policy. Exact token admission
  must be rerun using the packaged submission tokenizer before that stage.
- This experiment does not change the canonical pipeline or submission.
