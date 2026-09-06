# INC-049: Criterion-to-Source-Line Retrieval Audit

## Question

Can the permitted `BAAI/bge-m3` model retrieve the unchanged source line that
contains an organizer-provided dev evidence string when the query contains
only the competition item's published criterion and the notice metadata?  This
tests the retrieval link in the proposed `extract -> retrieve -> adjudicate`
architecture.  It is not a classifier experiment, a candidate-count sweep, or
a replacement for reading the full notice.

## Fixed corpus and units

The corpus is every nonempty, unchanged source line from every dev notice,
with the document order and source offsets retained.  Lines longer than 500
characters remain in the retrieval corpus but are marked non-selectable for a
future evidence response; this audit reports their status rather than cutting
them.  INC-048 established that a line, unlike a punctuation sentence, keeps
the organizer evidence intact in the relevant table/layout cases.

For every notice/item whose positive dev label has a nonempty organizer
evidence field, the success target is any source line of *that notice* that
contains the full evidence string.  Labels and evidence are used only after
ranking for evaluation.  They do not alter a query, corpus membership, or
ranking.

## Representations

Each source line is embedded once with BGE-M3 `search_document` input type.
For every notice/item, rank that notice's own source lines by cosine similarity
for two predeclared, non-adaptive queries:

1. `criterion`: item id, organizer item name, national/local law text, and
   note from the item table;
2. `criterion_plus_metadata`: the same query plus canonical JSON metadata for
   the notice.

This deliberately does **not** use an LLM-produced rationale yet.  If the
criterion cannot recover source evidence above a lexical reference, adding a
second model stage is not justified.  If it can, an independent later pilot
may replace the criterion query with a source-unquoted fact ledger, while
retaining full-document final judgment.

## Transport and reproducibility

Every BGE input is a complete source line.  Requests are checkpointed by
notice after its rank rows have been computed.  The initial request size is
128 inputs: this replaced the initial 512 only after the provider held a
512-line request for over four minutes after three successful batches, before
any retrieval rank was produced.  It is a transport setting, not a
model-selection value:
on a provider size failure, the same ordered batch is recursively bisected
until accepted, with no line discarded.  The report records all request sizes,
usage, source hashes, query hashes, and failures.

## Measurements and gates

For each query representation, report exact-evidence recall and reciprocal
rank across all eligible notice/item pairs, plus rank quantiles and per-item
counts.  The report presents recall at ranks 1, 3, 5, 10, and 20 only as a
descriptive retrieval curve; it does not select one as a production cutoff.
A later final-stage prompt must admit candidates by exact token budget and
must not turn a missing retrieved candidate into a negative decision.

- **Advance:** `criterion_plus_metadata` has materially higher reciprocal
  rank than the lexical reference and at least 90% evidence recall by rank 20,
  with no source loss or unresolved transport failure.  Proceed to a separate,
  repeated small pilot in which an LLM fact ledger is a retrieval query only.
- **Partial:** retrieval improves over lexical but misses the 90% gate.
  Diagnose document type/layout and keep it only as evidence-resolution
  research; do not use it to gate labels.
- **Reject:** no improvement over lexical, source loss, or transport failure.
  Do not add a rationale-extraction call for this architecture.

The 90% value is an evidence-preservation requirement, not a score-tuned
candidate-count: a retrieval layer that systematically omits at least one in
ten known source grounds cannot safely influence a compliance decision on an
unknown test distribution.
