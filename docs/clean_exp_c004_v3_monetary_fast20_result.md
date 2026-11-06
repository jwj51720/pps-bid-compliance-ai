# EXP-C004 v3 monetary relation — fast20 결과

실행일: 2026-09-21

## 결론

점수 가설은 목표를 달성했지만 serialization gate를 통과하지 못해 **INCOMPLETE / HOLD**다.
holdout20과 dev200은 실행하지 않는다.

- output: `outputs/clean-exp-c004-v3-monetary-v1/fast20/`
- specialist calls: 10
- v3 baseline: TP 1 / FP 0 / FN 2 / F1 `0.500000`
- v3 candidate: TP 3 / FP 0 / FN 0 / F1 `1.000000`
- Macro: `0.6791666667 → 0.7000000000`
- 다른 23개 changed cells: 0
- v3 positive without evidence: 0
- response finish reason: 10/10 `stop`
- prompt tokens: 14,915, max 2,884
- completion tokens: 902, max 209
- wall time: 11.821초(OpenRouter이며 evaluator vLLM 근거가 아님)

## 성공한 부분

`PPS-DEV-042`, `051`, `062` 모두 Gemma가 실제 참가자격의 단일 실적금액과 exact source를
올바르게 구조화했다. Python은 각각 `100,000,000`, `300,000,000`, `300,000,000원`으로
검증하고 organizer 입찰추정가격과 엄격 부등식만 계산했다. 결과는 세 건 모두 TP였고 FP는
추가되지 않았다.

이는 기존 r10의 실패 원인 두 가지를 직접 지지한다.

1. 단일 source-id가 qualification과 amount 판단을 동시에 증명해야 했던 provenance 병목.
2. Gemma에게 숫자 비교까지 맡겨 생긴 산술 오류.

## 실패한 gate

후보가 있으나 실제 참가자격 금액이 아니어서 baseline을 유지한 정상 semantic fallback 네 건과
별개로, 두 응답이 local serialization validation에 실패했다.

- `PPS-DEV-165`: expected M01/M02/M03 중 M02를 두 번 출력하고 M03 누락
- `PPS-DEV-169`: expected M01/M02 중 M01을 두 번 출력하고 M02 누락

JSON schema의 `source_id enum + minItems/maxItems`는 배열 길이만 고정할 뿐 source ID의 유일성과
전수성을 강제하지 못한다. 두 응답 모두 provider 기준 schema-valid/finish `stop`이었지만 local
candidate-complete contract는 invalid였다. 따라서 사전 gate `malformed=0`을 만족하지 않는다.

## 판정

점수만 보고 holdout으로 승격하지 않는다. 다음 revision은 source view, prompt 의미, role enum,
reducer, provider parameter를 모두 고정하고 **배열을 candidate-ID keyed object로 바꾸는
serialization-only 실험**이어야 한다. 먼저 실패한 2건을 exact task로 재호출해 중복/누락이
사라지는지 확인하고, 성공할 때만 fast20 전체를 새 schema로 재실행한다.

