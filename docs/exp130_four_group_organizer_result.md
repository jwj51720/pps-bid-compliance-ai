# EXP130 — four-group organizer prompt diagnostic result

Plan: [EXP130 plan](exp130_four_group_organizer_plan.md)  
Config: `configs/config.exp130-four-group-organizer-fast-panel.yaml`  
Ignored artifacts: `outputs/exp-130-four-group-organizer-fast-panel/`,
`outputs/prompt-audit-exp130/`, `outputs/prompt-admission-exp130/`

## Preconditions verified

- Preflight declared exactly `prompt.profile` and the three versioned grouped
  execution fields; mock completed all 20 rows × 4 groups.
- Exact rendered inputs were read for `PPS-DEV-062`, `-042`, and `-01` at
  `outputs/prompt-audit-exp130/*.grouped.messages.md`.
- Each notice's four user messages had the same SHA-256. Each system prompt
  and JSON schema contained only its declared group keys. The real `[절단]` and
  `[미수록 문서]` markers remained visible in every relevant group prompt.
- Exact Gemma tokenizer admission over all fast-20 inputs is recorded in
  `outputs/prompt-admission-exp130/admission.json`: 20 notices, exactly 80
  calls, maximum 3,719 input tokens. No document splitting occurred.

## Fast-panel result

| Setting | Macro positive-F1 | Parse errors | Calls | Sum call latency | Mean completion tokens/call |
|---|---:|---:|---:|---:|---:|
| EXP125A exact organizer 24-item control | .17196 | 0 | 20 | 226.9 s | 758.6 |
| EXP130 four organizer groups | **.30020** | 0 | 80 | 337.2 s | 216.8 |

The latency sum is not wall time: four notices are concurrent, while each
notice runs its four groups serially. It is still a 4× call-count design and
is not submission-safe without a separate large-scale runtime projection.

### Meaningful changes

The four groups recovered true positives for v1 (+1 TP, no FP), v2 (+1 TP,
no FP), v4 (+1 TP, +1 FP), v6 (+1 TP, +1 FP), v7 (+1 TP, no FP), v15 (+1 TP,
FP removed), and v24 (+1 TP, FP 6→0). Evidence span F1 also rose .332→.665.

The result is not uniformly beneficial: v8 added four FPs, v21 added six
additional FPs (2→8), v13 and v17 each lost their only TP, and v19 lost its
only TP. These must be evaluated on a cohort that was not used to choose the
grouping. No per-item prompt/card/rule was edited from these cells.

## Decision

This is the first prompt-structure signal that passes the frozen fast-panel
quality gate, but it is **not promoted**. Run the same config unchanged on
the previously frozen label-blind `dev_prompt_holdout_v1` cohort next. Reject
if the independent macro direction or source-visible recall does not hold;
only then consider dev-200 and runtime analysis.
