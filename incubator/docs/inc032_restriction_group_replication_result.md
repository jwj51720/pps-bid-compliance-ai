# INC-032: Restriction-Group Output Replication Result

## Validity

All 200 fresh calls completed successfully; no parse/transport failure occurred.
Retained positive evidence validity is 100%. Reported cost is $0.23419410.

## Replication result

| Run | Target Macro F1 | TP / FP / FN | Micro recall |
|---|---:|---:|---:|
| INC-030 no-law group | 0.30948 | 11 / 31 / 14 | 0.44000 |
| INC-032 exact repeat | 0.22577 | 9 / 36 / 16 | 0.36000 |
| Repeat minus original | -0.08371 | -2 / +5 / +2 | -0.08000 |

INC-032 fails the preregistered target-F1 floor (0.25), recall floor (0.36 is
equal but not compensatory), and maximum allowed divergence from the original
run (0.05). The run is therefore not a stable component.

For transparency only, replacing v4/v6/v7/v8 in immutable INC-018 with the
first group run gives overall Macro F1 0.24519, while replacing them with the
independent repeat gives 0.23124. Both are above the historical 0.19361
baseline, but neither is a valid promotion: the component itself failed its
repeat gate and its two realized improvements differ materially. These are
counterfactual diagnostics, not submission estimates.

## Decision

**Rejected.** Do not use output-group partitioning for v4/v6/v7/v8, do not
select the better of the two runs, and do not form an ensemble from them. Along
with INC-024, this closes standalone output-topology changes as a reliable
route. The experiment establishes a required process change: an apparent
small-cohort or single-run gain must be independently replicated before it can
be composed into a global policy or escalated.

The remaining promising directions must reduce reliance on stochastic legal
judgment itself—for example, source-grounded deterministic fact extraction with
an externally justified predicate—not merely redistribute the same judgment
across calls.
