# INC-103: unlabeled high-reasoning casebook T1 pilot — not promoted

The 16 records were selected from the pre-existing label-free INC-080 manifest;
no dev label entered generation or validation.  Fourteen records were
schema-valid.  Two failed with malformed/truncated JSON (`Unterminated string`)
despite the 8,192 output cap.  Among the 14 valid records, eight positive
quotes were produced and two were not exact source substrings, giving a raw
exact-quote rate of 75%, below the 95% gate.

The invalid quotes were both from one notice and omitted an anonymization
marker embedded in an otherwise verbatim source sentence.  That suggests a
deterministic source-span resolver may recover an exact evidence string, but
it does not cure the two malformed records and is not applied as a retroactive
promotion.  The label distribution is also sparse (mean 0.57 positives per
notice, four v24 positives), so this sample is not yet a useful retrieval
corpus.

**Decision:** do not scale T1 to 64 or 20k.  Before another teacher call,
build and unit-test a source-span resolver that maps a near-verbatim quote with
only organizer anonymization markers omitted back to an unchanged source
substring.  Separately, redesign the casebook output to avoid malformed long
JSON (for example a compact label/signature pass followed by positive-only
source records).  Both are transport/provenance improvements, not a new
judgment threshold.
