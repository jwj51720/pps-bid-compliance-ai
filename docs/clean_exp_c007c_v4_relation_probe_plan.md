# Clean EXP-C007C v4 relation-only diagnostic probe plan

작성일: 2026-09-21

## 지위

이 실험은 C007B의 native requirement-instance prompt가 실제 Gemma에서 역할·관계를 안정적으로
구조화하는지 확인하는 **diagnostic probe**다. organizer 항목명의 “고시금액 이상”과 dev label의
충돌을 아직 해결하지 않았으므로 완결된 v4 전략이나 canonical 후보로 부르지 않는다.

## 가설

후보별 `role + mandatory + restriction + allowance + necessity` 관측은 기존 단일 `q/r/e/id`보다
참가자격과 평가표·서식을 잘 구분하고, fast20의 v4 FN을 회수하면서 기존 TP를 보존할 수 있다.

- quality base: C005D
- fast20 v4 base: TP 2 / FP 0 / FN 1 / F1 `0.8`
- relation-only 목표: TP 3 / FP 0 / FN 0 / F1 `1.0`
- 다른 23개가 고정이면 fast Macro 기대 상승:
  `(1.0 - 0.8) / 24 = 0.0083333333`

## 통제

- base config: `clean_exp_c005d_v19_dev200_promotion_v1.json`
- owner change: v4 only
- source view/schema/prompt/reducer: C007B에서 사전 검증한 native module
- provider parameters: unchanged
- fast candidate notices/calls: 18/18, overflow 0
- source audit: 374/374 documents, positive 6/6, error 7/7, actual prompt max 13,321
- 다른 23개 label/evidence: byte-identical C005D stored rows

허용 변경은 `layers.views`, `layers.decisions`, `layers.assembly`, `v4_policy`,
`runtime.expected_calls_per_record`뿐이다. 금액 threshold, card, 다른 owner, evidence validator,
provider parameter는 바꾸지 않는다.

## 실행 전 gate

1. fully resolved manifest preflight PASS
2. fast20 task hashes가 C007B label-blind audit과 일치
3. fast20 exact rendered short/attachment/largest/error panel 사람 검토
4. mock 20x49, non-v4 changes 0, evidence validation PASS
5. test suite PASS

## 승격/중단

fast20 paid probe:

- required: invalid 0, non-v4 changes 0, v4 positive evidence valid
- minimum: TP 2 / FP 0 / FN <=1 (baseline 비열화 없음)
- target: TP 3 / FP 0 / FN 0

target을 달성해야 independent holdout20으로 진행한다. minimum만 만족하면 prompt/reducer 관측을
분석하고 자동 승격하지 않는다. FP 증가, TP 감소, invalid 또는 evidence 오류가 있으면 C007C를
중단한다.

holdout target은 TP 1 / FP 0 / FN 0이다. holdout까지 통과해도 relation-only 결과를 곧바로
dev200/canonical로 승격하지 않는다. 동일 저장 observation에 organizer-title threshold reducer를
0-call replay해 두 정책의 차이를 명시한 뒤 다음 결정을 내린다.

