# INC-076: Frozen Holdout Reset

The dev-200 set has now been used in many exploratory decisions.  Continuing
to choose prompt direction from its aggregate score is more likely to optimize
local noise than hidden-test behavior.  INC-076 creates two deterministic,
multi-label-positive-balanced folds using labels only for split assignment.

The immutable INC-041 composition is scored on both folds as a stability
diagnostic.  The split is not retrospective proof: prior experiments have
already seen all 200 labels.  Its role is prospective governance:

1. New ideas are designed from source/law reasoning and explored only on one
   designated fold.
2. A single frozen configuration is run once on the opposite fold.
3. Only a same-direction confirmation can consume all-dev budget.

This preserves rare-label representation without inventing a score-based
threshold, and stops iterative full-dev prompt tuning.
