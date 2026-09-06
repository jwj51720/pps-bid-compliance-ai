# INC-030: Restriction-Law Context Dev-200 Confirmation Result

## Validity

All 400 calls completed successfully (200 control, 200 law). No provider
admission, transport, or parse failure occurred. Complete legal units and whole
notice documents were retained; no length repair occurred. Reported API spend
was $0.55275713, below the $0.70 ceiling. Retained positive evidence was
source-valid in both arms (100%).

## Confirmation result

| Arm | Target Macro F1 | TP / FP / FN | Micro recall | Cost |
|---|---:|---:|---:|---:|
| Whole notice, no law | 0.30948 | 11 / 31 / 14 | 0.44000 | $0.23248 |
| Same notice + complete applicable law | 0.24991 | 9 / 22 / 16 | 0.36000 | $0.32027 |
| Law minus control | -0.05957 | -2 / -9 / +2 | -0.08000 | +$0.08779 |

Per-item treatment-minus-control F1 is v4 `+0.02670`, v6 `-0.15385`, v7
`-0.14141`, v8 `+0.03030`. Thus the legal context is a precision suppressor
for this group but makes the already low v6/v7 recall worse. Its 10,000
notice-bootstrap paired Macro-F1 delta has p05 `-0.20006`, median `-0.05291`,
and p95 `+0.07672`; the required lower bound of zero is decisively unmet.

## Pilot reproducibility check

The exact 36 INC-029 notices are included in INC-030. Under the same recorded
model, temperature, seed, messages, schemas and law units, the repeated
subset itself changed materially:

| Run / arm on the same 36 notices | Macro F1 | TP / FP / FN |
|---|---:|---:|
| INC-029 control | 0.30880 | 9 / 15 / 16 |
| INC-029 law | 0.38515 | 9 / 8 / 16 |
| INC-030 repeat control | 0.41414 | 11 / 13 / 14 |
| INC-030 repeat law | 0.36397 | 9 / 5 / 16 |

There are 8/144 target-label disagreements for the repeated control and 7/144
for the repeated law arm. This is observed provider/model-path output variation
despite the requested seed; it is not safe to attribute it to a particular
backend mechanism. It means the INC-029 apparent gain was not replication-safe
even before considering the remaining 164 notices. Future paid pilots must
pre-register an independent repeat before escalating on a small-cohort gain.

## Decision

**Rejected.** INC-030 fails every performance promotion condition except
evidence validity: target Macro F1 is lower, recall decreases, and bootstrap
support is negative. Do not promote complete legal context for v4/v6/v7/v8,
do not merge it with the control, and do not alter law boundaries or prompt
wording to rescue it. Preserve its source-unit resolver only as provenance
infrastructure.

The broad methodological lesson is that legal context can suppress false
positives without giving Gemma a reliable applicability decision. The next
research program must distinguish deterministic applicability facts from
judgment and incorporate replicated provider calls into pilot gates; another
global context/prompt topology is explicitly deprioritized.
