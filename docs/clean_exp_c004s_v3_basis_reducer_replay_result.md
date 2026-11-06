# EXP-C004S v3 basis reducer replay 결과

실행일: 2026-09-21

## 결론

**PASS.** Organizer source에 없는 `SINGLE_CONTRACT` gate를 제거한 0-call replay가 예상한 한
건만 고쳤다.

- output: `outputs/clean-exp-c004s-v3-basis-reducer-replay-v2/`
- calls: 0
- task identity: MATCH
- stored keyed responses: 61 + recovery attempts 2 selected
- invalid responses: 0
- changed label: `PPS-DEV-059/v3 0→1` 한 건
- changed evidence: `PPS-DEV-059/e3` 한 건, exact substring valid
- forbidden/non-v3 changes: 0

| cohort | before v3 | after v3 | Macro before → after |
| --- | --- | --- | --- |
| fast20 | 3/0/0, F1 1.0 | 동일 | .700000 → .700000 |
| holdout20 | 1/0/0, F1 1.0 | 동일 | .430556 → .430556 |
| dev200 | 7/1/1, F1 .8750 | 8/1/0, F1 .941176 | .800980 → **.803738** |

## 해석

`PPS-DEV-059`의 문장은 실제 참가자격으로 통근버스 운행 실적 2억원 이상을 요구한다. Gemma는
역할·mandatory·금액을 모두 맞혔지만 문구에 `단일`이 없어 AGGREGATE로 분류했다. 법령은
실적금액의 비교만 규정하므로, basis가 SINGLE인지 AGGREGATE인지가 v3의 0 조건이 될 수 없다.

저장 observation 중 다른 AGGREGATE 참가자격 세 건은 요구금액이 추정가격보다 작아서 0을
유지했다. 결과가 notice-specific override가 아니라 일반 strict inequality의 결과임을 확인했다.

이 결과로 v3의 남은 오류는 FP `PPS-DEV-137` 하나다. 제안요청서 첨부서식의 실적기준을 실제
참가자격으로 오분류한 role 오류이며, reducer에 문구 rule을 추가하지 않고 독립 FORM-role
검증 실험으로만 다룬다.

