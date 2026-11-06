# EXP137 — G02-only decision-card result

## Verification

- Focused suite: 58 tests passed before the paid call.
- Preflight reported exactly one allowed difference:
  `grouped_run.decision_cards_overrides.G02_document_restrictions`.
- Actual rendered message review covered `PPS-DEV-062`, `042`, and `01`.
  G01 had no card and exactly matched EXP133's token counts; G02 had exactly
  v6/v7/v8/v9/v19 cards; paired user-message hashes were identical.
- Full fast-20 admission: 40 calls, maximum 4,132 input tokens.
- Mock: all 20 rows completed.

## Result and decision

| Run | macro positive F1 | G02 mean F1 | evidence validity |
| --- | ---: | ---: | ---: |
| EXP133 two-way no-card control | **0.26151** | **0.43333** | 0.76744 |
| EXP137 G02-only card v6 | 0.22391 | 0.23333 | **0.92857** |

The cards lowered v6 from F1 0.500 to 0, increased v8 false positives from 2
to 4 while retaining no true positive, and lowered v19 from 1.0 to 0.5.
Evidence formatting improved but decision quality declined. Reject this card
variant; do not run holdout or dev-200 and do not edit the cards from these
fast-panel labels.

The isolated group-card override remains useful infrastructure: it made the
otherwise confounded root-card configuration (EXP136) detectable before a paid
call and keeps future group-specific prompt tests reproducible.
