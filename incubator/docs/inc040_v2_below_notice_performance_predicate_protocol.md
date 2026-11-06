# INC-040: v2 Below-Notice Performance Predicate Audit

## Legal basis

The organizer-provided 2026-01-08 notice-amount file sets the national
goods/services amount at **230,000,000 won**. The organizer national guideline
states that a manufacturing/service contract below the notice amount must not
restrict competition by performance; the local decree uses the same national
notice amount for its manufacturing/service performance restriction.

## Frozen predicate

The audit is positive only when all are true:

1. raw `입찰추정가격` is below 230,000,000 won;
2. raw `업무구분` is not construction;
3. an unchanged source line contains a performance term, an explicit Korean
   won amount, a lower-bound expression, and an ordinary bidder-qualification
   construction (for example `실적이 있는 자`, `이상인 업체`, `보유한 업체`,
   or `있어야`). A proof/document-submission expression alone is not enough:
   it may describe proposal evaluation rather than entry eligibility.

The amount is the organizer-law value, not a development-derived tuning
parameter. This predicate does not decide v3's one-times ceiling or v4's
specific-performance role. Missing or ambiguous source roles default to zero;
each positive keeps its complete unchanged source line as evidence.

## Gate

All v2 positives must be covered, no negative may be positive, source evidence
must validate, and every positive must have the law-applicable raw metadata.
Otherwise retain only the fact extractor and do not compose a label rule.
