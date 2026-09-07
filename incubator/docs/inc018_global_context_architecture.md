# INC-018: Global Context-Architecture Ablation

This is the first incubator experiment that treats all 24 labels and every
dev notice as the unit of comparison. It replaces item-specific prompting with
a direct comparison of two complete-document architectures: one joint full
notice pass, and independent source-document passes with the competition's
logical merge contract.

`single_full` reads all documents and metadata once. `full_split_merge` sends
each source document to Gemma independently, includes only a bounded
announcement anchor for non-announcement documents, requires non-absence
evidence from that pass's target document, OR-merges non-absence decisions,
and AND-merges absence decisions. Oversized documents are split only after
exact tokenizer admission. Both policies use the same 24-item prompt, model,
schema, temperature, seed, and whole dev set.

Success requires split macro positive-F1 above single by 0.02, non-decreasing
evidence validity, and at least 95% successful calls. Per-label results form
the next global error atlas. No root policy or submission code changes here.

## Result

The all-dev baseline is established. `single_full` scored Macro F1 0.19361
(TP/FP/FN 49/241/104; recall 0.32026; evidence validity 0.70690), close to the
team's external 0.21 result. It is therefore a credible global baseline rather
than a small-cohort artifact. `full_split_merge` scored 0.15108 (63/981/90;
recall 0.41176; evidence validity 0.15613), failing its gate decisively. One
of 574 calls timed out after retry; 573/574 succeeded, so the failure rate did
not invalidate the comparison.

The split architecture increased recall by OR-merging speculative positives
from unrelated document passes. Its strict target-document evidence gate did
not repair this because the model still generated many locally valid but
legally irrelevant snippets. Reject `full_split_merge` as a global policy.
Keep `single_full` as the dev-200 reference and use its per-label TP/FP/FN
table as the error atlas.

The atlas selects the next *family*, not a single item: product/procurement
compliance v10--v18. It contains the largest concentrated error: v13 alone
has all 6 positives but 115 false positives, while v10--v12 and v14--v18 have
near-zero recall. These nine items share organizer-provided exact product-code
and procurement-status facts, unlike the unrelated monetary/geographic and
procedure families. The next step is an offline applicability matrix from that
official index, followed only if it has auditable coverage by a frozen
family-card experiment across all nine items.
