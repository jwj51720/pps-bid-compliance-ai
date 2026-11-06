# INC-025: Leave-One-Out BGE Case-RAG Retrieval Audit

## Controlled question

Can generic semantic similarity between complete organizer notices retrieve
other dev notices with the same violation item strongly enough to justify a
global few-shot Case RAG branch? The protocol was fixed in
`inc025_case_rag_retrieval_preregistration.md`; no Gemma judgment call or
prediction was made.

## Execution

- 200 dev notices were represented by 440 source-preserving BGE units.
- Units respect source paragraph boundaries, then source line/table-row
  boundaries only when a paragraph exceeds the BGE-M3 8K context contract.
- Exact BGE tokenizer input: 1,917,473 tokens; reported embedding cost:
  `$0.01917539`.
- No atomic source line was unembeddable and no text was silently truncated.
- The first two batches of an initial transport probe completed, then a batch
  at local count 8,192 was rejected by OpenRouter as 8,193 tokens. Before any
  retrieval metric was calculated, the rerun reserved that one observed
  transport token. The valid rerun is the sole result below.

## Result

Only 8 of 24 items had a positive-query leave-one-out enrichment above 2× the
available-corpus base rate at any of ranks 1, 3, or 5. The clearest isolated
signals were v9 (rank-1 6.63×), v12 (6.63×), and v21 (13.27×); v17 had 3.98×
at rank 5. Most items had zero same-label neighbor at rank 1, including v1,
v2, v4--v8, v10--v11, v13--v16, v18--v20, and v22--v24.

The full per-item average precision/enrichment table and provenance-preserving
top-five neighbors are retained in ignored
`incubator/runs/inc025_case_rag_retrieval_audit/`. The BGE vectors are stored
as a reproducible derived artifact, not a trained model.

## Decision

**Failure for global Case RAG.** The pre-registered gate required 12 items
with at least 2× enrichment or a coherent task-shape-specific effect. Eight is
below that gate, and the isolated signals span unrelated task shapes rather
than forming a reliable branch. No generic dev-few-shot Gemma experiment and
no self-label expansion follows from this result.

This is useful negative evidence: raw whole-notice semantic similarity is too
dominated by generic procurement language. If Case RAG is revisited, retrieval
must be conditioned first on a verified source fact or evidence type (such as
a product code, normalized date/ratio, or a typed metadata field), and that
conditioning must pass an offline retrieval audit before any few-shot call.
The next primary branch is therefore source-aware deterministic fact/evidence
extraction, not another embedding-rank or prompt variation.
