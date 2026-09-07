# Cost-bounded Experiment Loop

## Objective

Build evidence for a better item-aware inference policy without repeatedly
spending on full dev-200 runs or overfitting a prompt to a handful of labels.
Each run produces a decision: reject, diagnose, refine, or promote.

## The loop

| Stage | Required action | Output / gate |
|---|---|---|
| 0. Design card | Define one hypothesis, changed variable, fixed comparator/cohort, request and KRW/USD ceiling, expected failure mode, and promotion rule. | Versioned config and run plan; no API call yet. |
| 1. Offline audit | Run parser, cue/fact extraction, law selection, token admission, and evidence-window construction without a model. | All inputs are valid; candidate recall/coverage is reported against dev; no fixed context exceeds budget. |
| 2. Small pilot | Call OpenRouter Gemma on a deterministic cohort designed to contain affected positives *and* hard negatives. Use the exact saved messages from Stage 1. | Raw responses, parsed predictions, per-item deltas, token/cost/runtime, and failure rate. |
| 3. Forensic review | Compare every changed `(notice, item)` result with gold, source text, extracted facts, and selected law chunks. | A concise error ledger distinguishes legal/prompt/retrieval/merge/extraction failures. |
| 4. Decision | Reject if the hypothesized failure did not move or gains come only from an invalid comparison. Refine one cause, or promote using the declared rule. | `decision.md` naming the next action and risks. |
| 5. Dev-200 confirmation | Re-run only promoted candidates and their unchanged comparator with frozen code/model/settings. | Macro F1, per-item P/R/F1, bootstrap uncertainty, evidence checks, cost, and runtime projection. |
| 6. Readiness review | Test held-out operational behavior: missing docs, long notices, malformed output, no-candidate notices, and submission fixture. | Integration proposal or rejection; never an automatic submission. |

## Cohort policy

Small pilots are diagnostic cohorts, not “first 20” by default. Select IDs before
calling the API and save them as an input artifact:

1. affected gold positives for each target item, where available;
2. hard negatives that share the same cue, contract law, product status, or
   price bracket;
3. representative no-cue negatives to expose over-triggering;
4. incomplete-document notices when absence logic is under test.

For a group with sparse positives, use all its dev positives plus matched
negatives. Do not advertise a group-level success based on a cohort with no
positive examples for the item.

## Promotion rules

Before a pilot, choose one of these rules and record it.

- **Extraction/retrieval rule:** all gold-positive source cues or required facts
  in the cohort must remain reachable; any lost positive is a blocker unless the
  source proves it is out of scope.
- **Judgment rule:** target-item F1 improves without reducing recall, or the
  precision/recall trade-off is explicitly justified and survives hard negatives.
- **System rule:** no schema/evidence regression; projected final calls and
  tokens fit the 1,853-notice, two-hour limit.

A dev-200 confirmation is required if a change modifies merge semantics,
candidate suppression, retrieval, a legal reference bundle, or any final
decision correction.

## Required artifacts per run

`runs/<experiment_id>/` must contain:

```text
plan.yaml                 hypothesis, comparator, cohort hash, budget, gates
config.yaml               complete executable settings
inputs.jsonl              final messages and token counts (local-only)
responses.jsonl           raw transport responses and usage (local-only)
predictions.csv           49-column result
metrics.json              headline and per-item metrics
per_item_metrics.csv      TP/FP/FN, precision, recall, F1
error_ledger.jsonl        changed and sampled unchanged cases
decision.md               conclusion, rejected explanations, next step
```

All derived text and responses remain untracked. `decision.md` must be concise
enough to track later without including raw competition documents.

## Cost controls

- Mock preflight is mandatory for every new prompt, selector, or response schema.
- Begin with 20--40 requests only when each request tests a defined question.
  Group calls count separately from notice count.
- Set both `max_requests` and `max_cost_usd`; stop before retrying beyond either
  ceiling. Record provider errors separately from model errors.
- Use temperature 0, a fixed seed where supported, and a fixed model version.
- Reuse only identical cached calls keyed by model, parameters, prompt hash, and
  input-record hash; never reuse a response after a prompt or policy change.
- Expand to dev-200 only after a pilot meets its preregistered gate. Do not run
  simultaneous broad prompt variants.

## Metrics and interpretation

The decision table always leads with Macro positive-F1 but includes per-item
TP/FP/FN and P/R/F1. Evidence validity, substring overlap, parse rate, input and
completion tokens, requests, elapsed time, and cost are mandatory guardrails.

For dev-200, report notice-level bootstrap intervals for Macro F1 and the full
list of changed predictions. The interval does not make dev representative of
test; it prevents treating a one-example change as a robust discovery.
