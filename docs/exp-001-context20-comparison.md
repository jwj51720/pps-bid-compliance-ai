# EXP-001: 20-Notice Document-Context Comparison

## Hypothesis

The low EXP-001 score is materially caused by the 4,000-character document cap. Holding the first 20 dev notices, item prompt, metadata, model, temperature, seed, and 2,500-token output allowance fixed, compare the historical cap with all supplied documents.

## Conditions

| Condition | Source | Document input | Macro F1 |
|---|---|---|---:|
| Historical reference | `exp-001-first-submission` checkpoint, first 20 rows | 4,000 characters | 0.09028 |
| Full documents | `exp-001-context20-full-paid` | No character cap | 0.13214 |

The full-document result is higher by **0.04187**. `v9` changes from F1 0.0 to 1.0 on this small cohort; `v3` and `v13` also improve slightly. `v5` declines, and two `v24` positives are missed. The context change causes 13 binary-label changes, so added text affects the model rather than being ignored.

## Token Check

All 20 full-document prompts completed successfully. Observed prompt tokens ranged from 3,370 to 29,867; the largest requested sequence was `29,867 + 2,500 = 32,367`, below the 32,768-token evaluation limit. The largest realized prompt-plus-completion total was 30,669 tokens.

This verifies that the first 20 notices can safely use their full documents under the current joint-output allowance. It does not establish that all 200—or the private test set—will fit; retain per-notice token measurement and overflow packing for submission.

## Reproduction

```bash
.venv/bin/python scripts/evaluate_prediction_subset.py
.venv/bin/python scripts/run_experiment.py --config config.exp001-context20-full-paid.yaml
```

The 4,000-character reference was reused rather than rerun. It has the same historical paid model, prompt cap, temperature, seed, and output allowance, but not an independently repeated provider route; interpret this as a focused diagnostic, not a final benchmark.
