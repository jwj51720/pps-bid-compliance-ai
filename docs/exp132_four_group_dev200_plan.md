# EXP132 — frozen four-group organizer dev-200 confirmation

EXP132 is the dev-200 confirmation of EXP130/131. It is not a new prompt
experiment: every inference-policy field is identical to EXP130. The only
change from the fast-panel config is removing the selector so all 200 dev
notices run.

The two predeclared gates passed:

| Cohort | Full organizer control | Four groups |
|---|---:|---:|
| `dev_fast_panel_v1` | .17196 | .30020 |
| label-blind `dev_prompt_holdout_v1` | .12500 | .20833 |

Before calls, rerender and read the shared-policy inputs for a complete
reference fixture (`PPS-DEV-062`), a truncated announcement (`-042`), and an
attachment overflow notice (`-01`). Run preflight, grouped mock, and exact
Gemma tokenizer admission over all 200×4 calls. The audit must prove exactly
four calls per notice and record the maximum token count.

Evaluate macro positive F1 and all item TP/FP/FN versus the existing canonical
baseline. Record group output-token distribution, parse errors, and latency.
Do not make a submission or alter canonical config from this run: 800 remote
calls are only a quality confirmation. Submission feasibility additionally
requires an offline-vLLM 1,900-notice runtime projection, because grouping is
four calls per notice and batch size cannot reduce that count.
