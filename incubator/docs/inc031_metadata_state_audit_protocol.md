# INC-031: Metadata-State Deterministic-Rule Audit

## Purpose

Repeated law-context prompting reduced false positives but could not recover
recall. This no-API audit asks a prior question: for which items, if any, does
the organizer-provided metadata expose a stable *legal applicability state*
that could later support a deterministic fact—not an automatic label?

## Frozen representation

For every notice, record exactly these organizer metadata fields without
normalization or learned grouping:

- `적용계약법`, `업무구분`, `계약방법`, `낙찰방법`;
- `지역제한여부`, `제한지역코드목록`, `업종제한여부`, `면허업종제한목록`;
- `공동도급구성방식`, `조항호내용`, `정보화사업여부`; and
- raw `입찰추정가격`, raw `배정예산금액` presence only (not a numerical
  threshold or bin).

The audit considers predeclared semantic state families: procurement regime,
restriction flags, joint-contract form, and organizer clause text. It reports
for every v1--v24 the exact-state support, positive/negative mixture, and
whether a state appears exclusively in one label class in dev. Raw amounts are
not binned; any later threshold must come from a cited law, not dev values.

## Guardrails and decision

This audit never emits predictions, trains a classifier, chooses a state based
on F1, or treats a dev-exclusive state as a rule. A useful result requires a
state family with broad positive coverage **and** a documented organizer-law
predicate explaining why the state is legally relevant. Mixed states reject a
metadata-only rule for that family.

Any paid follow-up must use the state only as a rendered applicability fact for
one independently justified item family, include a repeat arm before
escalation, and retain full source-document evidence. It may not auto-label
unseen notices by a dev-frequency table.
