# INC-075 Result: Announcement-Only Attention

INC-074's evidence attribution gave a structural reason to test v7/v23:
every positive organizer evidence substring is in the announcement.  It did
not imply that an announcement-only judgment would be better.  The paired
test confirms that distinction.

| Repeat | Full-document Macro F1 | Announcement-only Macro F1 | Delta |
|---|---:|---:|---:|
| r1 | 0.16667 | 0.14286 | -0.02381 |
| r2 | 0.12500 | 0.47619 | +0.35119 |

All calls and source evidence validation succeeded; total cost was `$0.13834`.
The r2 gain is one v7 true-positive recovery in a cohort containing only one
v7 anchor.  It does not repeat in r1.  v23's false-positive behavior does not
improve in either repeat.

**Decision:** reject announcement-only attention as a predictive policy.  Keep
the document-topology audit only for evidence transport and future scheduling;
the location of organizer evidence is not sufficient evidence that other
documents should be hidden from the legal judgment.
