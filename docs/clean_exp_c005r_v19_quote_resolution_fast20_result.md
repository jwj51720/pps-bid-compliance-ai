# EXP-C005R v19 quote resolution fast20 결과

실행일: 2026-09-21  
결론: **PASS — unchanged-policy independent holdout20 승인**

## 결과

C005의 저장 task/response 17개를 새 provider call 없이 replay했다.

- output: `outputs/clean-exp-c005r-v19-quote-resolution-replay-v2/`
- provider calls: 0
- stored responses replayed: 17
- task hash identity: 17/17 MATCH
- invalid responses: 14 → 0
- candidate 없는 baseline fallback: 3
- unresolved positive evidence fallback: 0
- non-v19 changed cells: 0
- v19 positive without evidence: 0
- response content 변경: 0

| metric | C004S / incomplete C005 | C005R |
| --- | ---: | ---: |
| v19 TP / FP / FN | 0 / 0 / 1 | **1 / 0 / 0** |
| v19 F1 | 0 | **1.0** |
| fast20 Macro | .700000 | **.741667** |

036의 최종 evidence는 다음 실제 원문 substring이며 500자 이하이다.

```text
공급업체의 경우 당해 물품 제조사의 정품인증서 및 A/S확약서를 전자입찰서 제출 마감일
전일까지 보유하고, 계약체결 후 수요기관에 제출하여야 합니다.
```

## quote resolution audit

40 candidate observation의 quote 상태는 다음과 같다.

- `BYTE_EXACT`: 18
- `WHITESPACE_UNIQUE`: 5
- `NO_MATCH`: 17
- `AMBIGUOUS_MATCH`: 0

`NO_MATCH` 17개는 `N/A`, `UNKNOWN`, 요약 등이며 모두 reducer의 negative candidate였다. Label
계산에는 사용되지 않았고 diagnostic에는 그대로 남았다. 유일한 positive 036은
`WHITESPACE_UNIQUE`였으며 공백을 제외한 모든 문자가 일치하고 candidate 안에서 한 번만
발견되어 원문 offset으로 역매핑됐다.

Python은 semantic field를 수정하거나 phrase로 v19를 정하지 않았다. C005의 unchanged
predicate가 positive라고 판정한 뒤에만 evidence를 resolve했다. 공백 외 수정, 유사도, 생략부호,
복수 match는 허용하지 않는다.

## 원 C005 호출 audit

C005 fast provider run 자체는 17 calls, 38.572초, prompt/completion tokens
`63,193 / 7,810`, 최대 `6,553 / 1,026`이었다. 이는 OpenRouter 관측이며 evaluator vLLM runtime
근거가 아니다. C005R은 새 호출과 token 소비가 0이다.

## 승격 판정

사전 fast gate `TP>=1, FP<=1, invalid=0, non-v19 changes=0`을 모두 만족했다. 따라서 다음은
prompt, schema, reducer, quote resolver, provider parameters를 바꾸지 않은 independent holdout20만
허용한다. Holdout의 C004S v19 기준은 positive 0, FP 1이며 C005R 정책은 FP=0 목표, FP<=1
비열화 한계를 지켜야 한다.
