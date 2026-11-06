# INC-103: unlabeled high-reasoning casebook T1 pilot

## Purpose

Create a small, auditable static casebook from organizer-provided unlabeled
notices.  It is not a prediction experiment and does not inspect dev labels.
Its only question is whether the high-reasoning direct case-report contract can
produce retrievable records with complete source provenance before any corpus
scale-up.

## Fixed input and budget

The first 16 rows of INC-080's pre-existing, label-free, 256-notice structural
manifest are used unchanged.  Each receives one `gpt-5.6-luna` call with full
metadata, all documents, card v6, `reasoning=high`, and an 8,192 output cap.
Concurrency is two; no retry is made after a failed call.  Maximum calls: 16.

## Record contract and gate

The response has a compact notice-level case signature plus 24 `{v,basis,quote}`
entries.  Positive quotes must validate as unchanged substrings of the current
unlabeled notice.  Raw outputs, validated records, input hashes, request
settings, and failures are retained.  Advance only if all 16 responses are
schema-valid, at least 95% of positive quotes validate, and no input is
silently truncated.  A passing pilot permits a fixed repeat subset and then a
64-record scale test; it does not yet justify RAG or 20k labeling.
