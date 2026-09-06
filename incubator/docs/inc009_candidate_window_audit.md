# INC-009: Deterministic Candidate-Window Audit

This no-API experiment changes no model policy. It creates source-offset windows
from predeclared Korean lexical/numeric cue sets derived from organizer item
names, notes, and competition description. Labels are read only after candidate
extraction to measure coverage; they do not choose cues or spans.

Each window records `doc_id`, document type, exact character offsets, matched
cue patterns, and unchanged source text. This makes it usable for final evidence
resolution without an LLM-generated paraphrase.

An item family is eligible for a paid active-family pilot only when every item
with dev positives has candidate recall at least 0.90, its maximum mean window
burden is operationally bounded, and manual inspection confirms that the cue is
not merely a generic label-name echo. A failed family is retained as a
high-recall triage aid only; no candidate absence may suppress a final positive.

## Baseline result and permitted repair

The baseline procedure family had 100% positive candidate recall, but manual
inspection found generic selectors: `입찰참가자격` for v20, bare `%` for v21,
and `제안서` for v22/v23. These terms create broad notice selection rather than
item-specific source attention. INC-009R removes only those generic selectors;
it does not inspect dev labels to add new terms. A procedure pilot remains
blocked unless this repair retains recall while materially reducing the negative
candidate rate and window burden.

## INC-009R result

After removal, v19--v21 retained 100% positive candidate recall. Their negative
candidate rates were 44.85%, 18.97%, and 68.04%, respectively, with mean
candidate-window burdens of 1.98, 2.00, and 3.01. v22 and v23 fell to 60% and
20% recall, so both are excluded from candidate-window judgment experiments.

The refined extractor is eligible only as an attention source for v19--v21. It
cannot be a negative gate: the extractor's candidate absence must never force a
final zero, particularly for the excluded v22/v23 cases.
