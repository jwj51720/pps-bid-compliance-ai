# INC-126: Luna + frozen rule composition result

## Result

| Policy | Dev-200 macro positive-F1 | Delta |
|---|---:|---:|
| INC-125 official-ledger Luna policy | 0.427366 | — |
| INC-125 + frozen `v2/v3/v21` source predicates | **0.462222** | **+0.034856** |

This is the highest local Luna result to date.  It replaces only 18 of the
600 item-record cells covered by the three predicates.  All resulting positive
evidence strings are unchanged source substrings; the predicates' source,
metadata, official-law, and negative-activation conditions were frozen before
INC-125.

| Item | INC-125 F1 | Composed F1 | INC-125 TP / FP / FN | Rule TP / FP / FN |
|---|---:|---:|---:|---:|
| v2 | 0.538462 | 1.000000 | 7 / 12 / 0 | 7 / 0 / 0 |
| v3 | 0.875000 | 1.000000 | 7 / 1 / 1 | 8 / 0 / 0 |
| v21 | 0.750000 | 1.000000 | 6 / 4 / 0 | 6 / 0 / 0 |

## Interpretation

This is intentionally an historical composition, not an independent
generalization estimate: each predicate was originally audited on dev200.
Its value is that the new Luna ledger policy did not supersede clear,
source-complete conditions; it made errors on them that an already justified
deterministic policy corrects.  There is no authority to add another rule from
the remaining errors.

## Next direction

The teacher ceiling is now established.  The next score-bearing target must be
Gemma, because a submission still requires a real full-notice Gemma call.  The
next experiment should not repeat the rejected global ledger/e-prime transfer.
It will first audit whether a **single-call, full-notice Gemma operational
contract**—explicitly separating restriction, applicability-then-absence, and
same-field v24 comparison—has not already been tested under the EXP-120
4,000-character/card-v6 policy.  Only a genuinely untested, one-variable
contract gets a fresh paired 32-notice pilot; otherwise the next branch is a
teacher-record retrieval design with a separate source-preservation gate.
