# N001 native v1 fast20 diagnostic result

작성일: 2026-09-22

결론: **FAIL. holdout/dev200 중단.** 이 실행은 v1-only 실제 Gemma
20회이며 독립 24-item score가 아니다. fast를 중간 gate로 사용해
dev200 전에 출력 의미 계약 결함을 발견했다.

## 결과

- cohort: 고정 fast20, gold v1 positive 3 / negative 17
- calls: 20, finish_reason stop 20, transport invalid 0
- strict parser: invalid 20, U 20, TP/FP/FN 0/0/3,
  U→0 진단 F1 `0.0`
- 저장 response의 state만 별도 감사: Y=0, N=1, U=19,
  TP/FP/FN 0/0/3, F1 `0.0`
- positive/negative unknown: 3/17
- 다른 항목 판정 및 frozen fallback: 없음

strict invalid 20건의 직접 원인은 N/U response에도 모델이 source
quote를 함께 출력했기 때문이다. JSON schema는 `quote`를 string/null로
허용했지만 parser는 Y가 아닐 때 null만 허용했다. 더 근본적으로 system
prompt는 state enum을 제시하면서 `Y=v1의 1 조건 충족`, `N=v1의 0 조건
충족`, `U=불명`이라는 매핑을 명시하지 않았다. `보이지 않는 부분에
조건이 없다고 추정하지 않는다`는 지시와 결합해 모델이 19/20건을 U로
보냈다. 명백한 gold positive `PPS-DEV-049`의 “체육교육학 전공이 있는
대학만” 조항도 N으로 출력했다. 따라서 parser만 느슨하게 해도 품질은
회복되지 않는다.

이 결과는 Gemma v1 능력의 상한이나 source view의 최종 실패를
증명하지 않는다. 입력은 사전 감사와 동일했고 fast20 20/20 fit,
max 10,658 tokens였다. 실패 원인은 **output semantic contract**로
국한된다. 다음 후보는 source view/card/provider/temperature/seed를
고정하고 다음만 명시한다.

1. Y는 카드의 `1 조건`이 충족된 위반, N은 `0 조건`인 비위반,
   U는 제공 후보가 모순되거나 실제로 판단 불충분한 경우다.
2. quote는 Y에서만 exact source substring이며 N/U에서는 null이다.
3. 모든 문서를 scan해 만든 참가자격 후보라는 사실과, 단순히 원문
   전체가 아니라는 사실을 동시에 설명하되 이것만으로 전건 U를
   요구하지 않는다.

새 prompt/schema 계약은 N001 response를 재해석하지 않고 새 version과
새 fast20 호출로 검증한다. N001 responses는
`outputs/clean-exp-n001-v1-fast-diagnostic-v1/fast20/responses/`,
report는 같은 경로의 `run_report.json`에 있다.
