# N007: v2 purchase-inclusive observation fast20 result

작성일: 2026-09-22

## 판정

N007은 **미승격**이다. 고정 fast20에서 TP/FP/FN=3/2/0,
precision 0.60, recall 1.00, F1 0.75였다. frozen L41의 v2
dev200 cell은 F1 1.0이므로 보존 대상이며, N007로 대체하면 안 된다.
fast20 성능은 개발 선별용이며 holdout20/dev200은 실행하지 않았다.
v2 F1 1.0 대비 0.75는 24항목 Macro에서 `-0.25/24 = -0.0104167`
기여에 해당하지만, 서로 다른 평가 범위의 점수를 직접 합산해 전체
실측 점수라고 부르지 않는다.

## 재현·비용

- manifest: `experiments/manifests/clean_exp_n007_v2_performance_fast_v1.json`.
- output: `outputs/clean-exp-n007-v2-performance-fast-v1/fast20/`.
- preflight: `docs/clean_exp_n007_v2_fast_preflight.md`, manifest diff PASS,
  exact task 20/20, 35문서, 191 source spans, token min/max
  2,750/10,497. short/attachment/largest rendered system/user 직접 검토.
- logical/new calls 20/20, OpenRouter wall 404.575초. 저장된 usage 합계는
  prompt 118,833, completion 1,548 tokens, response cost 필드 합계
  USD 0.01323559다. 가장 늦게 저장된 `PPS-DEV-036`은 attempts 2였고,
  response의 마지막 시도 latency만 1.403초로 기록되어 전체 대기시간을
  설명하지 않는다. 이 원격 wall은 evaluator vLLM 추정치가 아니다.
- mock은 별도 `fast20-mock`; mock F1은 성능 점수가 아니다.
- 전체 테스트: 157 passed.

## 오류 분해

| ID | gold→pred | 원인 |
| --- | --- | --- |
| PPS-DEV-058 | 0→1 | 원문 `연구용역을 수행한 경험이 있는` 기관을 참가자격으로 한정하지만, v2의 금액·규모·수량 **실적 문턱**은 없다. Gemma `performance_participation=Y`는 단순 경험과 정량 실적을 혼동했다. |
| PPS-DEV-165 | 0→1 | 제안요청서의 `유사사업수행실적 (6점)` 정량평가 및 실적증명 서식을 입찰 참가자격으로 오인했다. 실제 참가자격 조항은 별도 source span에 있다. |
| PPS-DEV-169 | 0→0 invalid | Gemma quote가 selected span뿐 아니라 제공된 원문 문서 전체에서도 동일한 부분문자열이 아니었다. parser가 `quote_not_in_source`로 0 처리했다. 해당 공고의 gold도 0이므로 FP/FN 수치에는 영향이 없지만 malformed/evidence 지표에는 1건으로 기록한다. |

TP 3건은 `PPS-DEV-062`, `PPS-DEV-042`, `PPS-DEV-069`; 각각
원문 substring evidence가 선택 source span에서 검증됐다. 전체 positive
출력 5건의 evidence validity는 5/5다. parse/evidence invalid는 1/20.

두 FP는 같은 Python threshold나 merge 문제가 아니다. 모두
`performance_participation=Y`, `procurement_role=service`,
`explicit_allowance=N`, `enterprise_rule_applies=N`으로 모델이
관측했고, 입력 가격은 2.3억원 미만이었다. Python은 선언된 conjunction을
그대로 적용했다. 실패 축은 **실적의 역할과 정량 문턱**이다.

## 다음 한 가지 변경 가설

source view, v32 card, schema, provider, threshold 및 parser는 그대로
두고 observation system에서 `performance_participation`의 Y를
`입찰 전 참가자격 조항에 연결된 과거 완료 실적의 명시적 금액·규모·수량
하한`으로 더 엄격히 정의한다. `경험이 있음`만 요구하는 자격과
제안서 정량평가 점수/서식은 N이라는 역할 대조를 명확히 한다.
이는 PPS-DEV-058/165의 개별 문자열을 규칙으로 추가하는 것이 아니라
v2 card에 이미 있는 truth condition을 observation 축에서 명시하는
prompt-only 후보여야 한다. 별도 N008 manifest/plan, rendered review,
semantic contract, mock/preflight를 거친 뒤 fixed fast20을 재측정한다.
fast 개선 시에만 독립 holdout20 → dev200으로 확장한다.

후속 계획: [`clean_exp_n008_v2_participation_axis_plan.md`](clean_exp_n008_v2_participation_axis_plan.md).
