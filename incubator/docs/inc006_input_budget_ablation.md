# INC-006: Ordered Input-Coverage Ablation

## Locked experiment

INC-005 found that the simple pilot exposes only about one-third of source
document characters while output use is comfortably below its cap. INC-006
tests one cause only: ordered document input budget.

The frozen INC-001 cohort of 24 notices is evaluated in paired contemporary
calls. Both arms use the same Joint-24 system prompt, metadata, ordered source
documents, model, seed, schema, temperature, output cap, and evidence
validator. The only changed value is the document-prefix character budget:
4,000 versus 12,000. No product fact, law text, card, retrieval, rule, or
output-shape change is permitted.

The 12,000-character budget is deliberately a bounded middle ground. It is
well within the recorded 32k model admission policy and is not a rerun of the
historical all-document context experiment.

## Gates

- Transport: at least 95% successful parseable requests per arm; raw response
  must be checkpointed before parsing in any future runner repair.
- Coverage: 12,000 characters must materially increase mean source-document
  character coverage.
- Effect: 12,000-character macro positive-F1 improves by at least 0.02 and
  has non-decreasing recall (summed across 24 labels).
- Safety: evidence validity must not decline by more than 0.05 and no label
  incurs more than three new false positives.

Success advances the larger budget to one dev-200 confirmation. Partial
success permits one follow-up that changes only the packing method, not the
budget. Failure rejects generic budget expansion and moves to item-local
candidate windows or typed facts.

## Result

All 48 paired requests completed with parseable raw output and `stop` finish
reasons. The 12,000-character arm increased document-character coverage from
20.77% to 56.26% and complete-notice count from one to nine, for a total
reported API cost of $0.05268.

| Policy | Macro F1 | TP / FP / FN | Micro recall | Evidence validity | Prompt / completion tokens | Cost |
|---|---:|---:|---:|---:|---:|---:|
| Ordered 4,000 chars | 0.07963 | 5 / 33 / 32 | 0.13514 | 0.71053 | 90,484 / 16,280 | $0.02103 |
| Ordered 12,000 chars | 0.18407 | 11 / 27 / 26 | 0.29730 | 0.84211 | 188,883 / 15,060 | $0.03164 |

The treatment changes are +0.10444 Macro F1, +6 TP, -6 FP, -6 FN, and +13.16
percentage points of evidence validity. No item acquired more than one new
false positive, satisfying the safety guard. The added input cost is about
$0.01061 on this 24-notice cohort; completion use did not grow.

## Decision

**Success.** This is the first independent policy change to pass its effect,
recall, evidence, transport, and false-positive gates. It does not supersede
the historical dev-200 baseline: the cohort is deliberately diagnostic and the
contemporary 4,000-character result is lower than INC-001's prior run, so only
the paired delta is decision evidence.

The next permitted action is a frozen dev-200 confirmation of the 12,000
character policy against a contemporary 4,000-character control, with the same
raw-before-parse checkpointing and lock. Before starting it, calculate the
request/cost projection and stop if the confirmed full-dev cost would exceed
the experiment cap. Do not mix product facts, law context, rules, or output
format changes into that confirmation.
