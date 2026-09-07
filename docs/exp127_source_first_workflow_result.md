# EXP127/128 — source-first workflow prompt result

Plan: [EXP127 plan](exp127_source_first_workflow_plan.md)  
Configs: `config.exp127-source-first-workflow-fast-panel.yaml`,
`config.exp128a-exact-baseline-holdout.yaml`,
`config.exp128b-source-first-workflow-holdout.yaml`  
Raw artifacts: ignored `outputs/exp-127-source-first-workflow-fast-panel/`,
`outputs/exp-128a-exact-baseline-holdout/`,
`outputs/exp-128b-source-first-workflow-holdout/`

## Hypothesis and exact change

The treatment appended exactly four process-only lines before the existing
organizer item list:

1. locate actual source restriction/requirement/mismatch or required absence;
2. use metadata only to check applicability and same-field correspondence;
3. do not widen one sentence to similar items; and
4. do not supplement unknown facts; use 0 when uncertain.

It added no cards, law/reference material, product facts, item grouping,
document-context change, decoding change, schema change, merge change, or
post-processing rule. Preflight found only `prompt.role_directive`; mock runs
completed 20/20. Exact rendered messages were inspected at:

- `outputs/prompt-audit-exp127/pps-dev-077.messages.md` — complete short notice;
- `outputs/prompt-audit-exp127/pps-dev-01.messages.md` — truncated announcement
  with omitted attachments;
- `outputs/prompt-audit-exp127/pps-dev-123.messages.md` — long notice with two
  omitted proposals.

The same treatment rendering was inspected for `PPS-DEV-046` and `082` under
the independent-cohort config. The directive did not claim omitted attachments
had been read. Gemma `apply_chat_template` admission was 200/200 one pass,
maximum 4,349 input tokens against the 14,848-token prompt budget.

## Results

| Cohort | Exact V/E control | Source-first treatment | Result |
|---|---:|---:|---|
| Frozen `dev_fast_panel_v1` (20) | 0.171958 (EXP125A, fresh prior control) | **0.208369** (EXP127) | Directional gain only |
| Label-blind `dev_prompt_holdout_v1` (20) | **0.125000** (EXP128A) | 0.041667 (EXP128B) | Rejected |

All three provider runs completed 20/20 with no parse-error record. EXP127
used 48.1 seconds; EXP128A and B used 49.2 and 45.0 seconds respectively.
The output contract remained V/E. The treatment therefore did not offer a
runtime reason to offset the failed quality gate.

## What changed on the independent cohort

The decisive comparison is EXP128A → EXP128B, not its absolute score.

| Measure | Control | Treatment | Change |
|---|---:|---:|---:|
| Global TP | 3 | 1 | -2 |
| Global FP | 28 | 32 | +4 |
| Global FN | 12 | 14 | +2 |
| Positive recall | 20.0% | 6.7% | -13.3pp |
| Positive precision | 9.7% | 3.0% | -6.7pp |

The two lost true positives were both visible in the supplied 4,000-character
announcement context:

- `PPS-DEV-053/v2`: the control correctly used the explicit 1억원 이상 유사사업
  실적 참가자격; treatment returned 0.
- `PPS-DEV-050/v9`: the control correctly detected the supplied model phrase
  `트랙터용 로우더 / k2-600급`; treatment returned 0.

The treatment also created 12 new false positives, chiefly by treating ordinary
small-business eligibility text as violations:

- v13: +4 FP;
- v17: +8 FP.

This is the opposite of the intended “do not widen one sentence” effect. It
shows that a generic reading-order instruction does not stably establish the
semantic boundaries between product/amount applicability items. The fast-panel
gain came from two recovered TPs (v2, v14), while it simultaneously lost v17's
only TP and introduced FP; it was not a broad improvement signal.

## Decision

Do **not** run this directive on dev-200, submit it, or create wording variants.
It fails the predeclared independent recall and macro gates. This closes the
generic workflow-directive branch.

The next prompt audit must not add more generic caution language. It should
inspect, item by item, whether the information needed for a gold decision is
already present in the raw item-table phrase, in the 4,000-character notice
context, and in the V/E output contract. Only an observed missing or ambiguous
semantic boundary may justify a new, narrowly declared prompt component.
