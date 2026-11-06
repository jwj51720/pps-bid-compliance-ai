# EXP219 — v4-only specialist replacement diagnostic

## Why this follows EXP218

EXP218 corrected the organizer-law scope conflict and changed v4 fast20 from
TP/FP/FN `0/0/3` to `2/0/1`. Its total macro score nevertheless fell because
the shared 24-item generation also changed unrelated outputs. EXP219 measures
the same v4 policy without that cross-item generation variance.

This is intentionally a diagnostic probe, not a complete submission strategy.
It reuses the already paid EXP205 result for the other 23 items and replaces
only v4/e4 with a new Gemma v4-only result. Python copies model-owned cells; it
does not infer a violation, inspect phrases, or override a model label.

## Controlled policy

- specialist `base_config`:
  `configs/config.exp205-relation-checklist-after-source-fast-panel-c4.yaml`
- allowed specialist changes:
  `prompt.active_items`, `prompt.decision_cards_path`, `prompt.profile`,
  `prompt.mode`
- `complete_fact_subset_v1` is the required subset serialization of the base
  `complete_fact_v1` profile; it retains the same input families and V/E
  semantics while permitting a one-item schema
- mode is `baseline` because EXP205's relation checklist contains no v4 entry;
  retaining it in a v4-only message would add instructions for eight inactive
  items without preserving any v4 condition
- active output: v4/e4 only
- v4 card: `decision_cards_v11_v4_scope.json`
- all source documents, readable metadata, organizer semantics, token
  admission, evidence validation, and model parameters remain inherited from
  EXP205. Product facts are not rendered because v4 has no product-code truth
  condition; the relation checklist is removed because it has no v4 entry
- counterfactual base output: `outputs/exp-205-relation-checklist-after-source-fast-panel-c4`
- merge contract: copy specialist v4/e4 only; retain every other base cell

## Gates

Before the paid specialist call, require:

1. preflight reports only the four declared changes;
2. exact admission and complete-source audits show zero source/fact omission;
3. exact short/attachment/overflow rendered messages contain the corrected v4
   condition and all required source inputs;
4. v4 semantic contract passes and exact mock output validates;
5. the replacement utility asserts identical ordered IDs and changes only
   v4/e4.

Fast success requires v4 F1 and counterfactual total macro-F1 to improve over
EXP205 without any changed non-v4 label. Only then create a separately versioned
holdout specialist config against EXP206. A holdout failure stops the path.

## Runtime interpretation

The specialist adds one complete-source topology beside the base topology:
fast20 expects 20 additional source-pack calls. A prospective dev200/full-test
implementation would roughly double the one-stage context-pass count, so a
quality win is not automatically submission-feasible. Runtime engineering is
deferred until after independent quality confirmation.

## Pre-provider gate — 2026-09-14

- Preflight reports exactly the four declared, jointly required differences:
  one active item, the corrected v4 card, subset serialization, and removal of
  the irrelevant non-v4 relation checklist.
- Exact fast20 admission is 20/20 single-pass calls. Reducing the fixed
  24-card/output overhead lets every fast record fit with its complete source;
  the largest prompt is 29,208 tokens under the 30,268-token budget.
- Full dev200 complete-input audit is also 200/200 single-pass: 374/374 source
  documents, source omission 0, metadata omission 0, missing active card 0,
  organizer-semantics omission 0, over-budget pack 0.
- Exact rendered messages were read at `PPS-DEV-062` (short), `PPS-DEV-194`
  (attachment), and `PPS-DEV-169` (formerly overflow). They contain the
  corrected v4 test, readable metadata, and every original source document;
  the inactive-item relation checklist is absent.
- Each review passes the one active item's semantic-input contract. Exact mock
  completes 20/20 and the replacement utility validates identical ordered IDs,
  49 columns, and zero changed non-v4 cells.
- Full tests remain 209 passed.

The v4-only fast provider call is approved.

## Fast20 result

- specialist call: 20 calls, 21.1 seconds, prompt/completion tokens
  `258,136/1,106`, parse error 0
- EXP205 counterfactual base: `.325000`
- merged EXP219: `.352778`, delta `+.027778`
- v4 TP/FP/FN: `0/0/3 -> 3/3/0`, F1 `0 -> .666667`
- changed non-v4 label cells: 0
- v4 evidence validity: 5/6; one positive has no valid source substring and is
  retained as a validation warning, not silently rewritten

The fast gate passes on recall and total macro-F1. Precision is only .5, so no
wording is tuned from the three fast false positives. EXP220 repeats the exact
specialist policy on `configs/dev_prompt_holdout_v1.json` and composes it only
with the already-paid EXP206 holdout base.

## Independent holdout20 result

- specialist call: 20 calls, 22.8 seconds, parse error 0
- EXP206 base: `.208333`
- merged EXP220: `.229167`, delta `+.020833`
- v4 TP/FP/FN: `0/0/1 -> 1/2/0`, F1 `0 -> .500000`
- changed non-v4 label cells: 0

The direction agrees with fast20 and the sole holdout v4 positive is recovered.
The two false positives quote service-center/facility ownership rather than a
past-performance restriction. This establishes a prospective structural error
class, but the prompt is not tuned after seeing holdout. EXP221 first extends
the unchanged specialist to dev200 to measure its real precision and macro
effect. A later fact-first refinement, if justified, must be a separate
experiment.

## Dev200 result

- specialist call: 200 calls, 201.7 seconds, prompt/completion tokens
  `2,380,996/10,134`, parse error 0
- EXP208 counterfactual base: `.292959`
- merged EXP221: `.306117`, delta `+.013158`
- v4 TP/FP/FN: `0/1/6 -> 6/26/0`, F1 `0 -> .315789`
- changed non-v4 label cells: 0

The item-local path therefore crosses `.3` on dev200 without relying on Python
label inference, while preserving every other EXP208 output. It proves that the
old v4 card scope and shared 24-item generation were both suppressing useful
signal. It does not yet provide adequate precision. Manual error decomposition
shows that the false positives repeatedly confuse four source roles with an
actual participant-qualification performance restriction: proposal-evaluation
scores, proof-document issuer instructions, facility/A/S/product requirements,
and broad performance requirements that accept comparable private or public
clients. EXP222 will test a source-grounded role decomposition before the model
owns the final v4/e4 decision; it will not encode dev IDs or phrases as rules.
