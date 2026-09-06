# INC-080: Teacher casebook pilot protocol

## Fixed purpose

Test whether a permitted external teacher can create useful, reproducible case
records from organizer-provided unlabeled notices before spending on the full
20,000-record corpus.  The final model is not replaced: the records are static
retrieval context for a later Gemma comparison.

## Frozen input cohort

`inc080_teacher_pilot_manifest.py` selects 256 records without opening
`dev_labels.csv`.  Its stratum is observable `업무구분 × 계약방법 × document
signature × source-length decile`; it covers each of the 128 most common strata
once before any stratum receives a second record.  A length decile is a corpus
rank, not a character-rule or a label threshold.

## Teacher record contract

For each full organizer notice, the teacher receives the unmodified metadata,
all source documents in their order, the 24 item names, and only organizer
provided legal material.  It returns:

1. a flat `v1`--`v24` label vector;
2. a compact case signature describing procurement/object/restriction facts;
3. for each positive, a one-to-two-sentence legal decision basis and an exact
   source-document quote or offset; and
4. no invented fact when source support is absent.

The raw response, schema validation result, model/provider, generation
settings, input hash, token use, and retry history are persisted.  The compact
retrieval record is derived from the raw response; neither can overwrite it.

## Two teacher topologies

- **T1 direct legal decision report:** full notice plus legal material -> case
  signature, labels, positive bases.
- **T2 extract then decision report:** full notice -> structured factual ledger
  -> labels/bases from that ledger plus the legal material.

They are compared on the same frozen 256 notices.  This is not a claim that T2
is final inference; it determines which offline case representation is more
complete and stable.

## Promotion criteria

Advance a topology to case-RAG evaluation only when all are true:

- >= 98% schema-valid records after bounded retries;
- >= 95% full-source admission (no silent truncation);
- positive bases with a valid source quote for >= 90% of teacher positives;
- a fixed repeat subset has >= 0.85 mean item-label agreement; and
- projected 20k cost, artifact size, and creation time fit the project budget.

The later decisive metric is not teacher agreement: it is held-out Gemma
Macro-F1 in the predeclared direct vs lexical/BGE/hybrid case-RAG comparison.
