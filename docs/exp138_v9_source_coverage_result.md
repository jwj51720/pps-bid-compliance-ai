# EXP138 — v9 source-coverage result

## Verification

- Preflight disclosed all three G03 context changes, including explicit
  `max_document_chars: null`. The audit was first fixed to distinguish an
  unset key from an explicit null; otherwise this material change would have
  been missed.
- Actual-message review covered complete, overflow, and attachment notices,
  plus the three source-inaccessible v9 examples `09`, `12`, and `23`.
  Their G03 규격서 passes visibly contained the formerly absent `GB10`,
  `TurboJet`, and `DJI Matrice` source text.
- Fast-20 admission: 79 underlying calls (20 G01, 20 G02, 39 v9 document
  passes), maximum input exactly 14,848 tokens; mock completed.

## Result

| Run | macro positive F1 | v9 TP / FP / FN | v9 F1 | provider call latency sum |
| --- | ---: | ---: | ---: | ---: |
| EXP133 two-way control | **0.26151** | 0 / 0 / 1 | 0.0 | 257.7 s |
| EXP138 v9 complete-source passes | 0.23075 | 0 / 1 / 1 | 0.0 | 371.6 s |

There were no parse errors. EXP138 is rejected for the fast-panel policy
comparison: it adds source passes and latency without improving v9.

## Important scope limitation

The frozen fast-20 contains only one v9-positive notice (`PPS-DEV-051`), whose
organizer label has no evidence text. It does **not** include the three
evidence-visible-in-규격서 cases (`09`, `12`, `23`) that motivated the source
coverage hypothesis. Thus EXP138 does not prove that complete-source access is
useless in general; it proves only that this expensive v9 split does not earn
its cost on the fast panel and cannot be promoted from that evidence.

Do not run a dev-200 or submission version. A future source-coverage probe may
use a predeclared diagnostic cohort, but it must remain separate from policy
selection and cannot create a label-derived routing or correction rule.
