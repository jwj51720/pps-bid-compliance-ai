# EXP222 — v4 specialist role/fact decomposition plan

## Decision problem

The unchanged v4-only specialist improved all three cohorts and recovered every
dev200 v4 positive, but predicted 26 false positives. The error is not missing
source input: the dev200 specialist admitted all 374/374 documents, rendered the
corrected card and readable metadata, and used one complete-source message per
notice. The remaining problem is semantic role confusion inside a long notice.

Observed false-positive families are:

1. a performance phrase belongs to proposal evaluation or scoring, not
   participant qualification;
2. a named institution is the issuer of a proof document, not the client that
   ordered the past performance;
3. the restriction concerns an A/S center, facility, organization, product, or
   technical compatibility rather than past completed contract performance;
4. past performance is a real qualification, but broadly similar performance
   or private/public clients are accepted rather than only a named ordering
   institution or narrowly named performance class.

These distinctions are direct operands of the organizer-law v4 truth condition
and cannot be represented reliably by the old fields `특정발주기관한정` and
`특정실적종류한정` alone. They justify the smallest possible new schema for v4
only; no multi-item framework is inferred from this diagnosis.

## Hypothesis

Before producing model-owned v4/e4, require Gemma to expose a compact
source-grounded review with the following fields:

- `실적요구원문`: unchanged source substring for the most relevant clause;
- `조항역할`: participant qualification, proposal/evaluation score,
  proof-document administration, facility/organization/product/technical
  condition, other, or unclear;
- `과거계약실적요구`: yes/no/unclear;
- `발주기관범위`: only a specified ordering institution, public/private or all
  institutions accepted, no institution restriction, or unclear;
- `실적종류범위`: narrowly named class excluding equivalents, broad/substantially
  similar accepted, general same-purpose class, no performance restriction, or
  unclear;
- `유사동등실적인정`: yes/no/unclear;
- `구체적필요사유`: yes/no/unclear;
- `카드대조`: 1-condition, 0-condition, or indeterminate.

The prompt explicitly distinguishes ordering client from certificate issuer and
qualification from evaluation/scoring. The review is an observable reasoning
record, not a Python label rule. Gemma must reread the corrected v4 card,
metadata, and all admitted original documents before its final v4/e4. Python
may validate the excerpt as a source substring and serialize the model output;
it must not derive or override v4 from review fields.

## Controlled experiment

- specialist base config:
  `configs/config.exp219-v4-only-scope-fast-panel-c4.yaml`
- intended config:
  `configs/config.exp222-v4-specialist-fact-first-fast-panel-c4.yaml`
- `experiment.allowed_policy_changes`: `[prompt.mode]`
- active item remains exactly `[v4]`
- corrected card remains `decision_cards_v11_v4_scope.json`
- profile remains `complete_fact_subset_v1`
- source admission, metadata, organizer semantics, model/provider parameters,
  output V/E contract, merge target, and evidence validation remain unchanged
- counterfactual merge base remains the already-paid EXP205 fast output

This is a prompt/schema structure test. It does not change cards, documents,
merge semantics, provider parameters, or Python labels.

## Pre-provider gates

Before any paid call:

1. preflight must report only `prompt.mode`;
2. exact tokenizer admission must retain complete source coverage and report
   zero over-budget messages;
3. exact short, attachment, and largest/overflow rendered messages must be
   exported and read by a human;
4. the active-v semantic-input contract must trace v4 applicability, 1 and
   material 0/exception conditions, required source types, and metadata into
   exact rendered spans;
5. schema/parser tests must prove the review cannot silently become a label
   override and excerpt validation is source-only;
6. exact mock and specialist merge must produce a valid 49-column output with
   zero changed non-v4 cells.

## Evaluation sequence and stop rules

Run only `configs/dev_fast_panel_v1.json` first. Compare both v4 precision,
recall, F1 and the merged macro-F1 against EXP219/EXP205. The candidate passes
fast only if it retains useful recall while materially reducing v4 false
positives or improving v4 F1. If it passes, repeat the identical policy on
`configs/dev_prompt_holdout_v1.json`; only a directionally consistent holdout
result may advance to dev200.

Record config, metrics, per-item TP/FP/FN, parse errors, evidence validity, call
count, runtime, rendered-message review, and paired changed-cell audits in
isolated output paths. A failure is retained as a result and is not repaired by
post-hoc phrase lists.

## Runtime interpretation

This remains one Gemma call per admitted v4-only notice context. It changes the
response schema and reasoning order but does not add a verifier pass. Therefore
its immediate purpose is local precision, while preserving the short response
and complete-input topology that could later replace or accompany a broader
one-stage decision within the two-hour submission limit.

## Pre-provider validation — 2026-09-14

- preflight found only the declared `prompt.mode` difference;
- fast exact admission was 20/20 one-pass, with a maximum of 29,994 prompt
  tokens before generation;
- dev200 complete-input audit retained 374/374 documents, with zero source,
  metadata, card, or organizer-semantics omissions and zero over-budget packs;
  the larger fixed prompt changed the projected distribution to 199 one-pass
  notices and one two-pass notice;
- exact rendered short `PPS-DEV-062`, attachment `PPS-DEV-194`, and largest
  `PPS-DEV-197` messages were read. The complete card/metadata/source precedes
  the final role checklist in each;
- the active v4 semantic contract passed 1/1 on all three messages;
- exact mock and merge validation passed, and the regression suite was
  211 passed.

## Fast20 result and stop decision

- provider call: 20 calls, 24.0 seconds, prompt/completion tokens
  `258,156/5,506`, parse error 0
- EXP205 counterfactual base: `.325000`
- merged EXP222: `.345833`
- EXP219 corrected-card specialist: `.352778`
- v4 TP/FP/FN: EXP219 `3/3/0` versus EXP222 `3/6/0`; F1
  `.666667 -> .500000`
- changed non-v4 label cells: 0

The candidate fails the fast gate and does not advance to holdout. The review
did identify administrative and evaluation roles in several notices, but its
fields were not logically binding: for example, Gemma emitted
`조항역할=제안평가_배점` or `민간_공공_또는_모든기관인정` and still emitted
`카드대조=1조건충족` and final v4=1. This proves that a larger same-response
reasoning schema does not by itself enforce conjunction consistency. Do not
repair this run with Python field-to-label rules or phrase lists. A future v4
attempt would need an independent model verification topology or a materially
simpler decision decomposition, not more fields in the same response.
