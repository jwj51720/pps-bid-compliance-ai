# INC-076 Result: Frozen Holdout Reset

The final deterministic split has exactly 100 notices in each fold.  Every
item has at least two positives in each fold (the rarest item counts are 2/3),
so no future family comparison is forced to score an item with zero positives.

The immutable INC-041 composition scores:

| Fold | Size | Macro F1 |
|---|---:|---:|
| fold_0 | 100 | 0.25580 |
| fold_1 | 100 | 0.27625 |

The 0.02045 difference is not a hidden-test estimate because all prior work
has already seen dev-200.  It is nevertheless a concrete warning that small
pilot deltas below this scale cannot justify integration.  The split and ID
hashes in `runs/inc076_frozen_holdout_audit/holdout.json` are frozen for
prospective work: explore on one fold only, then make one unchanged
confirmation on the other before an all-dev run.

This changes the research process rather than the root pipeline.  It is the
necessary reset after repeated full-dev prompt/context ablations, not evidence
that a particular prompt is better.
