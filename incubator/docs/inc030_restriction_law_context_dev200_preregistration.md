# INC-030: Restriction-Law Context Dev-200 Confirmation

## Authority

INC-029 passed its frozen paired-pilot gates (+0.07635 target Macro F1, no
recall decrease, -7 FP, 100% retained evidence). This confirmation is the
pre-registered next step, not a fresh search.

## Frozen policy

For every one of the 200 dev notices, call Gemma once for control and once for
treatment. Both calls contain all notice documents, metadata, the same four
items (v4/v6/v7/v8), generation settings, output schema, source-only evidence
validator and retry policy as INC-029.

Treatment alone adds the exact same complete organizer-law units from INC-029,
selected solely by metadata `적용계약법`. No law boundary, prompt wording,
output group, RAG rank, example, deterministic label, or document admission
policy may change. A provider rejection is recorded; no source is shortened.

## Cost and success contract

Maximum 400 calls, $0.70 reported cost. A transport/parse/admission failure
rate over 5% invalidates the confirmation. Report target per-item and macro
F1, TP/FP/FN, evidence validity, raw costs/tokens, changed cells, and 10,000
deterministic notice-bootstrap paired Macro-F1 deltas (seed 20260905).

Promotion requires all of:

1. treatment target Macro F1 is at least control +0.025;
2. treatment target micro recall does not decrease;
3. treatment target FP does not increase;
4. 90% bootstrap lower bound of treatment-minus-control Macro F1 is at least
   zero; and
5. 100% retained treatment positive evidence validity.

If promoted, this remains a four-label component, not a claim that the entire
24-label submission reaches the target. Its isolated overall impact is measured
by replacing only v4/v6/v7/v8 in the preserved INC-018 `single_full` output;
the other 20 labels are unchanged. Any failure rejects the component and no
post-hoc merge is allowed.
