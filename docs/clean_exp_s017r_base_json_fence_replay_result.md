# S017R — base repeat JSON fence 0-call replay 결과

실행일: 2026-09-23

상태: **PASS — fence 복구 뒤에도 final V/E 변화 0**

## 무결성

- LLM calls: 0
- embedding calls: 0
- expected recovered set: `r10/PPS-DEV-21` 1/1
- inner JSON structural equality: PASS
- other 5 responses: unchanged
- repeat diagnostic: r10/PPS-DEV-21 strict-valid/fallback=false
- output:
  `outputs/clean-exp-s017r-base-json-fence-replay-v1/run_report.json`

## 결과

fence 내부 repeat는 원 response와 다음 관측이 달랐다.

- v3 q/x: `N/N → U/U`
- v4 q/r/e: `N/N/Y → U/U/U`
- v23 b: `N → U`

그럼에도 S001-equivalent final row는 변하지 않았다.

- v3: native specialist가 최종 owner라 r10 변화가 덮인다.
- v4: q와 r이 둘 다 확정 Y가 아니므로 양성으로 전파되지 않는다.
- v23: b가 N 또는 U이면 모두 위반 0이다.
- 나머지 r10/B/C24 결과도 동일 final을 유지했다.

최종 수치:

```text
single replacement changed V cells: 0 / 6 tasks
joint replacement changed V cells: 0
joint evidence changes: 0
Macro: 0.8151465658 -> 0.8151465658
```

## 해석

이 결과는 서로 다른 두 큰 source strata의 중앙 token 공고에서 base generation 표면 차이가
typed/reducer/owner routing을 통과해 final label로 전파되지 않았음을 보여준다. 따라서 현재 증거로는
base generation variance를 public-local gap의 우선 원인으로 올리지 않는다.

다만 표본은 2 notices/6 tasks뿐이며, 600개 전체 task나 evaluator INT8 vLLM을 대표하지 않는다.
특히 양성 경계 사례의 disagreement rate를 추정할 크기가 아니다. 관측 0/6의 단순 95% rule-of-three
상한은 약 50%라 매우 느슨하다. “불일치가 없다”가 아니라 “큰 격차를 설명할 직접 증거를 이
micro에서 찾지 못했다”가 정확한 결론이다.

## 다음 행동

추가 base repeat를 넓히기보다 S014에서 population-weighted F1 하락이 가장 컸고, S011에서 wholesale
rollback은 나빴던 v17을 가장 작은 semantic relation 단위로 감사한다. 목표는 Python cross-item
veto를 제거하는 것이 아니라 다음을 분리하는 것이다.

1. 직접계약/<1억에서 제품 적용성·기업범위·제한문구가 같은 requirement에 연결되는가.
2. v10/v11의 오류가 v17 final에 전파되는가.
3. organizer CSV `특이사항`과 실제 구매품의 조건 비교가 LLM에 완결 입력되는가.

dev lexical correction은 만들지 않고 20,000건 source strata와 고정 source sample을 먼저 사용한다.
