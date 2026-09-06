# INC-111: Gemma direct versus BGE case-RAG pilot

Use the first eight IDs of the pre-existing label-free structural manifest.
Each receives two paired Gemma calls with the same full notice, metadata,
cards, model, output schema, and decoding.  The treatment alone receives the
top-three BGE-retrieved static case records from the 58-record unlabeled-only
casebook.  Retrieved self-labels are non-authoritative precedents; the current
notice remains the sole decision source.  No dev label is in the index.

Advance only if all calls parse and the treatment improves paired macro F1;
otherwise do not scale the casebook or RAG context.
