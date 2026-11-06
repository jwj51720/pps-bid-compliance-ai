# EXP314–316: v18 whole-notice absence card audit

Status: fast20 and independent holdout completed; treatment rejected, canonical config unchanged.

## Hypothesis and separation

The incumbent v18 card names a required small-enterprise restriction and an unspecified
priority-procurement exception, but does not operationalize the exception or distinguish
qualification restrictions from incidental certificate references. Compare one-item attention
first, then a card-only source-correct treatment. This is not another full-product-catalog,
relation-proof schema, or repeated V-only consensus experiment.

- EXP314 base: `configs/config.exp205-relation-checklist-after-source-fast-panel-c4.yaml`.
  Allowed changes: `prompt.active_items`, `prompt.profile`, `prompt.mode` only.
  Active item v18; `complete_fact_subset_v1`, ordinary `baseline`, V/E unchanged.
- EXP315 base: EXP314. Allowed change: `prompt.decision_cards_path` only.
  New card changes v18 only. Preserve product renderer, all-source coverage, exact tokenizer,
  metadata semantics, schema, merge, provider parameters and evidence contract.
- EXP316 base: EXP315. Allowed change: `prompt.output_mode` only, V-only.
  v18 is already an evidence-exempt absence item; no evidence-recovery call is necessary.

All arms retain actual complete admitted source packs and cards/needed metadata/product facts.
Python does not determine certificate roles, exceptions, product applicability or legal labels.
The existing per-pass AND remains frozen; audit pass-level labels separately rather than
silently altering it. Fast uses only the fixed `dev_fast_panel_v1`.

## Source-first card constraints

Organizer SME decree article 2-2(1)(1) defines the below-KRW100m small-enterprise/small-business
priority procurement premise; article 2-3 defines exceptions and publication of their reasons.
Preserve actual purchase-object applicability rather than converting absent codes into a
general-product classification. A mere mention in evaluation, generic forms, or incidental
background does not itself establish a qualification restriction. Conversely, a mandatory
qualification-verification document can be substantive; do not hard-code that a certificate
outside a heading is irrelevant. Unresolved source contradictions are not automatic positives.

The precise proposed card and every legal condition must be source-traced before generation.
Do not use a particular dev ID or gold label in the card. The treatment must not define
presence so narrowly that it is designed to recover PPS-DEV-044.

## Pre-run gates and isolated artifacts

1. Build/version card; prove only v18 differs from incumbent.
2. Run `scripts/preflight_experiment.py` for each config, with no undeclared differences.
3. Exact tokenizer admission and full source/provenance report; zero source omission.
4. Export/read full rendered short-complete, attachment and overflow system/user requests.
5. Separate semantic-input review: all v18 applicability, 1, 0, exception, metadata and CSV
   conditions must be traced to organizer source and rendered spans. All other v items are
   inactive, not claimed as audited by this subset experiment.
6. Exact mock with output schema, blank e18 and unchanged pass merge checks.
7. Outputs `outputs/exp-314-...`, `exp-315-...`, `exp-316-...`; preserve config, per-item
   TP/FP/FN, parse errors, evidence validation, prompt/completion tokens, calls, runtime,
   pass-level outputs, rendered review and product applicability stratification.
8. Final paid-run readiness check: all hypothesis components actually selected.

## Promotion and source ambiguity

Fast v18 positive PPS-DEV-039 and holdout positive PPS-DEV-044 both have unknown exact-product
facts. Thus card text alone might not solve applicability. Existing control must establish
whether item isolation changes labels. No fast gain means no holdout/dev200 escalation.
Fast gain must survive independent fixed holdout, including precision and malformed-output
rate, before dev200. V-only is preferred only if labels improve, not because output is short.

Offline review of the full PPS-DEV-044 packet (2,040 lines, D0 announcement plus D1 proposal
request) is complete. Qualification headings do not state a small-enterprise restriction;
announcement submission documents nevertheless require a small-enterprise/small-business
certificate. The attachment qualification section refers back to the announcement. This
creates a substantive presence-role ambiguity, not a proven missing input or safely resolved
gold conflict. Do not remove that source span or invent an exemption to match its gold.
This uncertainty must remain visible in interpreting holdout; one ambiguous positive cannot
by itself prove generalized recall improvement.

Reference: `docs/decision_card_full_audit_20260915.md`, source packets and report under
`outputs/product-item-source-audit-20260915/`. No paid calls performed for this plan yet.

## Implementation checkpoint

Implemented version `v24_v18_absence` in `scripts/build_decision_cards.py` and generated
`data/derived/decision_cards_v24_v18_absence.json` from the restored organizer item table.
Three configs are named `config.exp314-v18-only-existing-card-ve-fast-panel-c4.yaml`,
`config.exp315-v18-absence-card-ve-fast-panel-c4.yaml`, and
`config.exp316-v18-absence-card-vonly-fast-panel-c4.yaml` under `configs/`.
All three preflight commands passed with exactly their declared changes. Decision-card
tests: 14 passed, including only-v18 difference and preservation of certificate roles,
amount, exception operands, whole-source scope and e18 contract.

