# INC-055: Unlabeled Template-Overlap Audit

## Question

Before self-labeling or case RAG, determine whether organizer-provided
unlabeled notices contain exact reusable document/template material from dev.
Without such overlap, dev-labelled examples are more likely to teach
surface-language correlations than transferable legal reasoning.

## Method

For every source document, compute SHA-256 after Unicode NFC normalization and
whitespace normalization only.  For documents that are not exact duplicates,
compute the set of normalized nonempty source lines and measure whether an
unlabeled notice shares an entire line with a dev notice.  No label changes a
hash, line set, matching rule, or ranking.

The report describes all-dev overlap and, only as a diagnostic, the fraction
of each item's dev-positive notices having an unlabeled exact-document or
shared-line neighbor.  It never transfers a label.

## Gates

- **Advance to narrow case research:** meaningful exact-document reuse or a
  coherent item-level source-line overlap concentration, with provenance.
- **Partial:** only line/template fragments recur.  Use them only to form
  source-fact strata for later self-label sampling; do not inject dev labels.
- **Reject generic case RAG:** no meaningful overlap.  Do not label or retrieve
  notices based on generic nearest-neighbor similarity.
