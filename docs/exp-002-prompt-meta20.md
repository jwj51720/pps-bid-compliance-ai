# EXP-002: Prompt and Native-Metadata Ablation (20 Notices)

## Scope

All conditions use the first 20 dev notices, full supplied documents, the paid fixed Gemma model, temperature 0, seed `20260826`, and a 2,500-token output allowance. No law-package text, product CSV, BGE index, RAG, dev-label rule, or self-label data is used.

| Condition | Change from full-document baseline | Macro F1 | Prompt tokens | Cost |
|---|---|---:|---:|---:|
| Baseline | Item names, absence flags, notes | 0.13214 | 282,789 | $0.03369 |
| EXP-002A | Generic judgment guidance and all official item-table reference strings | 0.08796 | 328,589 | $0.03660 |
| EXP-002B | EXP-002A plus normalized facts restated from the same notice metadata | 0.11221 | 333,745 | $0.03638 |
| EXP-002C | Concise common evidence-first judgment procedure; no extra reference data | 0.08909 | 286,669 | $0.03379 |

## Result

The generic prompt guidance and legal-reference strings did not improve this cohort. Reformatting native metadata recovered some performance and added v7 F1 0.6667, but remains below the 0.13214 baseline. The concise EXP-002C process guidance also failed, despite adding only a small token overhead. More prompt text is therefore not itself a solution; it can distract the single joint 24-item judgment.

This does not reject structured prompt engineering. It rejects this first, broad all-item formulation. The next prompt experiment should keep the common guidance concise and make the item information easier to use, while preserving a strict token budget. No legal-package reference data should be added until that measurement is complete.

`PPS-DEV-11` used 32,157 prompt tokens in EXP-002A and 32,402 in EXP-002B. Either value plus the 2,500-token output allowance exceeds the 32,768-token submission sequence budget, so full-document packing must reserve space for any expanded prompt.

## Reproduction

```bash
.venv/bin/python scripts/run_experiment.py --config configs/config.exp002a-prompt20-paid.yaml
.venv/bin/python scripts/run_experiment.py --config configs/config.exp002b-prompt-meta20-paid.yaml
.venv/bin/python scripts/run_experiment.py --config configs/config.exp002c-guided20-paid.yaml
```
