# INC-085 — fact ledger then adjudication: rejected topology

## Fixed experiment

The predeclared question was whether an externalized, source-validated factual
ledger can replace the original notice for final legal adjudication and become
a reusable case-record format.

- 64 dev notices were frozen without reading `dev_labels.csv`: one
  deterministically ranked notice from each of the 64 most common observable
  `업무구분 × 계약방법 × document signature × source-length decile` strata.
- Stage A (Luna): full original documents, metadata, and concise legal cores
  -> 24 per-item `{fact, quote}` entries. It is prohibited from returning a
  violation judgment.
- Validation: every nonempty quote must be an unchanged substring of one of
  the source documents. Invalid entries are cleared before stage B.
- Stage B (Luna): validated ledger + metadata + same legal cores, but **not**
  the original documents -> 24 labels.
- Comparator: already-completed direct Luna prediction from INC-084 on the
  exact same frozen notices. There is no selected ensemble or label-wise merge.

Both stages completed 64/64 after bounded retries. The initial failure mode was
not a model failure: Responses sometimes placed JSON in an `output` message
block rather than the top-level `output_text`. The compatibility handling and
append-only successful-retry selection are retained in the experiment script.

## Result

| Method | Macro positive-F1 on same 64 notices |
| --- | ---: |
| Direct Luna with full notice (INC-084 predictions) | **0.244643** |
| Validated ledger only -> adjudication | 0.173611 |
| Architectural delta | **-0.071032** |

Stage A produced nonempty validated facts for 69.34% of item-notice pairs and
discarded 346 nonempty entries whose quotes did not validate. The remaining
ledger is still not a sufficient representation of an entire legal decision:
the stage-B model misses most positives in conditional, exception, and absence
items. This is an architectural failure, not a character-count or threshold
finding.

## Decision

Do **not** use `e-prime/ledger only -> final label`, and do not bulk-label the
20k corpus with it. The user-proposed fact extraction remains useful only as a
retrieval/case-record component or as supplementary context; a final decision
must retain the real notice documents.

## Next topology

Test a direct **case report** rather than a lossy adjudication hand-off:

`full notice + legal core -> labels + compact cross-item case signature +
positive source quotes`

The final labels are produced while the model can still inspect every document.
The case signature is static training-free retrieval material for a later
Gemma-with-actual-notice comparison. Before producing all 256 unlabeled pilot
records, calibrate this richer output contract on a fixed label-free 64-dev
cohort and compare it to direct-label-only Luna. Promotion requires no broad
loss in direct teacher F1 and a high exact-quote validation rate.
