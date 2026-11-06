# EXP133 — two-way G02 output-scope validation

## Why this is a new experiment

EXP132's complete four-way partition was rejected: dev-200 macro positive F1
was `0.22181`, below the exact organizer-format control EXP109 (`0.22350`),
and it multiplied calls by four. A post-run **counterfactual audit** replaced
one four-way group's predictions into the exact control row. Only G02 was
positive on every frozen cohort:

| Cohort | Exact control | G02-only counterfactual |
| --- | ---: | ---: |
| fast-20 | 0.17196 | 0.20668 |
| independent holdout-20 | 0.12500 | 0.16667 |
| dev-200 | 0.22350 | 0.25133 |

That audit is not a runnable policy: predictions came from independent calls.
EXP133 therefore tests the smallest real execution partition implied by it.

## Controlled policy

The base is EXP125A. This changes only the versioned output partition:

- G01: `v1`–`v5`, `v10`–`v18`, `v20`–`v24` (19 items);
- G02: `v6`, `v7`, `v8`, `v9`, `v19` (5 items).

Each group receives the same actual organizer-format 4,000-character notice
context. Its system/schema names only its own items. The final row is a
disjoint union of the two LLM outputs. There is no overlap, output reuse,
label rule, card, retrieval, product context, document split, decoding change,
or post-hoc correction.

## Mandatory gates before the paid run

1. Export and read actual system/user messages for `PPS-DEV-062` (complete),
   `PPS-DEV-042` (announcement overflow), and `PPS-DEV-01` (attachment
   overflow). The two user messages per notice must be byte-identical; each
   system/schema must contain exactly its declared keys.
2. Run experiment preflight, exact-tokenizer admission for all fast-20
   records, and grouped mock execution. Expected calls: 20 notices × 2
   groups = 40.
3. Save every export under the isolated output directory and record the review
   conclusion in the result document.

## Decision rule

Compare against EXP125A. Continue to a separately configured holdout only if
the fast-panel macro F1 does not decline, the five G02 items do not regress in
combined F1, parsing is clean, and runtime is materially below four-way
execution. No item-specific repair is allowed from the fast-panel labels.
