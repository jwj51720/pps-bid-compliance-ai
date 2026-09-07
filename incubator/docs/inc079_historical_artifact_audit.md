# INC-079: Historical submission-artifact audit

## Material inspected

`dist/pps-artifacts_20260904_mac.tar.xz` (229,956,104 bytes) contains the two
successful submission zips, staged submission code, full-dev artifacts, and
historical configurations through EXP-120.  This audit reads the archive; it
does not copy or modify the archived project.

## Verified anchors

| Experiment | Local Macro-F1 | Runtime | Tokens | Cost | Public score | Interpretation |
|---|---:|---:|---:|---:|---:|---|
| EXP-109 official V/E baseline | 0.223498 | 513.8s | 0.932M | $0.130 | 0.210360 | Most reliable calibration anchor. |
| EXP-014 full split + card v2 | 0.228021 | 1,305.1s | 4.659M | $0.462 | 0.183495 | Local gain did not transfer; architecture is too expensive. |
| EXP-116 announcement only | 0.234542 | 223.0s | 0.925M | $0.125 | not submitted | A local diagnostic only. |
| EXP-120 single pass + card v6 | 0.248932 | 337.4s | 1.493M | $0.188 | not submitted | Best archived low-cost local single-pass arm; needs independent confirmation. |

The EXP-109 staged runtime is concrete: vLLM batch size 128, fixed Gemma,
16,384 model length, 1,536 output-token reserve, int8-per-channel default
quantization, and no RAG/card asset.  Its local-to-public delta is only -0.0131.
EXP-014's measured local runtime is optimistic relative to the 96m50s public
runtime; all multi-pass proposals must use public runtime as the safety bound.

## Consequences

1. Full document expansion, splitting, and strict evidence merging are not the
   default path.  They were both locally weak or public-weak and consume the
   scarce two-hour execution budget.
2. A 4,000-character direct call is not merely a weak baseline: it is a
   submission-proven control.  It leaves room for a second retrieval-informed
   call and conditional adjudication inside two hours.
3. EXP-120 is worth keeping as a *separate* control when building the new
   pipeline, but must not become final policy until it has public evidence.
4. The new branch must add information (the allowed 20k case corpus), not just
   another card or a document-selection variation.
