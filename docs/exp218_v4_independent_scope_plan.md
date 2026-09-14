# EXP218 — v4 independent specific-performance scope

## Problem statement

The current `decision_cards_v10_v6_v7_scope.json` makes “고시금액 이상” a
mandatory v4 prerequisite. This is not merely a missing numeric operand. The
organizer-provided government contract execution standard states two separate
tests:

- article 5(1): below-notice-amount manufacturing/service contracts must not be
  restricted by performance at all;
- article 5(4)(2)-(3): a tender must not exclude equivalent performance by a
  narrowly named performance type or accept only performance ordered by named
  institution classes.

The second prohibition has no notice-amount prerequisite. The dev labels are
consistent with that source structure: four of the six v4-positive dev200
notices have `입찰추정가격 < 230,000,000`, and three notices are simultaneously
positive for v2 and v4. The present card therefore turns one legal dimension
into a false exclusion gate for another.

This is an organizer-source scope correction, not a notice-ID rule. The dev
labels are used only to measure the observed consequence after the conflict is
identified in the organizer law source.

## Hypothesis

Removing the amount gate from v4 and stating the actual relation—participant
qualification performance + named ordering institution/narrow performance type
+ no concrete necessity—will recover v4 positives without changing source
admission, model capacity, other item cards, evidence policy, or final label
ownership.

## Controlled experiment

- candidate: EXP218
- `experiment.base_config`:
  `configs/config.exp205-relation-checklist-after-source-fast-panel-c4.yaml`
- `experiment.allowed_policy_changes`:
  `prompt.decision_cards_path`
- the new card artifact differs from the base artifact only at v4
- unchanged: one-stage full-source admission, relation checklist, V+E schema,
  metadata and conditional exact-product facts, all other cards, evidence
  validation, frozen EXP123 postprocess, provider parameters, and merge policy
- no Python v4 label rule or override

## Paid gates

Before the provider call:

1. Generate and byte-diff the new card artifact; assert v4 is the only changed
   card.
2. Run `scripts/preflight_experiment.py` and require only the declared card-path
   change.
3. Audit exact tokenizer admission and source provenance on dev200; require all
   organizer-provided documents admitted across the generated packs and no
   over-budget message.
4. Export and read exact rendered messages for a short complete notice, a
   notice with attachments, and an overflow notice.
5. Audit the semantic-input contract for all 24 items in each rendered example;
   v4 must contain the revised condition, metadata, and actual source.
6. Run the exact config with `--mock`; validate 49 columns, IDs, parse recovery,
   evidence, and isolated output path.

## Promotion rule

- Run only `configs/dev_fast_panel_v1.json` first.
- Continue to the versioned independent holdout20 only if v4 TP/F1 improves and
  total macro-F1/TP do not materially regress.
- Continue to dev200 only if the holdout direction also agrees.
- A failure ends this card revision; do not tune wording to individual dev
  examples.

## Follow-up, kept separate

The rendered-input audit also found that v2/v5-v7/v14-v16 refer to
“고시금액” while the numeric threshold is absent from the prompt. That is a
separate semantic-input problem. It must be resolved through an institution-
and-work-type threshold provenance audit and a separate single-policy-change
experiment; it is deliberately not mixed into EXP218.

## Pre-provider gate — 2026-09-14

- Generated `decision_cards_v11_v4_scope.json`; structural comparison against
  `decision_cards_v10_v6_v7_scope.json` reports exactly one changed card: v4.
- Preflight reports exactly the declared
  `prompt.decision_cards_path` difference.
- Exact tokenizer admission on the fixed fast20 is 24 messages
  (`17x1 + 2x2 + 1x3`), with a maximum admitted prompt of 30,268 tokens.
- Full dev200 complete-input audit covers 374/374 source documents in 222
  messages (`184x1 + 13x2 + 3x3`): source omission 0, metadata omission 0,
  missing cards 0, organizer-semantics omission 0, and over-budget pack 0.
- Exact rendered messages were read at:
  - `outputs/exp218-preflight/semantic-PPS-DEV-062/rendered_inputs/` (short,
    complete, single document),
  - `outputs/exp218-preflight/semantic-PPS-DEV-194/rendered_inputs/`
    (announcement + specification attachment),
  - `outputs/exp218-preflight/semantic-PPS-DEV-169/rendered_inputs/`
    (overflow announcement + RFP).
- Human review conclusion: every message retains cards, readable metadata,
  organizer anonymization semantics, conditional product facts, admitted
  original source, and the final relation checklist. The revised v4 text is
  present and explicitly states that v4 can co-occur with v2/v3. No law text is
  injected. The item-table display name still contains “고시금액 이상”; the
  revised card immediately resolves that known organizer-title/source conflict
  rather than silently changing the organizer item name.
- The three rendered examples each pass the 24/24 semantic-input contract
  audit. Exact mock completes 20/20 with 49 columns and no execution error.
- Full tests: 209 passed.

The paid fast20 run is therefore approved. It remains a one-card diagnostic;
no holdout or dev200 claim is made until the promotion gates pass.

## Fast20 result

- EXP205 base: `.325000`
- EXP218: `.309722`, delta `-.015278`
- v4: TP/FP/FN `0/0/3 -> 2/0/1`, F1 `0 -> .800000`
- v4 changed cells: two corrected, zero regressed
- off-target changed cells: three corrected, six regressed
- 24 source-pack calls, 53.8 seconds wall time, prompt/completion tokens
  `377,107/15,474`, parse error 0, validation warnings 5
- paired artifact: `outputs/exp218-preflight/paired_exp205_exp218.json`

The v4 source correction produced the intended item-level effect with no v4
false positive, but changing the shared 24-item generation also moved unrelated
v8/v12/v17/v19/v23 decisions. The net macro gate therefore fails and EXP218 is
not promoted to holdout in this shared-output form.

The result supports one next diagnostic: isolate only v4 as a model-owned
specialist output and keep the other 23 items under the unchanged base card.
That experiment must declare the additional group/call topology and must not
be described as the previously rejected all-item grouping strategy.
