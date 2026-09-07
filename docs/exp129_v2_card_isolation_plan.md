# EXP129 — v2 card isolation diagnostic

## Question

`v2` positives are almost entirely observable in the current 4,000-character
input (six of seven have gold evidence in the rendered context).  Does the
existing `decision_cards_v6` v2 rule help Gemma apply that visible boundary,
when it is the only requested judgment?

This is deliberately not a new card-writing exercise and not a proposed
submission policy.  It separates one pre-existing card from the 24-item output
burden before any further prompt engineering.

## Controlled arms

| Arm | Prompt difference |
|---|---|
| EXP129C | exact organizer 24-item baseline; measures output-scope effect |
| EXP129A | official item-table name and note only |
| EXP129B | exactly EXP129A plus `decision_cards_v6`'s existing v2 text |

All arms use the same 4,000-character single context, human-readable official
metadata, V/E JSON contract, Gemma model, decoding, retries, and 14 notice
IDs. EXP129C retains the exact 24-item organizer renderer. The new
`official_baseline_subset_v1` profile is a diagnostic renderer only: it keeps
the organizer wording and user-message format, replacing only the necessarily
different output scope from 24 items to `v2`.

## Frozen cohort

`configs/dev_v2_card_probe_v1.json` contains all seven available dev v2
positives and seven label-blind hash-selected negatives.  This makes recall
loss visible but is not an independent evaluation set.  No result from this
cohort can promote a submission policy.

## Required input review before provider calls

For all three configs, generate and read these exact files:

- `PPS-DEV-02`: short, complete notice;
- `PPS-DEV-042`: v2 positive whose announcement itself exceeds the 4,000-character
  context;
- `PPS-DEV-053`: visible high-value explicit participant-qualification case.
- `PPS-DEV-01`: attachment-bearing overflow notice; verify the explicit
  `[미수록 문서] 과업지시서 1건, 제안요청서 1건` marker.  It is an input-audit
  fixture, not a scored member of this v2 cohort.

Verify that all arms have byte-identical user messages. Verify that EXP129A/B
have no inactive v item and that their only system diff is the v2 card block;
verify EXP129C is the exact 24-item organizer baseline. No arm may inject raw
law text, product-code status, or a hidden rule. Then run preflight, mock, and
exact tokenizer admission. Record the paths and conclusion in the result.

## Evaluation and stop rule

Read only the v2 row of `per_item_metrics.csv`; aggregate macro F1 is invalid
because inactive items are intentional zero placeholders.  Compare TP/FP/FN,
parse errors, evidence validity, token counts, and changed records.  Stop after
this pair unless the card improves v2 recall without a compensating FP increase;
even then require an independent cohort before any 24-item/dev-200 candidate.
