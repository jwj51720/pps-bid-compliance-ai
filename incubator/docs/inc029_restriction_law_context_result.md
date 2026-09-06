# INC-029: Restriction-Law Context Isolation Result

## Validity and spend

The fixed 36-notice cohort executed 72/72 calls successfully. No provider
admission or structured-output failure occurred. Complete source units were
used unchanged; the observed maximum admission probe was 11,749 prompt tokens
for the local-law arm. Total reported cost was $0.09285640. Five raw responses
contained an invalid notice-evidence quote and were deterministically
downgraded before scoring; the treatment had one such downgrade. All retained
positive treatment evidence validates against its original notice (100%).

## Paired result

| Arm | Target Macro F1 | TP / FP / FN | Micro recall | Positive evidence |
|---|---:|---:|---:|---:|
| Whole notice, no law | 0.30880 | 9 / 15 / 16 | 0.36000 | 24/24 |
| Same notice + complete applicable law | 0.38515 | 9 / 8 / 16 | 0.36000 | 17/17 |
| Law minus control | +0.07635 | 0 / -7 / 0 | 0.00000 pp | 0.00 pp |

Per-item F1 changes were v4 `0.54545 → 0.58824`, v6 `0.18182 → 0.22222`,
v7 `0.22222 → 0.44444`, and v8 unchanged at `0.28571`.

There were 17 changed cells: 11 corrections and 6 newly wrong cells. The
important pattern is not a post-hoc union: the law arm removes seven net false
positives while preserving the aggregate TP/FN count. Among the 15
stratum-matched negative notices, it removes false positives in four notices
and introduces none at notice level. It does lose two positives and recover two
others, so it has not yet demonstrated a recall improvement.

## Decision

**Success; promote to the pre-registered dev-200 confirmation only.** It meets
all pilot gates: +0.05 target Macro F1, non-decreasing recall, at most two new
matched-negative FPs (zero), and 100% retained evidence validity. It does not
authorize a final policy, a global score claim, a changed law boundary, or
combining it with RAG/family-output changes.

The confirmation uses the same complete source units selected only by
`metadata.적용계약법`, same four-item output, complete notice, source-evidence
gate, model/settings and parsed response contract on all 200 dev notices.
