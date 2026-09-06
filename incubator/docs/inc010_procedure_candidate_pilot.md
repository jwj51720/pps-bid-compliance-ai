# INC-010: Procedure Candidate-Window Pilot

## Locked design

INC-009R makes only v19--v21 eligible: each retains 100% candidate recall
after generic-cue removal. v22 and v23 are explicitly excluded because their
refined candidate recall is below 0.90. This pilot outputs exactly v19--v21 in
both arms; it does not compare an active output with Joint-24 output.

The cohort includes every dev notice positive for v19--v21 (17 notices), the
12 negative notices with greatest precomputed v19--v21 candidate burden, and
four deterministically ordered no-candidate negatives. Labels choose the cohort
only after the candidate manifest is frozen. Both policies receive metadata,
the same model, temperature, seed, JSON schema, output cap, and evidence
validator.

- Control: ordered 12,000-character source prefix.
- Treatment: exact source-local candidate spans from the frozen manifest,
  organized by source document and capped in deterministic document/offset
  order; a 1,200-character announcement anchor is retained for
  notice identity. Candidate absence is explicitly not a proof of no violation.

Requests run in batches of at most eight independent OpenRouter calls. Each
response is checkpointed with raw content before parsing, and batch failure is
recorded per request rather than causing a silent whole-batch fallback.

## Gates

Success requires treatment target macro F1 at least control +0.05, target
recall non-decreasing, valid evidence at least 0.95, and no more than one new
false positive in either v19, v20, or v21. Partial success permits one repair
to span packing only. Failure rejects candidate-window judgment for this family;
the source-offset extractor remains available for evidence alignment.

## Result

The eight-worker batch completed all 66 unique requests in about one minute.
There were 65 parseable successes; one candidate-treatment response was not
JSON and used the predeclared all-zero fallback. The control used 223,427 prompt
tokens and $0.03287; treatment used 110,552 prompt tokens and $0.01720.

| Policy | Target Macro F1 | TP / FP / FN | Micro recall | Evidence validity |
|---|---:|---:|---:|---:|
| 12k prefix control | 0.39434 | 11 / 19 / 6 | 0.64706 | 0.96667 |
| Candidate treatment | 0.38974 | 10 / 16 / 7 | 0.58824 | 1.00000 |

The treatment reduced three false positives but lost one v21 true positive, so
Macro F1 fell by 0.00460 and recall fell by 5.88 percentage points. v19 was
unchanged; v20 was zero-recall in both arms; v21 accounted for every changed
cell. The lost v21 positive had seven available candidate windows, so this is
not a simple candidate-cap overflow that justifies a packing repair.

## Decision

**Failure: reject candidate windows as the v19--v21 judgment context.** The
extractor remains useful for source-offset evidence alignment and lower-token
scheduling research, but it is not a label policy and must not suppress a
positive outside its windows. Do not prompt-tune this family again.

The next independent branch is v24 typed reconciliation: deterministic
source-to-metadata field extraction and normalization can be audited without
model calls, then Gemma can adjudicate only ambiguous field pairs. This changes
the task shape rather than continuing context/prompt fishing.
