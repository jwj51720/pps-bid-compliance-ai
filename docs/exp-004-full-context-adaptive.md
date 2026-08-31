# EXP-004: Full-Context Adaptive Token Admission (200 Dev Notices)

## Objective

Benchmark the same 200-notice dev set used by EXP-001 against its historical
4,000-character baseline, while removing the document character cap. Each
notice first receives exact Gemma-token admission. If the final prompt exceeds
30,268 tokens (32,768 less the fixed 2,500 output reserve), it is split into
ordered token-admitted passes and merged item-wise with OR.

## Controlled settings

- Model: `google/gemma-4-26b-a4b-it` through OpenRouter
- Prompt mode: baseline item prompt; no law package, RAG, self-labels, or rules
- Generation: temperature 0, seed `20260826`, max output tokens 2,500
- Inputs and labels: official dev 200 / `dev_labels.csv`
- Historical comparator: `exp-001-first-submission`, which uses the same paid
  model family, temperature, seed, and output reserve but limits documents to
  4,000 characters.

## Reproduction

```bash
.venv/bin/python scripts/run_experiment.py \
  --config configs/config.exp004-full-context-adaptive-paid.yaml --fresh
```

Record macro positive-class F1, per-item precision/recall/F1, evidence metrics,
runtime, token usage, cost, and the number of one- versus multi-pass notices.

## Results

All 200 notices passed exact token admission as one full-context pass. No split
pass was created: pass-count distribution is `{1: 200}`. Prompt tokens have a
median of 9,462, p95 of 27,620, and maximum of 29,867; the maximum remains
below the 30,268-token prompt budget.

| Metric | EXP-001 4,000-char baseline | EXP-004 adaptive full context | Delta |
|---|---:|---:|---:|
| Dev macro positive-class F1 | 0.220416 | 0.213825 | -0.006591 |
| Evidence validity | 0.795082 | 0.832278 | +0.037196 |
| Evidence span F1 | 0.322106 | 0.368826 | +0.046721 |
| Evidence exact match | 0.055556 | 0.111111 | +0.055556 |
| Positive evidence cases | 244 | 316 | +72 |
| Prompt tokens | 772,945 | 2,431,777 | +1,658,832 |
| Completion tokens | 135,312 | 139,715 | +4,403 |
| Reported cost | $0.1221054 | $0.2904333 | +$0.1683279 |
| Runtime | about 508s from initial start to completion | 441.862s | not directly comparable |

The full-context run produces materially more valid and better-overlapping
evidence, but it lowers the primary classification metric and costs about 2.38x
as much. Runtime is not a clean comparison because the historical run resumed
twice and its `run_meta.json` captures only the last resume segment.

### Per-item classification change

| Item | Baseline F1 | Full-context F1 | Delta |
|---|---:|---:|---:|
| v2 | 0.400000 | 0.444444 | +0.044444 |
| v3 | 0.608696 | 0.457143 | -0.151553 |
| v4 | 0.222222 | 0.333333 | +0.111111 |
| v5 | 0.380952 | 0.352941 | -0.028011 |
| v7 | 0.250000 | 0.000000 | -0.250000 |
| v8 | 0.285714 | 0.000000 | -0.285714 |
| v9 | 0.200000 | 0.294118 | +0.094118 |
| v11 | 0.000000 | 0.250000 | +0.250000 |
| v13 | 0.067797 | 0.081967 | +0.014171 |
| v19 | 0.571429 | 0.400000 | -0.171429 |
| v20 | 0.000000 | 0.285714 | +0.285714 |
| v21 | 0.166667 | 0.208333 | +0.041667 |
| v23 | 0.200000 | 0.000000 | -0.200000 |
| v24 | 0.190476 | 0.277778 | +0.087302 |

The other ten items are unchanged: v1, v6, v10, v12, v14, v15, v16, v17, v18,
and v22. The primary loss is concentrated in v3, v7, v8, v19, and v23; gains
in v4, v9, v11, v20, and v24 do not offset it.

## Interpretation

This is a valid full-context benchmark, but not a split-overflow efficacy test:
the adaptive branch did not split any dev notice. It rejects the hypothesis that
more raw notice text alone raises dev macro F1 for the generic joint prompt.
The next experiment should retain exact token admission for safe submission
execution while adding source-backed decision conditions or targeted prompt
structure, then compare against both recorded EXP-001 and EXP-004 outputs.

## Submission parity correction

The first generated EXP-004 archive copied the organizer baseline to obtain a
quick vLLM entrypoint. That copy used its own token-shrinking fallback and did
not invoke the shared adaptive splitter, violating the project invariant that
experiments and submissions call the same pipeline. It was discarded before
submission.

The replacement archive packages `submission/script.py` and `src/`. Its offline
vLLM client loads `PPS_MODEL_DIR`, exposes the runner tokenizer's
`count_tokens()` callback, and injects it into `BaselinePipeline` with
`overflow_split_enabled=True`. Thus the exact same full-context admission,
overflow splitting, OR merge, evidence postprocessing, and CSV validation are
used in benchmark and submission paths. `scripts/make_submission.py` stages
only these tracked sources, and the staged script is mock-tested against the
official 10-notice test fixture before delivery.
