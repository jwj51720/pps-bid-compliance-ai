# INC-035: v21 Default-Share Rule Composition Audit

## Frozen component

INC-034 fixed a source-preserving, law-default v21 predicate before any
composition: eligible explicit minimum share below 10% under national law or
below 5% under local law; explicit 분담이행 is excluded; all unknowns are zero.
It has no learned weights, dev-derived threshold, model output, retrieval, or
post-hoc exception.

## Audit

Apply that unchanged component to every dev notice and to the organizer's
unlabeled-format corpus. On dev only,
replace **only** `v21/e21` in the immutable INC-018 `single_full` predictions;
the other 23 labels/evidence cells remain byte-for-byte from the artifact.
Validate source evidence and calculate the complete 24-label score. The
unlabeled-format corpus has no labels: report only source validation, reason
counts, and candidate-positive prevalence; do not infer test performance from
its prevalence.

## Gate

The audit is a component feasibility result, not final submission approval.
It passes only if all dev v21 rule positives have valid source evidence, the
exact baseline replacement improves overall Macro F1, and no non-v21 cell is
altered. An unlabeled-format anomaly (missing jurisdiction, malformed source evidence
or an implausibly unvalidated candidate) blocks integration. A later final
policy still requires the same component to be packaged with the shared
pipeline and evaluated against staged submission behavior.
