# INC-013: v20 Law Decision-Card Foundation

Hypothesis: v20's zero recall is more plausibly caused by the missing legal
predicate than by token admission or output formatting. A compact card made
only from organizer-provided law can give Gemma the required threshold,
amount, exception, and disclosure facts without introducing a label rule.

This is an offline audit, not a scored model run. It reads only `dev.jsonl.gz`,
`dev_labels.csv` for audit counts, and the organizer-supplied software-business
guideline. It writes an ignored fact card and per-notice cue manifest. The
label is never used to construct a card, cue, or prediction.

The card preserves exact line-numbered source excerpts for: the Appendix 1
thresholds, the amount definition, long-contract and split-procurement
conditions, the notice/RFP disclosure duty, and exception-request context. It
treats `정보화사업여부=미입력` as unknown. It expressly prohibits inferring a
v20 result from metadata, a keyword cue, or amount alone.

Preflight gate for a paid pilot: every dev v20 positive must have at least one
source-document SW-applicability cue, the legal excerpts must be exact and
hashed, and no metadata-only applicability path may exist. If it passes, the
next experiment is a five-positive, matched-negative, v20-active paired Gemma
pilot: same source context/model/seed/schema, control versus this card only.
The card is added to the user message as fixed context and is not evidence.

Promotion rule for that paid pilot: at least 3/5 v20 true positives, no more
than one additional false positive than control, and a gain over the control
v20 F1. Otherwise reject the card and return to source/evidence architecture.

## Result

The preflight gate passed: all 5/5 dev positives had at least one source
SW-applicability cue, while 43/195 (22.05%) negatives had such a cue. All five
positive records had `정보화사업여부=미입력`; metadata-only gating would have
discarded every one. No positive contained an explicit disclosure cue, versus
1/195 negatives, which is consistent with v20 being an absence item rather
than a keyword-detection task.

Decision: promote the card, not its lexical cues, to the preregistered paired
Gemma pilot. The treatment must make Gemma decide applicability and the
absence of the required declaration from the full source; the extractor may
only point to source locations and preserve unknown metadata.
