# INC-044: v2/v4 Source-Candidate-ID Coverage Audit

## Purpose

INC-042 failed because free-text evidence generation was not submission-safe.
This audit prepares a different output contract: Python enumerates exact source
lines as IDs, the LLM chooses one ID or `NONE`, and Python writes the unchanged
line as evidence. The LLM still receives the complete notice; candidate absence
is never interpreted as a negative prediction.

## Frozen candidates

For every nonempty source line, retain an exact candidate if it contains
`실적` and a Korean won expression. The candidate ID is deterministic:
`C{document-order}-{zero-based-line-number}`. This is the broad,
full-coverage INC-038 fact class, not the narrower eligibility-rule predicate.
Candidate text is the full unchanged line, limited only by the competition's
500-character evidence limit: longer lines are represented as unavailable for
selection rather than split or truncated.

## Gate

Report v2/v4 positive coverage where a selectable candidate contains the
gold-provided evidence string, candidate counts, document types, over-500
exclusions, and hard-negative activation. Candidate IDs may be used in an LLM
output experiment only if every v2/v4 positive has at least one selectable
source candidate. This audit makes no binary prediction.
