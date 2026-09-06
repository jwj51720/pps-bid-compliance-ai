# INC-019: v10--v18 Product/Procurement Family Matrix

This audit acts on the nine-item product/procurement family selected by the
global INC-018 error atlas. It resolves organizer-provided ten-digit
세부품명번호 from both metadata and documents against the organizer's official
competition-product CSV, preserving `matched`, `not_matched`, and `unknown`.
It separately records source locations for direct production, small-business,
small-and-medium-business, competition-product, and distribution-exception
language, plus raw amount and contract metadata.

No fact or cue is a prediction. In particular, missing code is unknown rather
than not-applicable, a matched product does not establish a violation, and a
source cue does not establish the legal amount/exception predicate. The audit
uses dev labels only to report coverage by item.

The paid follow-up is allowed only if the matrix reveals a meaningful,
auditable applicability separation across the family. It must use one frozen
family card and joint-24 global context; nine independent item prompts would
repeat the local-experiment failure mode.

## Result

The matrix rejects a single v10--v18 family card. Exact competition-product
matching does not cover the family: v10 positives match 1/7, v14 1/8, v16
0/6, and v18 0/7; many are legitimately `unknown` because no exact code is
available. Conversely, small-business language is near-ubiquitous in negatives
(169--176 of 192--194 across the items), so it cannot establish a violation
predicate. v13 has the strongest exact-match signal (4/6 positives) but still
46/194 matched negatives, consistent with INC-018's 115 false positives.

Decision: do not add one family-wide product card or a product-code gate. The
global taxonomy should instead split into: competition-product compliance
(v10--v13, with exact match as an unknown-preserving fact); general-product
amount/exception compliance (v14--v18); and the remaining qualification,
procedure, and cross-source families. This is a design finding, not a scored
policy promotion.
