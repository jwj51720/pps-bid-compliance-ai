# EXP127 — source-first prompt workflow fast-panel probe

## Hypothesis

The current exact organizer baseline presents a flat 24-item list and then the
notice.  It does not explicitly tell Gemma to separate (a) observable source
facts from (b) metadata applicability checks before assigning each item.

`source_first_v1` adds only a four-step reading workflow.  It neither adds
legal conditions nor changes the interpretation of an item, documents,
metadata, evidence, schema, decoding, or merge policy.

## Control and treatment

| Arm | Config | Difference |
|---|---|---|
| Control | `config.exp125a-exact-baseline-ve-fast-panel.yaml` | Exact organizer-format V/E baseline |
| Treatment | `config.exp127-source-first-workflow-fast-panel.yaml` | `prompt.role_directive: standard → source_first_v1` |

The treatment has no decision cards, law/reference context, product facts, item
grouping, full split, or output change.

## Required rendered-input review

The treatment messages were exported without an API call under
`outputs/prompt-audit-exp127/` before any paid execution:

| Record | Input type | Review focus |
|---|---|---|
| `PPS-DEV-077` | short, one complete announcement | Does the workflow add only a reading order? |
| `PPS-DEV-01` | announcement truncated at 4,000 characters with two omitted attachments | Does it avoid claiming omitted documents were read? |
| `PPS-DEV-123` | long announcement with two omitted proposals | Does it avoid inventing attachment facts? |

Review completed before the network call: all three rendered files contain the
same four-line workflow immediately before the unchanged item list. `PPS-DEV-01`
and `PPS-DEV-123` retain their existing `[절단]` and `[미수록 문서]` markers;
the directive never says these omitted documents were read. `PPS-DEV-077`
contains its complete single announcement. Against the exact control, the
message delta is only the directive (246 Korean characters for `PPS-DEV-01`).
The workflow adds no legal condition or output requirement and preserves the
baseline's existing “uncertain → 0” policy.

## Gates and evaluation

1. `scripts/preflight_experiment.py` must report only `prompt.role_directive`.
2. Mock run must complete all fast-panel notices with unchanged V/E schema and
   no parse/evidence regression.
3. The paid run uses the fixed `dev_fast_panel_v1` cohort and OpenRouter Gemma.
4. Report macro positive-F1 *and* each changed item’s TP/FP/FN/evidence
   validity/runtime. A fast-panel gain is only a candidate signal; no canonical
   or submission policy changes without a fresh dev-200 confirmation.

## Stop condition

If the treatment does not improve recall without a material precision collapse,
do not rewrite this directive repeatedly. Return to the input audit and choose
another independently testable prompt stage.

## Fast-panel result and confirmation decision

The fast-panel treatment completed 20/20 with no parse-error record in 48.1
seconds and Macro positive-F1 `0.208369`, compared with the fresh EXP125A
control `0.171958`. The treatment recovered one TP each in v2 and v14, but
lost v17's only TP and introduced false positives in v13, v17, and v21. Its
gain is therefore a directional signal, not a dev-200 promotion.

The next and only confirmation for this exact directive is a paired, fresh
control/treatment run on label-blind `dev_prompt_holdout_v1`:
`EXP128A` versus `EXP128B`. Both retain the exact organizer V/E contract;
EXP128B changes only `prompt.role_directive`. If both cohorts do not show
positive-recall preservation and a material macro gain, the directive will be
closed without wording variants or dev-200 execution.
