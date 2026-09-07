# INC-130: EXP-123 frozen-fold stability audit

INC-130 makes no model call and creates no new rule.  It applies the predicates
already frozen before EXP-123 to the archived EXP-120 predictions, then scores
the existing label-balanced INC-076 folds independently.

| Fold | Records | Archived EXP-120 | EXP-123 composition | Delta |
|---|---:|---:|---:|---:|
| fold_0 | 100 | 0.262247 | 0.319192 | **+0.056944** |
| fold_1 | 100 | 0.222421 | 0.305754 | **+0.083333** |
| full dev200 (recalculated) | 200 | 0.248932 | 0.317797 | **+0.068865** |

All positive frozen-rule evidence remains an unchanged source substring.  The
rules change 22 cells across the 600 item-record positions.  In both folds,
v2, v3, and v21 rise to F1 1.0 from baseline values respectively `(0.5, 0.8,
0.333)` and `(0.333, 0.667, 0.0)`.

The full score is not the arithmetic mean of the two fold macro-F1 values:
positive-class F1 is recomputed from pooled TP/FP/FN.  A direct all-200
recalculation reproduces the INC-123 lineage exactly, resolving the apparent
metric difference.

This supports the direction of the source-complete correction on both frozen
partitions, but does not make it an independent hidden-test estimate because
predicate discovery predates the split and used dev labels.  The public
leaderboard submission remains the required external generalization check.
