# EXP137 — G02-only decision-card test

## Hypothesis

The EXP135 G02 output partition improved across fast-20, holdout-20, and
dev-200. Its five item names omit material distinctions: low-value local
contract conditions (v6–v8), actual model requirement versus example/equivalent
product (v9), and pre-bid versus contract-stage assurance timing (v19).
`decision_cards_v6` encodes those compact organizer-source conditions without
injecting raw laws, retrieval text, product lookup, labels, or Python rules.

## Exact policy change

EXP137 is based on EXP133. `grouped_run.decision_cards_overrides` is explicit:

- G01 has no card file, preserving EXP133's prompt byte-for-byte;
- G02 alone loads `data/derived/decision_cards_v6.json` and renders only its
  five active cards.

This is deliberately not a root `prompt.decision_cards_path`: rendered review
invalidated EXP136 because that would add all 19 G01 cards too. The override is
an inspectable execution configuration, is included in preflight differences,
and is mirrored by `inspect_grouped_prompt.py` and the runner.

## Mandatory gates

Before a paid call, read exact G01/G02 messages for one complete notice, one
announcement-overflow notice, and one attachment-overflow notice. Confirm:

1. G01 contains no `판정 카드:` text and matches EXP133's G01 message;
2. G02 contains exactly v6, v7, v8, v9, v19 cards, with no inactive card or
   raw-law/reference prose;
3. both groups retain the same actual organizer metadata/document user message
   as EXP133.

Then run preflight, full fast-20 tokenizer admission, and grouped mock. Compare
to EXP133. This is a diagnostic only; require holdout confirmation before any
dev-200 run.