EXP315 automatic semantic audit produced PASS under `outputs/exp315-preflight/`, with
rendered files for PPS-DEV-01 and PPS-DEV-123. This is not paid-run approval: its inherited
contract/ledger does not independently prove every newly expanded exception. Human review
of the exact short/attachment/overflow rendered requests, exact tokenizer/source coverage,
source-span mapping for the new card and mock remain outstanding. No paid call yet.

## Exact admission and mock checkpoint

- EXP315 fast20: 20 calls, 35 source documents, zero omitted source spans, no overflow;
  prompt budget 30,268 tokens. `outputs/exp315-preflight/admission.json`.
- Label-blind dev200 profile: 200 calls, 374 source documents, zero omissions, no overflow;
  largest PPS-DEV-11 is 30,162 tokens, only 106 tokens below budget.
  `outputs/exp315-preflight/admission-all.json`. This is admission profiling, not dev200 inference.
- PPS-DEV-169 is 29,158 tokens and fits one pass in this subset policy. Do not call it an
  overflow fixture. There is no natural dev200 overflow for this arm; any forced overflow
  regression must be marked synthetic and must not alter the paid experiment policy.
- Exported exact-tokenizer requests under `outputs/exp315-preflight/prompt_review/`:
  PPS-DEV-062 (short), PPS-DEV-194 (announcement/specification), PPS-DEV-169 (long), and
  PPS-DEV-123. Short request read completely. Attachment request review was interrupted by
  tool-output truncation and its missing span was inspected separately, but full long-request
  review remains outstanding. Do not claim all rendered-review gates complete.
- All three arms ran the configured 20-ID mock, preserved under their `-mock` directories;
  CSV validation passed with no errors/warnings. Mock metrics are not quality evidence.
- Full test suite: 260 passed in 16.99s. `git diff --check` passed.

Paid execution still requires the source-span mapping for every expanded exception and exact
rendered human review for both V/E and V-only. Automatic semantic PASS alone is insufficient.

Source-concordance table is now `docs/exp315_v18_source_contract.md`. Its review found the
initial draft overcompressed school/counseling/specimen-test exception scopes; the card now
preserves extracurricular school activities, policy/civic-policy advisory purposes and
health-insurance-benefit specimen testing. No paid calls preceded this correction. Previous
admission/mock/render artifacts above validate the pre-correction draft, not the final card.
Regenerate final checks in fresh `outputs/exp315-preflight-final/` (automatic semantic audit
there passed, still not a full human review). Decision-card tests after correction: 14 passed.

Final-card EXP315 fast admission was regenerated: 20 records/calls, 35 source documents,
zero omitted source spans and no overflow (`outputs/exp315-preflight-final/admission.json`).
Exact-tokenizer short/attachment/long requests regenerated under its `prompt_review/`.
Long human review remains in progress; tool-output truncation is not counted as completed
reading. Final draft has not been paid-run approved.

During rendered review PPS-DEV-123 was found to contain D1 English unofficial translation
plus D2 Korean proposal request. Rechecked the organizer ZIP directly: gzip SHA256
`7dedfaaf02cc9ea15f4178ed60fc1a4fedf94c37e948a9375edb6557328c6a2b` matches local exactly,
and all three document starts match. Therefore this is organizer input, not local translation
injection. Keep both documents in this experiment; deleting translations is a separate
source-scope ablation and is not authorized by these allowed changes. Duplication/translation
is an observed context-length risk, not yet an experimentally established performance cause.

## Final fast20 readiness

Final EXP314/315/316 admission: each 20 calls, 35 source documents, zero omissions and zero
natural overflow. Separate reports are in `outputs/exp{314,315,316}-preflight-final/admission.json`.
All three exact mock validation reports passed. EXP315/316 mock regenerated after final wording.
Three short/attachment/long fixtures (062/194/123) exported under each arm's `prompt_review/`;
user messages byte-identical across all arms. System differences reviewed separately: existing
card versus source-concordant v18 card, then output-only V-only. Full source text reviewed in
EXP315, including previously truncated 123/194 ranges; no raw-law/reference injection or source exclusion.
Final semantic source/rendered mapping is `docs/exp315_v18_source_contract.md`.

No natural overflow exists: diagnostic-only config `config.exp315-v18-synthetic-overflow-review.yaml`
forces 6,000-token admission on attachment fixture194. Exact rendered messages are under
`outputs/exp315-preflight-final/synthetic-overflow/`; six contexts were inspected (repeated
system/metadata/announcement anchor plus all changed target fragments). Exact tokens
`6000,6000,5054,6000,6000,5662`, source coverage gaps `[]`. This is not a paid quality arm.
An initial 2,500-token budget on062 failed admission with `document header cannot fit token budget`;
that extreme-budget diagnostic was not executed against a provider or used as performance evidence.

