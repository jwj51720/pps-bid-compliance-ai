# INC-041: Controlled v2 Addition to the v3/v21 Composition

## Scope and invariant

INC-041 takes the verified INC-037 materialized CSV as its immutable input and
replaces **only** `v2/e2` with the frozen INC-040 predicate. Thus the v3/v21
components are not rerun, retuned, or selected again. The output must retain
INC-037 row order and every non-v2/e2 cell byte-for-byte.

## Robustness audit

The new v2 parser runs on the 20,000-record organizer-format unlabeled corpus
only to record its reason classes and verify each positive evidence string is
contained in the original notice. No labels, threshold changes, prevalence
claim, or hidden-test score are derived from this scan.

## Decision gate

Record the controlled dev composition and provenance audit. A perfect result on
seven v2 positives does not authorize wording expansion. The component remains
an experimental candidate until a submission-parity integration audit and a
separate, non-dev basis for its legal-role coverage are available.
