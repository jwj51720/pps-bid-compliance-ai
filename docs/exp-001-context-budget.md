# EXP-001 Context Budget Check

## Question

Can one Gemma call receive every document and metadata field for each dev notice while reserving output space for the 24 joint judgment/evidence objects?

## Method

The official evaluation limit is `max_model_len=32,768`, not the baseline's speed-oriented 16,384 setting. This check reserves 2,500 output tokens, leaving a 30,268-token prompt budget.

The local machine does not have the fixed evaluation model path or its tokenizer. We therefore use the recorded `prompt_tokens` from the completed same-model EXP-001 OpenRouter run. For each notice, the observed prompt-token count with the existing 4,000-character document context is scaled by the ratio of an otherwise identical full-document prompt's characters to its original prompt characters. This is an estimate, not final tokenizer validation.

## Result

For the 200 dev notices, 196 are estimated to fit; 4 exceed the 30,268-token prompt budget. Estimated full-prompt tokens are median 9,759, p95 29,044, and maximum 37,098. The four estimated overflows are `PPS-DEV-123`, `PPS-DEV-11`, `PPS-DEV-143`, and `PPS-DEV-169`.

Thus the next pipeline should pass all documents unchanged whenever the supplied Gemma tokenizer reports that they fit, and apply deterministic token-budgeted selection only to overflow notices. Before a submission, validate the final chat template with `runner.count_tokens()` using `PPS_MODEL_DIR`; do not treat this scaling estimate as an admission check.

## Reproduction

```bash
.venv/bin/python scripts/estimate_context_budget.py
```

The machine-readable artifact is `outputs/exp-001-context-budget/estimate.json`.
