# INC-119: Gemma official-law transfer pilot

## Purpose

Transfer the now-replicated Luna official-law context to the target Gemma model
without changing the notice, metadata, item schema, or output budget. This is
a small transfer gate, not a final Gemma score estimate.

## Fixed design

- Model: `google/gemma-4-26b-a4b-it` through OpenRouter.
- Two arms for the same 16 fresh notices: archived card-v6 and official-law
  ledger.
- Cohort: 4 notices from each contract profile, SHA-256 selected after all
  three INC-118 cohorts were excluded; labels were not used in selection or
  prompts.
- Output limit: 1,200, matching the existing Gemma direct-decision setting.

## Transport result

The first call yielded three parser failures caused by a valid JSON object
followed by explanatory text. Two official-ledger rows succeeded on the one
permitted retry. Card-v6 `PPS-DEV-062` repeated that form. Its earliest raw
response's first JSON object was schema-valid and was recovered without another
model call. `src/inc119_recover_first_json.py` fixes this choice to the earliest
checkpoint row; it cannot select the later response after labels are read.

All 16 paired rows are therefore evaluable.

## Result

| Policy | Macro-F1 |
| --- | ---: |
| Gemma card-v6 | 0.06250 |
| Gemma official-law ledger | 0.07963 |
| Paired delta | +0.01713 |

The sign agrees with Luna but the effect is too small, and the absolute score
too low, to promote the transfer. This cohort is deliberately tiny and its
class mix is not a leaderboard estimate.

## Decision

Keep the Luna official-law branch promoted. Do **not** yet apply it as a Gemma
submission policy or scale it to unlabeled data. The next Gemma work must first
inspect the paired false negatives/false positives and separate: (1) source
facts absent from the compact legal context, (2) source facts present but
Gemma misclassified, and (3) JSON transport failures. Any new Gemma prompt must
change one of those observed failure modes, not merely add more legal text.

Artifacts: `runs/inc119_gemma_legal_transfer16/`, frozen manifest
`data/derived/inc119_gemma_legal_transfer16_manifest.jsonl`, and deterministic
recovery record `runs/inc119_gemma_legal_transfer16/deterministic_recovery.jsonl`.
