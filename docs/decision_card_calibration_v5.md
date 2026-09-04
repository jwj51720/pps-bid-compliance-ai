# Decision card v5 calibration review

## Purpose and scope

This is a narrow, source-backed revision plan for `decision_cards_v4`.
It does **not** add a new retrieval strategy, threshold, product list, or a
notice-specific correction.  It changes only model-facing wording where the
existing v4 wording makes a known logical distinction easy to miss.

The legal source of every added condition is the organizer-provided text
preserved in `data/derived/legal_condition_ledger_v1.json` and summarized in
`docs/legal_condition_review_v1.md`.  Dev metrics identify which direction to
inspect; they do not supply the legal condition.

## What the completed runs say

The full-dev v2-card run, EXP014, is the only directly comparable 200-notice
card result.  It shows two materially different error modes:

| calibration class | items | EXP014 pattern | v5 policy |
| --- | --- | --- | --- |
| Require narrower affirmative proof | v3, v9, v19, v21, v23, v24 | repeated false positives: 22, 13, 14, 11, 4, 5 respectively | Make the missing conjunction explicit; keep 0 when field, timing, scope, or comparison basis is not explicit. |
| Recall is blocked by missing factual applicability | v2, v4–v8, v10–v18, v20 | several items had zero or near-zero recall | Do not invent a threshold or product classification in a card.  State the decision sequence more clearly; obtain the missing factual input separately before relaxing a final condition. |
| Stable current formulation | v1, v22 | usable precision/recall in EXP014 | Keep v4 wording unchanged. |

Fast-panel EXP091/EXP092 is a diagnostic only.  Its many all-zero labels and
EXP092's three output-cap parse failures make it inappropriate as a source of
new item-specific legal rules.  It does, however, confirm that output capacity
must be restored before comparing prompt policies.

## v5 changes

`scripts/build_decision_cards.py --version v5` produces an artifact that
inherits v4 and changes only the following items.

| item | direction | explicit v5 distinction |
| --- | --- | --- |
| v3 | stricter | Compare a participant's single required performance amount only to a same-purpose, same-scope comparison amount. |
| v4 | clearer, not broader by assumption | A specific institution limitation and a specific issuer/type performance limitation are alternative patterns; either still needs the high-value and no-permitted-reason conditions. |
| v9 | stricter | A model name must be a mandatory procurement requirement, not an example, existing-equipment reference, or a performance specification with equivalent goods allowed. |
| v19 | stricter | The confirmation must be required before bid/proposal submission; a generic list of documents is not enough. |
| v20 | stricter applicability | A software registration/industry phrase alone does not prove the procurement is an SW project in an applicable value band. |
| v21 | stricter | A number must be a minimum participation share under an identified joint-contract method, not a representative share, investment ratio, or performance ratio. |
| v23 | stricter | The applicable local negotiated-contract status, amount band, and all dates needed for the calculation must be present. |
| v24 | stricter | Compare only explicit values of the same semantic field; a restriction phrase itself is not a metadata mismatch. |

All other v4 cards remain byte-for-byte policy-equivalent in v5.  In
particular, the product and absence cards are not made more permissive just to
recover dev positives.  Their principal missing input is a defensible
competition-product/general-product applicability fact, not a better synonym.

## Group-specific instructions

The existing three groups should retain their distinct truth contracts.

| group | items | required instruction |
| --- | --- | --- |
| Presence | non-absence items except v24 | Decide each card independently.  A positive needs both its card conditions and source-document evidence from the current pass.  Never transfer a condition or evidence phrase from another v. |
| Absence | v10, v11, v16, v18, v20 | First establish applicability; then search every document for the required condition/exception.  A pass is 1 only when applicable and the condition is absent.  The pipeline AND-merges passes.  Unknown applicability is 0, not a reason to treat one document as missing. |
| Consistency | v24 | Build only same-field pairs from an explicit notice value and metadata value.  Emit 1 only for an incompatible pair; otherwise 0. |

The last two are already implemented as task-specific workflows in
`src/prompt.py`.  v5 changes card wording, not merge logic.

## Required experiment sequence

1. Restore both `llm.max_tokens` and `prompt.output_reserve_tokens` to 2500.
   The reserve must match the output limit so exact tokenizer admission leaves
   room for a complete JSON response.
2. Run a serialization/runtime control with v4 unchanged.  This isolates the
   1536-token EXP092 parse failure from any card effect.
3. Run a v5-only ablation from that control: same provider, seed, groups,
   contexts, merge policy, product index, and output schema.
4. Run preflight and exact mock admission before each paid call; promote only
   after fast-panel evidence and then dev-200 confirmation.

No v5 result is currently a canonical or submission policy.

## Fast-panel outcome (2026-09-03)

The planned controls were executed after this review was written.

| experiment | differing policy | macro F1 | parse errors | calls |
| --- | --- | ---: | ---: | ---: |
| EXP092 | v4, 1,536 output reserve | 0.11944 | 3 | 126 |
| EXP094 | v4, 2,500 output reserve | 0.10625 | 2* | 133 |
| EXP095 | v5, 2,500 output reserve | 0.08523 | 0 | 134 |

`*` Both EXP094 malformed responses contained every requested field and only
missed the final outer `}` after trailing whitespace.  The new deterministic
parser recovery accepts exactly that form; it makes no label or evidence
change.  The two recovered payloads contained all-zero values, so this does
not change EXP094's score.

EXP095 is not a promotion candidate.  Its intended stricter wording reduced
one v9 false positive and one v19 false positive, but v3 false positives rose
from two to five and the final macro F1 fell.  Because remote generation also
varied (call count 133 vs. 134), this fast-panel comparison is directional,
not a claim that every v5 sentence is harmful.  The next card iteration must
be narrower than v5: preserve a change only after its target item's TP/FP/FN
has been isolated and repeatable, rather than bundling eight wording changes.
