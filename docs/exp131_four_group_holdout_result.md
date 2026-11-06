# EXP131 — four-group organizer independent holdout result

Plan: [EXP131 plan](exp131_four_group_holdout_plan.md)  
Config: `configs/config.exp131-four-group-organizer-holdout.yaml`  
Ignored artifacts: `outputs/exp-131-four-group-organizer-holdout/`,
`outputs/prompt-audit-exp131/`, `outputs/prompt-admission-exp131/`

## Preconditions

The effective policy is unchanged from EXP130. Preflight found no policy
change; grouped mock completed 20 rows × 4 groups. Exact real inputs were
read for `PPS-DEV-094` (shortest holdout announcement), `-046` (specification
attachment omitted), and `-082` (specification and proposal omitted). For
each notice the four group user messages were byte-identical, while system
prompts and JSON schemas contained only group-local keys. Exact tokenizer
admission at `outputs/prompt-admission-exp131/admission.json` found 80 calls
and a maximum 3,788 input tokens.

## Result

| Setting | Cohort macro positive-F1 | Parse errors | Calls | Sum call latency |
|---|---:|---:|---:|---:|
| EXP128A exact organizer 24-item control | .12500 | 0 | 20 | 191.5 s |
| EXP131 organizer four groups | **.20833** | 0 | 80 | 344.9 s |

The direction therefore reproduces on the cohort that was frozen before
EXP130. The treatment recovered v1 and v7's only gold positives without false
positives, and retained the control's v2, v3, and v9 true positives. It also
reduced several control false-positive families (v13 7→1, v17 2→1, v19 3→0,
v24 7→3).

The remaining weakness is not hidden: v21 false positives rose 3→9; v8 gained
one FP; v15 and v17 each had a new FP; v23 retained its FN and one FP. No
item-specific wording, rule, or post-processing was changed in response.

## Decision

The fixed four-group organizer policy passes its two-cohort quality gate and
has no remote parse failures in 160 grouped calls. It is eligible for a
dev-200 confirmation with the policy frozen. It remains non-canonical and
non-submission-ready until that result and a separately reasoned 1,900-notice
runtime assessment are complete.
