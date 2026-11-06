# INC-034: v21 Default Minimum-Share Predicate Audit

## Legal basis and scope

This is a deterministic diagnostic for one fully observed predicate shape, not
a trained classifier. The organizer sources state a default minimum share of
10% for national 공동이행, while the local Joint Contract Operating Guideline
states 5% and separately exempts 분담이행 from a minimum share requirement.
The task's v21 item is `공동 5% (10%)`.

The diagnostic uses only:

1. source line with an explicit `최소 지분율`/`최소 참여지분율`/`계약참여
   최소지분율` and a numeric percent;
2. organizer metadata `적용계약법`; and
3. organizer metadata/document-declared joint form, excluding explicit
   `분담이행` from positive eligibility.

It emits **unknown/zero** if a percentage cannot be tied to a minimum-share
phrase, if the joint form is 분담이행, or if the jurisdiction is missing. It
does not use document silence, a character window, dev-derived threshold, or
any model output. Its evidence is the unchanged source line.

## Fixed default predicate

- national: explicit eligible minimum share `< 10%`;
- local: explicit eligible minimum share `< 5%`;
- explicit 분담이행: no automatic violation.

This uses the legal default only. It does not claim to resolve a document that
expressly describes an authorized statutory adjustment or a construction-only
exception; those cases are retained for review rather than predicted positive.

## Gate

The first audit runs all dev notices and reports coverage, TP/FP/FN, evidence
validity, every unknown, and every source exception. A future policy candidate
requires 100% v21 positive coverage, zero false positives, and no excluded
exception that is a gold positive. If it passes, a fresh test-style robustness
audit over unlabeled notices and a submission-parity integration plan are still
required; this audit alone does not alter the 24-label baseline.
