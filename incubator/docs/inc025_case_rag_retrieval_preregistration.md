# INC-025: Leave-One-Out Case-RAG Retrieval Audit

## Purpose

The competition permits case RAG from labelled dev examples and self-labelled
organizer notices, but retrieval should not be assumed useful just because it
is available. This experiment asks a narrower, generalization-oriented
question: when the query notice is excluded, does BGE-M3 retrieve dev notices
with the same item label more often than the label base rate?

It makes no Gemma judgment call and cannot change a prediction or submission.
It is a retrieval-admission gate for later few-shot/self-label work.

## Representation and boundary policy

Every source document is represented completely. BGE-M3 has an 8K-context
contract. A source document is first divided only at existing blank-paragraph
boundaries; a paragraph that exceeds that contract is divided at existing line
(including table-row) boundaries. Adjacent intact units are greedily packed up
to the exact BGE tokenizer's 8K admission limit. An atomic line that itself
does not fit is recorded as an unembeddable source condition; it is never
silently truncated.

### Transport admission amendment (before a valid result)

The first execution received an OpenRouter 400 at local-tokenizer count 8,192:
the provider reported 8,193 input tokens against its 8,192 maximum. Before any
retrieval result was calculated, the admission policy was therefore amended to
reserve the one provider-observed transport token (`8192 - 1 = 8191`). This is
an API framing requirement, not a dev-derived length or a score-selected
parameter. A whole final atomic unit moves to the next pack; no source text is
discarded or shortened. The two completed probe batches are not used as a
retrieval result.

This 8K value comes from the embedding model's published context contract, not
from dev lengths or a score sweep. It is not a Gemma prompt length and cannot
be reused as one.

Each notice-to-notice similarity is the maximum cosine similarity over its
source-unit embeddings. The query notice is excluded from its own candidate
set. No label, legal-item wording, historical model error, or dev result
changes embedding text or retrieval rank.

## Measurements

For each item with at least two dev positives, report leave-one-out average
precision and positive enrichment at ranks 1, 3, and 5 relative to the
available-corpus positive base rate. Also report source-unit counts, admission
failures, BGE token usage/cost, and nearest-neighbor provenance. Rank metrics
are descriptive; they do not choose a later prompt's number of demonstrations.

## Decision

- **Success:** at least 12 of the 24 items have positive enrichment above 2×
  base rate at one or more reported ranks, with no unembeddable atomic source
  unit and the predicted cost below $0.10. Proceed to a separately
  preregistered, leave-one-out *Gemma* few-shot pilot using balanced retrieved
  positive/negative examples.
- **Partial:** enrichment is concentrated in a coherent task shape (for
  example, product coding or document layouts) but fewer than 12 items. Limit
  Case RAG investigation to that shape; do not make it a global policy.
- **Failure:** no coherent enrichment, source admission failure, or cost gate
  failure. Do not spend on few-shot prompt experiments; pivot to self-label
  candidate mining or deterministic fact extraction.

The resulting vectors and neighbor records are generated competition-data
artifacts. They are ignored locally and must be reproducibly regenerated or
packaged only if later selected for submission.
