# INC-004: Neutral Unknown-State Product-Fact Repair

## Locked experiment

INC-003's exact product fact reduced v13 false positives but changed both
unknown-status positives from 1 to 0. This is a tightly scoped repair test, not
a new retrieval or prompt-policy experiment. It uses only the seven
pre-registered `unknown` notices from INC-003 (two v13 positive and five v13
negative) and makes 14 paired requests.

Both arms retain the same product lookup, Joint-24 output, documents, metadata,
model, schema, and 4,000-character document budget. The control repeats the
INC-003 unknown wording. The treatment changes only that wording: it says
unknown exact matching must not affect v13 in either direction and that the
ordinary notice evidence must decide.

## Gate

The repair succeeds only if the neutral arm predicts both unknown positives as
violations and at most one of the five unknown negatives as violations. It is a
partial success if recall improves but that precision guardrail fails. It fails
if recall does not improve. A successful local repair still needs a later
full-cohort confirmation before it can be considered for a policy combination.

## Run integrity

The first execution was invalidated before analysis: two non-interactive client
calls continued after their client timeout and wrote duplicate checkpoint rows.
Its ignored artifacts remain only as a diagnostic record and must not be used.
The rerun has a new run ID and holds an exclusive non-blocking file lock for
its entire process, so a second invocation fails before any provider request.

The locked seed is also `20260826`, matching INC-003. An intermediate locked
rerun used a different seed and is retained only as a transport diagnostic, not
as a wording comparison; its run ID is distinct from the seed-matched result.

## Seed-matched result

The seed-matched run made 14 unique requests for a reported total of $0.00923.
Thirteen requests returned parseable structured output. One current-wording
control response was malformed JSON and used the pre-registered all-zero
fallback; it does not affect the neutral arm's direct gate result.

| Policy | v13 TP / FP / FN | Precision | Recall | F1 | Evidence validity |
|---|---:|---:|---:|---:|---:|
| Current unknown wording | 0 / 4 / 2 | 0.00000 | 0.00000 | 0.00000 | 0.25000 |
| Neutral unknown wording | 1 / 4 / 1 | 0.20000 | 0.50000 | 0.28571 | 0.60000 |

The neutral wording recovered one of two positives, but marked four of five
unknown negatives positive. It fails both the full-recall and false-positive
guards. The policy is rejected; it must not be combined with the matched and
not-matched product facts.

## Decision

**Reject unknown-state prompt steering.** The product fact is informative when
there is an exact match, but natural-language guidance for its unknown state is
not a stable precision/recall control. Do not spend another API loop on wording
variants.

The next independent branch should address a prerequisite exposed here:
structured-output recovery and evidence validation must be measured separately
from judgment quality. It should first use saved responses and a deterministic,
schema-aware JSON recovery routine (no model calls) to quantify how many
all-zero fallbacks and invalid-evidence positives can be repaired without
changing a label. Only after that offline check should a new judgment policy be
tested on a broader, fixed dev cohort.
