# EXP140 — independent two-call G02 overlay result

## Result

The frozen independent holdout achieved macro positive F1 **0.257576**.

| Experiment | Macro F1 | Non-G02 mean F1 | G02 mean F1 |
| --- | ---: | ---: | ---: |
| EXP128A exact organizer single call | 0.125000 | 0.105263 | 0.200000 |
| EXP134 disjoint `19 + 5` calls | 0.208333 | 0.157895 | 0.400000 |
| EXP140 full call + five-key overlay | **0.257576** | **0.220096** | **0.400000** |

G02's per-item F1 was `v6=0`, `v7=1`, `v8=0`, `v9=1`, `v19=0`. There
were no parse errors. Validation passed with nine non-strict evidence warnings.
The run used 40 calls and summed 404.37 seconds of provider latency.

## Interpretation

This independently confirms that the EXP139 fast-panel gain was not solely a
fast-panel artifact. It does not establish a submission policy: the G02 gain
is tied with EXP134 here and the full overlay doubles calls. The next required
test is a separately configured dev-200 run with no policy changes, followed
by an explicit quality/runtime decision.
