# INC-099: v11 specialist plus exact-code applicability veto

## Result

This is a no-API diagnostic merge, not a promoted dev-200 score.  Starting
from INC-088's full-context, high-reasoning Luna output, replace **only** v11
with the INC-097 specialist result when it is available.  If the specialist
returns 1 but an organizer-provided 10-digit product code is explicitly absent
from the organizer competition-product CSV, veto that 1.  Missing codes remain
unknown and are not vetoed.

| Metric | INC-088 joint high | v11 merge + exact-code veto |
| --- | ---: | ---: |
| v11 TP / FP / FN | 0 / 0 / 6 | 2 / 0 / 4 |
| v11 positive F1 | 0.000 | 0.500 |
| 24-item macro positive F1 | 0.36073 | 0.38156 |

The two retained v11 positives have no exact product code, so they are not
being inferred from a non-match.  All four specialist false positives have
provided exact codes that do not occur in the competition-product CSV, so the
v11 card's explicit non-competitive-product condition logically rules them
out.  The five rate-limited specialist notices retain the joint prediction.

## What this does and does not prove

It proves that INC-097's apparent false-positive mechanism was a missing
applicability fact in that specialist prompt, and that an exact organizer CSV
can constrain it without a fitted threshold.  It does **not** prove a
generalizable score gain: the discovery and measurement share dev-200, only
six v11 positives exist, and the specialist itself is incomplete.

## Next gate

Before any more expensive full dev-200 call, run a small predeclared
source-role diagnostic that includes the product applicability state from the
start and requires the model to distinguish bidder eligibility from
post-award/incidental mentions.  Only if it removes the observed role errors
without suppressing the two retained positive patterns should a fresh,
complete 200-notice confirmation be considered.  A confirmation must use a
new prompt version and a bounded request/cost ceiling; no xhigh escalation.
