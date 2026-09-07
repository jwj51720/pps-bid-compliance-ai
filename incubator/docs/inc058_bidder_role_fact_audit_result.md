# INC-058: Bidder-Role Fact Audit Result

The proposed common predicate required an unchanged source line to explicitly
express bidder eligibility, exclude evaluation wording, and additionally carry
institution/performance (v4) or regional anchor (v7).  It has low negative
activation but unacceptable positive loss:

| Item | Positive recall | Negative activation |
|---|---:|---:|
| v4 | 0/6 (0.0%) | 0.5% |
| v7 | 2/7 (28.6%) | 7.3% |

**Reject.**  Explicit bidder-role phrasing is not a complete observable fact
for these legal violations; requiring it would encode false negatives.  Do not
relax the cue list by examining missed examples, because that would become
wording-specific dev tuning.  No v4/v7 deterministic predicate or targeted
LLM prompt follows from this result.
