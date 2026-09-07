# INC-104: deterministic casebook quote-resolution audit

The resolver was tested with exact match, unique whitespace normalization,
unique organizer-anonymization-tag omission, and ambiguity rejection.  All
three unit tests pass.  On INC-103's eight teacher-positive quotes it resolves
six exact and two anonymization-tag-omitted quotes, returning an unchanged
source substring in all eight cases (100%).

This is evidence recovery only: it neither changes the self-label nor uses a
fuzzy match when more than one source location is possible.  It makes the two
INC-103 quote failures explainable as annotation-format loss rather than source
hallucination, but does not repair the two malformed teacher JSON responses.
