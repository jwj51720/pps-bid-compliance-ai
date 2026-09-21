# Product candidate retrieval: scope review before implementation

Status: proposal requiring explicit policy direction; no implementation or paid result.

Current product-lookup agreement (`docs/competition_product_lookup.md`) defines organizer CSV
as exact-code reference, not name-similarity search. Existing code supports exact friendly facts
and full-catalog diagnostic only. Do not silently promote similarity scores into applicability.

The saved experiments expose a distinct research question: full-catalog structured EXP247
recovers fast positives, while removing catalog EXP250 returns both unknown-code positives to0.
However EXP249dev200 has4TP/66FP/3FN, so candidate knowledge alone does not prove legal execution.
Plain full-catalog EXP245 never recovers fast positives. BGE candidate retrieval cannot be called
an established solution or a runtime-only equivalent without validating recall and actual scope.

Potential explicitly authorized alternative: retain all original exact-code facts unchanged;
source-grounded purchased-object query → fixed organizer-approved BGE-m3 retrieves a small
candidate set from only the615-row competition-product CSV → render original human-readable
names and full row conditions as non-authoritative candidates → Gemma final rereads actual
sources/cards/metadata and decides applicability/absence. No law/case RAG, keyword legal rules,
unknown→general conversion, model replacement or doc×v grouping. Similarity is not evidence.

First capability probe must be v10-only and predeclared, not a generalized v10–v18 schema.
It must compare whether a correctly supplied candidate helps actual object/condition/absence
reasoning before constructing retrieval or paying a large panel. Oracle-assisted hand-selected
candidate probes are diagnostic, not fast-panel strategy results. Do not select rows using gold
at inference, or label partial candidate machinery as a complete retrieval strategy.

If authorized, declare candidate policy/base/allowedchanges, complete source provenance,
query/candidate coverage, exact tokenizer and final complete-input contract, actual rendered
short/attachment/overflow messages, exact shared-pipeline mock, isolated outputs. Fixed fast
and independent holdout must establish precision/recall beforedev200. V-only evidence-exempt
v10 can test labels without evidence-recovery confounding; no extra repeated-vote pass.

Local environment inspection:transformers available, torch/sentence_transformers/FlagEmbedding
absent. No BGE or GPU inference has been tested here. Dependency/model installation is not
performed merely to investigate this proposal. A local CPU setup or other environment would
need its own verified fixed-model execution, tokenizer/runtime and offline-submission packaging.

Decision now: request whether this CSV-only candidate search may be explored as a separately
versioned exception to the current exact-lookup-only agreement. Root/submission unchanged.
