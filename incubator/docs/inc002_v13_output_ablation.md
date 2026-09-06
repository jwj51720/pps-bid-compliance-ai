# INC-002: V13 Output-Scope Ablation

## Hypothesis and design

INC-001 showed v13 over-prediction. This run tested the narrow hypothesis that
the false positives are caused primarily by generating v13 alongside the other
23 items.

The fixed 18-notice cohort contains all six dev v13 positives and 12 all-negative
notices that the preserved historical baseline predicted positive for v13. Each
notice received two calls with the same 4,000-character ordered document context,
metadata, model, temperature, seed, and evidence contract.

- **Control:** joint output for v1--v24.
- **Treatment:** v13-only output.

No product code fact, price fact, legal text, card, retrieval, rule correction,
or self-labeled case was introduced. The only intended variable is output/prompt
scope.

## Result

| Policy | Requests | v13 TP / FP / FN | Precision | Recall | F1 | Evidence validity | Cost |
|---|---:|---|---:|---:|---:|---:|---:|
| Joint-24 control | 18 / 18 | 6 / 8 / 0 | 0.42857 | 1.00000 | **0.60000** | 0.42857 | $0.01546 |
| V13-only treatment | 18 / 18 | 1 / 0 / 5 | 1.00000 | 0.16667 | **0.28571** | 0.00000 | $0.00790 |

The treatment changed v13 for 13 of 18 notices. It removed all eight control
false positives, but also removed five of six true positives. Completion tokens
fell sharply (12,180 to 472), so the treatment is operationally cheaper but
legally too conservative. Both policies had successful transport/schema calls.

## Decision

**Failure; do not promote v13-only output.** The preregistered effect gate
required F1 improvement, non-decreasing recall, and lower FP. The treatment
meets only the FP condition. It is not valid to claim that narrowing the output
scope solves v13 over-prediction.

The result changes the next direction. A v13-only prompt with product facts
would conflate the recall loss caused by output scope with the effect of those
facts. The next clean experiment should preserve the joint-24 control and add
only a concise, organizer-CSV exact product applicability fact for v13. It will
measure whether that fact can remove false positives while retaining the joint
prompt's recall. This is a new single-variable treatment; it is not an attempt
to repair INC-002 by adding multiple changes.