Immediately before paid execution all three preflight commands passed their declared differences;
card/product assets selected, active v18 only, no undeclared provider/schema/merge changes,
fixed fast panel and isolated paid output dirs. EXP314 intentionally retains the known-deficient
historical card as a control; it is not a new source-correct candidate.

## Fast results and conditional independent comparison

EXP315 completed: v18 TP/FP/FN `1/11/0`, F1 `.153846`, precision `.083333`.
EXP316 completed: `0/4/1`, F1 `0`; no V-only promotion. Each20 successful model passes,
parse errors0, e18 all blank, CSV validation passed, v18 postprocess changes0.
Remote runtime21.238/20.680s, prompt tokens260441/258921, completion548/180.
These are not vLLM runtime estimates. Overall subset macro includes inactive-item/frozen-rule
behavior and must not be reported as a full24 strategy score.
`scripts/analyze_exp314_v18.py` preserves an isolated comparison summary.

EXP314 has19 completed checkpoints and a live final request069; its observed v18 positive
is not recovered among those19. Do not restart or call this arm complete while transport waits.
If terminal control confirms fast gain, compare EXP317 existing-card V/E and EXP318
corrected-card V/E on independent fixed holdout with no policy changes. Versioned configs and
isolated paths selected; exact admission/mock/preflight required before calls. Same rendered
fixtures/source contract apply because only evaluation cohort/output paths change. V-only
holdout is unwarranted after zero fast TP. High fast FP means recall-only gain is insufficient:
holdout precision and the known044 presence-role ambiguity remain explicit promotion gates.

EXP314 terminal: `0/4/1`, F1 0, parse error1, runtime122.097s.069 emitted malformed
JSON followed by whitespace, finish_reason length, reported completion8192 despite configured
max_tokens2500. Adapter source passes configured max_tokens unchanged; provider-reported usage
anomaly is recorded, not attributed to vLLM.069 is a gold-negative and recovered0, so this
malformed record does not explain the fast positive039 difference. Excluding069 for diagnostic
comparison does not rescue precision: EXP315 still has10 FP and control3 FP among remaining19.
Do not rerun/select a cleaner control or interpret122s as a card speed effect.

EXP317/318 holdout readiness: preflight no effective policy differences; each20calls/41docs,
source omissions0, exact admission no overflow. Configured mock CSV validation passed both.
Same complete rendered inputs/criteria reviewed above, only cohort/output paths differ.
All hypothesis components selected. Execute independent comparison to test the numerical
fast F1 gain, not to promote the weak-precision fast candidate automatically.

## Terminal independent result and decision

| arm | cohort | TP/FP/FN | precision | recall | v18 F1 | parse errors | runtime sec |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EXP314 existing V/E | fast20 | 0/4/1 | 0 | 0 | 0 | 1 | 122.097 |
| EXP315 corrected V/E | fast20 | 1/11/0 | .083333 | 1 | .153846 | 0 | 21.238 |
| EXP316 corrected V-only | fast20 | 0/4/1 | 0 | 0 | 0 | 0 | 20.680 |
| EXP317 existing V/E | holdout20 | 1/4/0 | .2 | 1 | .333333 | 0 | 21.268 |
| EXP318 corrected V/E | holdout20 | 1/11/0 | .083333 | 1 | .153846 | 0 | 24.841 |

All100 records retain admitted originals and successful transport;314/069 is not a successful
structured judgment. All CSV validation passes, e18 blank, target postprocess label changes0.
Holdout each20passes/41docs, omissions0, prompt/completion247503/563 and256303/542.
Full test suite260passed17.22s. Each run preserves config/card/product copies, final inputs,
predictions/raw/pass outputs, metrics/per-item TP/FP/FN, errors/validation/signatures/usage/runtime.
Isolated comparison `outputs/exp314-exp316-v18-comparison/summary.json`; reproduce runner commands
above and `.venv/bin/python scripts/analyze_exp314_v18.py`.

Reject corrected-card promotion; stop before dev200. Holdout recall unchanged, FP4→11.
V-only has no fast label gain. Holdout044 is positive in both arms; certificate-role ambiguity
remains, not proof of corrected reading. Fast194 actual qualification requires small enterprise/
small business and its certificate, yet315 raw label1 (316 label0). Fast032 admitted metadata
has121180000 but both corrected outputs say1 for a <100m item. All evaluated records are onepass,
and target raw labels are unchanged by Python: these are not OR/AND merge leaks.
Card source fidelity improved but model quality did not generalize. No more exception wording,
identical-input repetition or Python legal overrides for this family.

314/069 transport anomaly is unresolved: adapter passes max_tokens2500 but reported completion8192,
whitespace loop and length termination. Audit separately before remote runtime claims; no provider
parameter change was mixed into this completed card/output ablation.
