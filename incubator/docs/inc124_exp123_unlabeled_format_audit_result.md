# INC-124 — EXP-123 unlabeled format audit

20,000 organizer-provided unlabeled notices에 대해 model call 없이 frozen v2/v3/v21
predicate의 activation과 evidence format만 검사했다. 이는 prevalence 또는 F1 증거가 아니다.

| Item | Positive count | Rate | Max evidence chars | Invalid evidence |
|---|---:|---:|---:|---:|
| v2 | 170 | 0.850% | 400 | 0 |
| v3 | 82 | 0.410% | 500 | 0 |
| v21 | 9 | 0.045% | 109 | 0 |

초기 scan은 v3 long source line 2건(893/884자)을 발견했다. EXP-123 rule은 trigger를
포함하는 결정적 500-character unchanged source window를 반환하도록 수정했고, 전체 20k
rescan에서 `invalid_evidence_count=0`을 확인했다. Dev200 rule-label equivalence는 긴 line이
없어 그대로 유지된다.

**Decision:** EXP-123 format/runtme guardrail passes. 이 audit은 hidden-test label quality나
public score를 보장하지 않으며, 공개 제출이 그 일반화 검증이다.
