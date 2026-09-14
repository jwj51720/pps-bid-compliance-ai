# EXP223 — v7-only specialist diagnostic

## Diagnosis and hypothesis

EXP208 dev200 predicts no v7 positives: TP/FP/FN `0/0/7`. All seven gold v7
evidence spans are present in the exact rendered source messages, and none is a
multi-pack or parse-error case. This rules out source omission as the proximate
failure and makes v7 a clean test of item-level attention dilution.

The hypothesis is that Gemma can recover the already-visible relationship when
it receives only the v7 card, required readable metadata, organizer semantics,
and all admitted original documents, instead of allocating one response across
24 heterogeneous decisions. This tests minimal item grouping; it does not
change the v7 truth condition or add a rule.

## Controlled policy

- base config:
  `configs/config.exp205-relation-checklist-after-source-fast-panel-c4.yaml`
- intended config:
  `configs/config.exp223-v7-only-specialist-fast-panel-c4.yaml`
- allowed changes: `prompt.active_items`, `prompt.profile`, `prompt.mode`
- active output is v7/e7 only;
- `complete_fact_subset_v1` retains the full source/input families with a
  one-item output schema;
- mode is `baseline`: the broad relation checklist is removed so instructions
  for inactive items cannot affect the v7-only generation. The v7 card itself
  already specifies amount regime, participation-area role, adjacency relation,
  and allowed-contract exception;
- card version, metadata renderer, source admission, organizer semantics,
  provider/model parameters, evidence validation, and Python postprocessing are
  unchanged;
- compose only model-owned v7/e7 onto the frozen EXP205 fast result. Python
  cannot infer or override the label.

## Gates and sequence

Before the paid fast call, require declared-diff preflight, exact token/source
audit, actual short/attachment/largest rendered review, active-v semantic
contract, exact mock, 49-column validation, and no non-v7 changed merge cells.

Use only `configs/dev_fast_panel_v1.json`. Advance the unchanged policy to the
independent holdout only if v7 F1 and merged macro-F1 improve without parse or
input failures. Advance to dev200 only if the holdout direction agrees. Do not
tune wording or introduce a numeric threshold from dev outcomes; a threshold
card correction, if organizer-source verification requires one, is a separate
experiment.

Record calls, runtime, tokens, parse errors, evidence validity, per-item counts,
paired changes, and rendered review in isolated outputs.

## Fast20 result

- preflight found exactly the three declared subset-serialization changes;
- exact fast admission was 20/20 one-pass; dev200 audit retained 374/374 source
  documents with zero metadata/card/organizer-semantics omissions and 200/200
  one-pass topology;
- rendered short, attachment, and largest messages were read and the active v7
  semantic contract passed 1/1 on all three; exact mock passed;
- provider call: 20 calls, 21.3 seconds, parse error 0;
- EXP205 base `.325000` -> merged EXP223 `.352778`, delta `+.027778`;
- v7 TP/FP/FN `0/0/2 -> 1/0/1`, F1 `0 -> .666667`;
- changed non-v7 cells: 0; v7 positive evidence validity: 1/1.

The fast gate passes. EXP224 repeats the identical specialist policy on the
independent holdout and composes it only with the already-paid EXP206 result.

## Independent holdout20 result

- provider call: 20 calls, 21.0 seconds, parse error 0;
- EXP206 base and merged EXP224 both `.208333`;
- v7 TP/FP/FN remained `0/0/1`; changed cells: 0.

The independent direction does not agree with fast, so this path stops before
dev200. Inspection of the sole holdout positive, PPS-DEV-050, shows that neither
document nor amount facts were omitted: the source explicitly says the
estimated price is below the notice threshold and restricts participants to
Jeollanam-do or Gyeongsangnam-do. The unresolved operand is the relation between
the anonymized demand-region token and the two named allowed regions. Loosening
the card to treat any multiple-region list as v7 would contradict its official
adjacent-expansion condition, so no post-hoc card edit is made from this case.
