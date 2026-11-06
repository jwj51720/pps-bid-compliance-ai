# INC-092: v24 field-alignment full-dev diagnostic result

This previously completed 200-notice Luna diagnostic was re-scored during the
INC-125 follow-up.  It is **not promoted**.

| Metric | Result |
|---|---:|
| Successful calls | 200 / 200 |
| TP / FP / FN | 7 / 45 / 1 |
| v24 positive F1 | 0.233333 |
| Invalid field quotes | 44 |

The one-item field-alignment prompt marginally exceeds the direct INC-088 v24
F1 (`0.222222`) but increases false positives and, critically, produces 44
claimed `match`/`contradiction` field quotes that cannot be recovered as an
unchanged source substring.  This is not a Python resolver issue: the response
contract itself asserted source text that did not occur verbatim.

Consequently, neither this output nor a hybrid with INC-125/126 may be scored
as a promoted policy.  Preserve direct card-v6 v24, which was independently
predeclared for the official-ledger composition.  Do not retry the same v24
wording, relax quote validation, or choose a per-case field-result merge.
