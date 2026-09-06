# INC-027 r1: Extract-Then-Adjudicate Result

## Validity

The original `inc027_extract_then_adjudicate_pilot/` execution is invalid. Two
notices completed before the third extractor returned non-parseable JSON; this
exceeded the preregistered 5% failure threshold. Its raw checkpoint is retained
for diagnosis and it contributes no score.

The amended r1 executed the unchanged eight-ID frozen cohort with a clarified
fact-type schema and per-notice fsync-backed checkpoints. All eight extractors
and all eight adjudicators succeeded (0/16 parse or transport failures). Every
treatment non-absence positive had an unchanged source substring after the
ledger/source gate (14/14, 100%). Reported r1 API cost was $0.02765582.

## Paired result

| Arm | Macro F1 | TP | FP | FN | Micro recall | Valid positive evidence |
|---|---:|---:|---:|---:|---:|---:|
| Frozen INC-024 joint control, same 8 notices | 0.16627 | 8 | 9 | 11 | 0.42105 | 17/17 |
| INC-027 r1 extract then adjudicate | 0.14444 | 7 | 7 | 12 | 0.36842 | 14/14 |
| Treatment minus control | -0.02183 | -1 | -2 | +1 | -0.05263 | 0.00 pp |

The seven changed label cells were: three false-positive removals (`01/v5`,
`01/v14`, `033/v13`), one recovered true positive (`049/v21`), one introduced
false positive (`02/v17`), and two lost true positives (`033/v19`, `035/v17`).
Thus the treatment has four individually corrected cells and three newly wrong
cells, only **one net corrected cell**. There are no all-negative notices in
this frozen first-eight cohort, so the all-negative clause of the success gate
is not observable rather than passed.

## Decision and interpretation

**Rejected.** The success gate requires at least four net corrected cells; r1
has one, while Macro F1 and recall both decline. The extractor was able to
produce source-valid ledgers after schema clarification, so the failure is not
an evidence-validation or structured-output failure. It is an adjudication
quality failure: splitting factual discovery from legal judgment removed some
speculative positives but also made the model miss two true violations. Do not
promote a general extract-then-adjudicate pipeline, run its 24-notice
confirmation, or make a second wording repair to the adjudicator.

## Next direction

The next broad branch should not be another global prompt topology. The
obvious v24 field-reconciliation branch is already closed by INC-011/011R:
its broad candidate extractor had 87.5% positive coverage with 76.0% negative
activation, while its layout-safe repair fell to 37.5% coverage. Repeating it
would be local lexical repair, not new research.

The remaining global signal worth isolating is **complete legal-article
context**. INC-021 raised full-dev Macro F1 over INC-018, but it confounded
retrieved legal context with four output families; INC-024 independently
rejected the output-family change. The next action is therefore a no-API,
source-hash-bound admission audit: map each item to its already-resolved
organizer-law article unit, measure exact tokenizer admission for a single
joint-24 prompt, and identify whether an all-item complete-article context is
feasible without a character cap or source truncation. Only if this preflight
admits a defined, legally complete context should a small paired joint-output
pilot test legal context alone. Otherwise it is rejected before model spend.

## Reproduction

```bash
python incubator/src/inc027_extract_then_adjudicate.py --id PPS-DEV-01
# repeat for the seven IDs stated in the preregistration
python incubator/src/inc027_extract_then_adjudicate.py --aggregate
```

Artifacts: `incubator/runs/inc027_extract_then_adjudicate_pilot_r1/`.
