# EXP242 — validated v5 specialist V-only ablation

작성: 2026-09-14, dev / mac

## 질문

EXP227에서 v4-only V-only는 V/E와 label이 정확히 같았고, EXP241 joint V-only도 v4는
V/E와 같았지만 v5에는 도움이 되지 않았다. 아직 숫자 operand가 완결된 **v5-only**
specialist에서 evidence 동시 생성 부담만 제거한 통제 실험은 없다.

EXP242는 EXP229와 같은 v5-only complete-source input에서 output mode만 V-only로 바꾼다.
목적은 반복 voting이 아니라, v5 label 성능과 completion 부담에 evidence가 미치는 영향을
정확히 분리하는 것이다.

## 통제 정책

- base: `configs/config.exp229-v5-only-threshold-card-fast-panel-c4.yaml`.
- sole allowed change: `prompt.output_mode`.
- active item v5, v12 numeric card, subset profile, readable metadata, organizer semantics,
  all source documents, tokenizer admission, provider/model/seed와 postprocess는 동일하다.
- Python은 label이나 evidence를 생성하지 않는다. 이 단계의 e5 blank는 의도된 label-only
  limitation이다.

## 게이트와 결정 규칙

preflight, exact dev200 admission, short/attachment/overflow rendered review, active-v5
semantic contract, exact mock와 tests를 먼저 통과한다. fast20에서 EXP229의 v5 F1 `.666667`
보다 개선되어야 holdout으로 간다. label이 같거나 나쁘면 별도 evidence locator나 반복
V-only를 만들지 않는다. V-only가 개선될 때만 independent holdout과 source-grounded
evidence 복원을 별도 후속으로 검토한다.

## 사전 검증과 fast20 결과

- preflight는 EXP229 대비 `prompt.output_mode` 하나만 보고했다.
- exact dev200 admission은 200/200 single-pass, 374/374 source documents,
  source/metadata/card/organizer-semantics omission 0, over-budget 0이었다.
- short/attachment/overflow rendered review와 active v5 semantic contract, exact mock,
  49-column validation, 전체 214 tests가 통과했다.
- EXP229 V/E와 EXP242 V-only의 v5 labels는 20/20 전부 동일했다. 양쪽 모두 TP/FP/FN
  `1/1/0`, F1 `.666667`이다.
- completion은 `690 -> 160` tokens로 76.8% 감소했지만 OpenRouter wall time은
  `20.4 -> 20.7s`로 줄지 않았다. parse error는 0이다.
- V-only는 positive evidence validity만 `1.0 -> 0`으로 만들었다.

결정: 정확도 gate를 넘지 못했으므로 holdout/dev200, 반복 V-only, evidence locator를
진행하지 않는다. v4-only EXP227과 v5-only EXP242에서 모두 V-only가 V/E label과 같았으므로,
현재 evidence 출력은 이 두 specialist의 label 병목이 아니다.
