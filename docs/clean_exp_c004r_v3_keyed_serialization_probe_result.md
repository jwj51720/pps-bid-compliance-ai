# EXP-C004R v3 candidate-keyed serialization probe 결과

실행일: 2026-09-21

## 결론

**PASS.** EXP-C004에서 candidate ID 중복·누락이 발생한 두 건을 candidate-keyed object schema로
재호출했으며 두 응답 모두 전수성·유일성·local parse를 통과했다. 의미 결과도 C004와 동일했다.

- output: `outputs/clean-exp-c004r-v3-keyed-serialization-probe-v11/`
- calls: 2 new / 2 total
- finish `stop`: 2/2
- keyed response valid: 2/2
- C004 final v3/e3 동일: 2/2
- wall time: 9.243초(OpenRouter이며 evaluator vLLM 근거가 아님)

## 응답별 결과

| notice | required keys | returned keys | local valid | final |
| --- | --- | --- | --- | --- |
| PPS-DEV-165 | M01/M02/M03 | M01/M02/M03 | yes | v3=0, C004와 동일 |
| PPS-DEV-169 | M01/M02 | M01/M02 | yes | v3=0, C004와 동일 |

두 건 모두 실제 참가자격 금액 observation이 아니라 평가·서식 후보로 분류되어 semantic
fallback으로 baseline 0을 유지했다. 이것은 malformed가 아니라 의도한 보수적 정책이다.

## 다음 gate

이 결과는 2건 serialization probe일 뿐 fast20 성능 결과가 아니다. source view, role semantics,
strict threshold, reducer, provider parameter를 고정한 별도 full-fast manifest로 후보 공고 10건을
전부 keyed schema로 새로 호출한다. 그 실행에서 v3 TP >= 2, FP=0, invalid response=0을 다시
통과해야 holdout20으로 승격한다.

