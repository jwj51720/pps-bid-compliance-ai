# INC-073 Result: e-prime Hybrid

All 120 calls parsed.  The direct full-notice control was paired with an
e-prime extractor and an e-prime-only adjudicator; `null` e-prime cells used
the direct result rather than being set to zero.

| Repeat | Direct target Macro F1 | Hybrid target Macro F1 | Delta | Positive e-prime coverage | Nonempty e-prime rate |
|---|---:|---:|---:|---:|---:|
| r1 | 0.37713 | 0.27750 | -0.09963 | 55.56% | 38.64% |
| r2 | 0.40390 | 0.40770 | +0.00380 | 44.44% | 31.82% |

Cost was `$0.08070`, under the `$0.45` ceiling.

## Decision

Reject the one-call joint e-prime extractor as a decision route.  The safety
fallback prevented `null` from becoming an automatic negative, but it cannot
repair an extractor that emits a nonempty incomplete summary and then causes a
wrong e-prime-only judgment.  Positive coverage below 56% also fails the
predeclared coverage gate; the two score deltas are not repeat-safe.

## What changed in the search map

This rules out both broad ways of injecting the legal essence currently
available: direct all-item judgment (INC-072) and a single compressed all-item
e-prime output (INC-073).  It does **not** rule out source-grounded semantic
fact extraction as an attention aid, but any successor must isolate a small,
homogeneous item family and measure fact completeness before using its output
to decide labels.  It may not use a missing extraction as a negative gate or
use BGE-ranked fragments as a decision condition.
