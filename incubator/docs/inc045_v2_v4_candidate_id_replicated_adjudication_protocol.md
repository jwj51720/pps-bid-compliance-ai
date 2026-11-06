# INC-045: Replicated v2/v4 Candidate-ID Adjudication

## Change from INC-042

This repeats INC-042's frozen 36-notice hard-negative cohort, model settings,
complete notice input, complete-law/no-law factor, and two independent repeats.
The sole changed variable is evidence transport:

- INC-042: model generated a free-text quote;
- INC-045: Python enumerates exact selectable source candidate IDs and the model
  returns `evidence_id` from that list or `NONE`.

Python maps a valid chosen ID to its unchanged ≤500-character source line.
There is no whitespace repair, similarity search, or generated quote.

## Candidate and output contract

Candidates are the frozen INC-044 source lines containing `실적` and a Korean
won expression; all v2/v4 dev-positive evidence is covered and no line exceeds
500 characters. The full source notice remains in each request. A candidate
list is evidence selection support, not a candidate-absence classifier gate.

For each item, `위반여부=1` requires an ID; `0` requires `NONE`. An invalid
ID, inconsistent pair, malformed JSON, or missing call is a format failure and
makes that arm unscorable. The four arms are control/law × r1/r2 exactly as in
INC-042.

## Promotion gate

This is still a mechanism cohort. Both law repeats must be fully successful,
each law-minus-matched-control target-macro delta must be non-negative, and the
direction must replicate before any dev-200 escalation. A candidate-ID format
success alone does not establish legal-context benefit or hidden-test utility.
