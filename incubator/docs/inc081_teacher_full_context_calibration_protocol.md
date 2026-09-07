# INC-081: Full-context teacher calibration

## Question

Which legal context lets an external teacher most accurately decide all 24
items when it receives every supplied document and metadata field of each dev
notice?  This is a calibration experiment, not a final inference replacement.

## Fixed conditions

- cohort: all dev-200, with labels withheld from every model message;
- model: `google/gemini-2.5-flash` through OpenRouter;
- source input: complete ordered notice documents, metadata, and dropped-doc
  metadata; no character-prefix policy;
- output: flat 24-label JSON only, so evidence generation cannot reduce label
  capacity;
- temperature: 0; maximum completion: 768; bounded OpenRouter retries;
- evaluator: the local gold labels are read only after request preparation.

## Arms

1. `card_v6`: complete notice plus the archived v6 decision-card legal
   summaries.  It is a historical-comparator arm, not a final policy claim.
2. `official_ledger`: complete notice plus profile-selected item summaries and
   de-duplicated unchanged official-law chunks from the archived ledger.  The
   ledger retains original organizer source selectors and hashes.

## Decision

Choose neither based on an isolated dev macro score alone.  Inspect per-item
precision/recall, whether the gain comes from broad labels rather than a single
rare item, and raw error overlap with EXP-109.  The winner only advances to the
unlabeled casebook pilot if it is schema-stable and offers an interpretable,
non-concentrated improvement or complementary correct cases.  The next stage
then tests whether its self-labeled cases improve *final Gemma* rather than
using teacher labels directly as predictions.
