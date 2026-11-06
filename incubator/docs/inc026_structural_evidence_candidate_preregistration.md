# INC-026: Structural Evidence Candidate Audit

## Question

Can predeclared item cues select intact source paragraphs/table rows that
contain the labelled evidence, without the arbitrary character-radius windows
used in earlier candidate work? This is a no-API audit. Dev labels evaluate
coverage only and never alter cues or source-unit selection.

## Frozen method

Use the baseline cue definitions from INC-009, which were written from the
organizer item names, notes, and competition description. Split documents only
at their existing blank paragraph boundaries; preserve every raw character and
source offset. A candidate is an entire structural block containing at least
one predeclared cue. There is no length cap, ranking cutoff, neighbor radius,
or candidate-absence prediction rule.

For every non-absence gold positive, locate the exact organiser-provided
evidence substring in the raw source and test whether a candidate structural
block contains that complete substring. Report source-attribution failures
separately from cue coverage. For negative notices, report candidate-notice
rate and structural-block burden; neither is an error rate or prediction.

Some organiser gold-positive rows may have an empty evidence cell. These are
reported separately as unavailable supervision, not as source-attribution or
candidate-coverage failures.

## Gate

The architecture is eligible for a paid active-item pilot only if every
non-absence item with dev positives has at least 90% complete-evidence
coverage, no source-attribution failure, and a coherent family has materially
lower negative burden than the old broad-window audit. Otherwise it is limited
to recall-only attention and cannot suppress a final positive.
