# EXP139 — original 24-item call plus G02 overlay result

## Result

Frozen fast-panel (20 notices) macro positive F1 was **0.282080**.

| Experiment | Macro F1 | Non-G02 mean F1 | G02 mean F1 |
| --- | ---: | ---: | ---: |
| EXP125A exact single call | 0.171958 | 0.190894 | 0.100000 |
| EXP133 disjoint `19 + 5` calls | 0.261508 | 0.216291 | 0.433333 |
| EXP139 full call + five-key overlay | **0.282080** | 0.215960 | **0.533333** |

The focused group obtained F1 values `v6=0.6667`, `v7=1.0`, `v8=0.0`,
`v9=0.0`, `v19=1.0`. There were no parse errors. Submission CSV validation
passed; seven positive-evidence warnings remain, as in the non-strict
organizer-format policy.

## Runtime and caution

The run made 40 remote calls (two per notice). Sum provider latency was
339.36 seconds. This is not suitable for a submission decision yet: it costs
approximately twice the single-call policy and OpenRouter's nominally greedy
outputs may vary between independent executions. The original 24-item system,
user message, and schema were nevertheless byte-identical to EXP125A on all
three reviewed notices, so this is a valid test of the declared execution
scope rather than an accidental prompt rewrite.

The independent label-blind holdout is EXP140. Do not use this fast-panel
result alone to select a canonical or submission policy.
