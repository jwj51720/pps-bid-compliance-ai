# INC-062: Per-Positive Source-Line Locator Pilot

## Purpose

INC-060 failed because one Joint-24 response had to decide and ground every
item simultaneously.  INC-062 holds an existing positive decision fixed and
asks a separate call only to locate one unchanged source line for that one
item.  It cannot improve or suppress a label and is not scored for F1.

## Fixed cohort

Use every non-absence positive cell from the immutable INC-041 predictions on
the fixed INC-054 48-notice cohort.  Labels do not select cells.  For each
cell, the locator receives item name, complete numbered source lines, metadata,
and the fixed statement that the upstream judgment is positive.  It outputs
one flat line index or `-1` if it cannot locate a source line.  No law card,
retrieval ranking, or source truncation is added.

## Measurements

Report source-ID validity, rate of `-1`, 500-character eligibility, output
completion, and cost.  It does not claim semantic evidence correctness merely
because a source line exists.  A later manual/audited semantic alignment gate
would be needed before labels use locator outputs.

Advance requires at least 95% valid nonnegative source IDs and no completion
above the 128-token single-index reserve.  Failure rejects separate locator
calls as a feasible submission evidence transport.
