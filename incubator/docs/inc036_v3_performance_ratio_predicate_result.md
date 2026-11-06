# INC-036 Result: v3 Performance Predicate

## Frozen method

The diagnostic accepts an unchanged source line only when it contains a
performance term, Korean won amount, lower-bound expression, and a bidder-
qualification predicate. Exactly one source amount is required; it is compared
to raw `배정예산금액`. Ambiguous amounts and non-qualification mentions are
unknown/zero. This implements the organizer item's `사업예산 기준` note and
the source-package national/local one-times estimated-price ceiling; it has no
development-derived number, character radius, model call, or ranking rule.

## Result

On all 200 dev notices: TP 8, FP 0, FN 0, F1 1.00000. All eight positive
evidence strings were unchanged notice substrings. Of the remaining notices,
184 had no eligible explicit source condition, seven had a below-budget
condition, and one had a multi-amount ambiguity.

The initial broad line filter produced four false positives. They were
performance words in non-qualification roles (evaluation tables and research
cost administration), not counterexamples to the numeric legal predicate.
The final eligibility requirement is a legal-role distinction, not a tuned
amount or length parameter.

## Decision

Advance only as an independently auditable component. The dev set has eight
positives, so this result neither estimates hidden-test F1 nor authorizes
additional phrase/exception tuning. INC-037 verifies controlled composition
with the frozen global baseline.
