# INC-063: Repeated Joint-Judgment Consensus Result

All 144 grounded Joint-24 calls parsed, but consensus fails its performance and
evidence gates.

| Policy | Macro F1 |
|---|---:|
| Raw r1 | 0.17079 |
| Raw r2 | 0.19399 |
| Raw r3 | 0.21203 |
| Mean raw | 0.19227 |
| Three-run majority | 0.18425 |

The consensus also had at least one positive label for which no positive
member run supplied source-valid evidence, so its evidence contract is false.
This cannot be repaired by choosing a different member evidence or dropping
that cell after seeing the score.

**Reject.**  Provider variability is real, but equal global majority does not
improve this task and loses grounded positives.  Do not run an all-dev
consensus, change the vote threshold, or make item-specific voting rules.
