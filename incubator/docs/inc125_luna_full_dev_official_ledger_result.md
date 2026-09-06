# INC-125: Luna official-ledger full-dev confirmation

## Result

The policy fixed before the full-dev call establishes a new best Luna result:

| Policy | Dev-200 macro positive-F1 | Delta |
|---|---:|---:|
| INC-088 direct card-v6, full source, high reasoning | 0.360726 | — |
| INC-125 official ledger for v1--v23 + direct card-v6 for v24 | **0.427366** | **+0.066640** |

The 104 newly requested, label-blind remainder records yielded 101 strict
schema successes.  Together with the matching three INC-118 cohorts, 196 of
200 records use the official-ledger result.  Four notices use the whole-vector
direct-card transport fallback: `PPS-DEV-034`, `PPS-DEV-079`, and
`PPS-DEV-147` produced no parseable JSON after the fixed request recovery; and
`PPS-DEV-125` was blocked by the provider safety filter in the preceding
cohort.  No record was rephrased or selectively repaired.

## What improved and what did not

The largest broad gains were the conditional legal items that motivated the
ledger: `v6` `0.000 -> 0.667`, `v7` `0.000 -> 0.769`, `v15`
`0.286 -> 0.727`, and `v18` `0.000 -> 0.444`.  `v5`, `v9`, `v16`, and `v20`
also improve.  `v24` is exactly unchanged because the direct-card output was
predeclared for that semantic field-alignment task.

The ledger is not uniformly better: `v1`, `v2`, `v3`, `v4`, `v8`, `v13`,
`v19`, `v21`, and `v23` regress.  There are 99 changed cells, with 40 becoming
correct and 59 becoming wrong; macro positive-F1 nevertheless rises because
the gains recover several formerly zero-F1 rare labels.  This is why the
per-item table—not only changed-cell count—is retained in the run artifact.

## Integrity and interpretation

This is a full-dev teacher-quality result, not a public-leaderboard estimate
or a final submission policy.  All ledger calls retained the complete
organizer notice and metadata; labels were excluded from every message.  The
full policy, v24 separation, three independent cohorts, fallback rule, output
cap, model, and context were fixed before this 200-row calculation.

The next permitted operation is an **offline, explicitly historical**
composition of the already frozen source-complete `v2/v3/v21` predicates.
Those rules were not discovered from INC-125, and their condition/evidence
audits already exist.  It may measure the combined teacher ceiling, but it
does not validate a new hidden-test rule and must not trigger further
item-specific tuning.  After that, the priority is a Gemma transfer design
that uses the permitted teacher records or context while preserving a real
Gemma full-notice call and submission runtime.
