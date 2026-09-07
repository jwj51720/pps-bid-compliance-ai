# INC-063: Repeated Joint-Judgment Consensus Pilot

## Hypothesis

Provider/model variability has been observed under nominally identical
settings.  Three independently executed copies of the same complete-notice,
Joint-24 grounded judgment may reduce idiosyncratic false positives without a
dev-tuned rule.  This is a global consensus hypothesis, not a new prompt,
legal card, retrieval policy, or label-specific threshold.

## Design

Use a fixed 48-notice cohort with one hash-selected positive per item plus
hash-selected remaining notices, as in INC-054.  Run the unchanged original
Joint-24 full-notice prompt three times with its source-evidence contract.
Evaluate each raw run, then predeclared aggregations:

- non-absence items: majority vote (at least 2 of 3);
- absence items: majority vote of their absence judgments;
- evidence: take the earliest source-valid evidence among positive member
  runs; no generated evidence is combined or invented.

All three raw prompts, model settings, and the aggregation rule are fixed
before calls.  The result is compared with the mean individual-run Macro F1,
not selected against a post-hoc best run.  A separate all-dev confirmation is
required even if the pilot succeeds.

## Gates

Success requires consensus Macro F1 at least mean raw-run F1 +0.05, no loss of
micro recall, source-valid evidence for every consensus positive, and at most
5% unresolved/format failures.  Failure rejects consensus as a performance
policy; it does not invalidate the per-positive locator evidence transport.
