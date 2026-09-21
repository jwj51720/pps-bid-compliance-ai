# EXP323–326 — 의미 완결 입력에서 V/E와 V-only 재검증

작성: 2026-09-15, dev / mac

## 질문

`decision_cards_v26_semantic_complete.json`, 필요한 human-readable metadata/제품 사실과 모든
tokenizer-admitted 원문을 동일하게 제공할 때 다음 중 어느 출력·검증 구조가 label 성능을
가장 높이는지 비교한다.

1. EXP323: 한 번의 V/E final.
2. EXP324: 한 번의 V-only final.
3. EXP325: untrusted V-only 초안 한 번 뒤, 같은 완결 입력과 전체 원문을 다시 읽는 V/E final.
4. EXP326: 독립 V-only 초안 두 번 뒤, 같은 완결 입력과 전체 원문을 다시 읽는 V-only resolver.

과거 EXP186/187은 카드 v6에서 각각 낮았고, item-local 반복 V-only도 일반화되지 않았다.
이번 재검증의 정당화는 pass wording 변경이 아니라 v26에서 판정 기준을 source-grounded하게
완결한 새로운 공통 입력이다. 이 한 번의 controlled comparison이 실패하면 같은 구조의 pass 수,
vote, majority, wording을 다시 조정하지 않는다.

## 공통 고정 정책

- prompt profile: `complete_fact_v1`.
- cards: `data/derived/decision_cards_v26_semantic_complete.json`.
- product facts: `competition_products_v1.json`, `conditions_and_provenance_v2` renderer.
- metadata: `official_lines_human_v2`.
- context: exact-token adaptive `single`; overflow 때만 ordered packs; 제공 문서 누락 0.
- active items: v1–v24 all-item; item grouping 없음.
- model/provider/temperature/seed/output reserve/concurrency 고정.
- merge: 기존 adaptive source-pack merge. 새 Python label rule, vote, OR/AND consensus 없음.
- postprocess: 네 arm 모두 `frozen_rule_set: null`. EXP123의 v2/v3/v21 Python final-label
  replacement가 model-output 비교를 가리지 않게 한다.

EXP323은 EXP322에서 `postprocess.frozen_rule_set` 제거만 허용한다. EXP324는 EXP323에서
`prompt.output_mode`만 허용한다. EXP325는 EXP323에 staged topology만 추가한다. EXP326은
EXP324에 staged topology만 추가한다.

## evidence 원칙

EXP323/325의 final V/E는 기존 unchanged-substring resolver와 500자 검증을 그대로 쓴다.
EXP324/326은 label-quality diagnostic이라 e를 비운다. V-only가 V/E보다 명확히 우수하기 전에
e 생성 알고리즘을 만들지 않는다. 이후에도 Python은 model이 고른 source span을 연결·검증할
수만 있고, item별 키워드나 법률 판단으로 evidence를 새로 선택해 label을 정당화하지 않는다.

V-only가 승리하면 별도 실험에서 positive item만 대상으로 하는 source-grounded evidence owner를
설계한다. 그 단계가 최종 label을 바꾸지 않고 exact substring만 회수할 수 있는지 먼저 검증한다.

## paid 전 gate

각 arm마다 다음을 완료한다.

1. preflight declared-difference PASS.
2. dev200 exact tokenizer source coverage/provenance 및 call topology 기록.
3. `PPS-DEV-062`, `PPS-DEV-194`, `PPS-DEV-143`의 실제 rendered stage/final message 검토.
4. 각 final source read에서 24-item semantic-input contract PASS.
5. exact mock, parse/recovery, 49열, ID, evidence validation PASS.
6. 실제 실행 직전 resolved config가 해당 arm의 output/staged/postprocess를 선택했는지 재확인.

## 평가와 승격

fast cohort는 `configs/dev_fast_panel_v1.json`의 동일 20건만 쓴다. 네 arm에 대해 macro
positive-F1, v별 TP/FP/FN, positive 수, parse error, evidence validity, prompt/completion token,
실제 source-pack/stage call 수와 remote runtime을 기록한다.

- 한 arm이 단일 best score만 낸 것으로 승격하지 않는다. EXP323 대비 macro와 positive recall,
  치명적 FP 증가를 함께 본다.
- V-only 또는 staged arm이 EXP323보다 개선되지 않으면 holdout으로 확장하지 않는다.
- 개선 arm만 `configs/dev_holdout_panel_v1.json`의 independent holdout20에서 동일 정책으로
  확인한다.
- fast와 holdout 방향이 일치한 arm만 dev200으로 확장한다.
- OpenRouter runtime은 evaluator vLLM 120분 통과 근거가 아니다. call topology가 submission
  가능하지 않으면 quality upper bound와 제출 후보를 분리한다.

이 비교에서 V-only가 이겨도 evidence recovery가 통과하기 전에는 submission-ready가 아니다.
반대로 V/E가 이기면 evidence 후처리를 위해 V-only를 고집하지 않고 V/E 구조를 유지한다.

## Fast20 결과

모든 arm은 같은 fixed fast20, v26 cards, human-readable metadata/조건부 제품 사실과 전체
tokenizer-admitted source를 사용했다. provider parse error와 final recovery는 모두 0이었다.

| EXP | 구조 | Macro positive-F1 | predicted positive | calls | runtime | prompt / completion tokens |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 323 | one-stage V/E | **`.198611`** | 15 | 26 | 527.7s | 502,731 / 17,584 |
| 324 | one-stage V-only | `.102083` | 12 | 25 | 40.6s | 485,897 / 4,600 |
| 325 | V-only draft → V/E final | `.140972` | 14 | 52 | 334.1s | 1,012,247 / 24,941 |
| 326 | V-only draft×2 → V-only resolver | `.092361` | 18 | 77 | 96.5s | 1,497,821 / 14,418 |

EXP325의 저장된 draft 자체는 `.113194`, EXP326의 두 draft는 각각 `.098611`이었다. 즉 좋은
V-only 판단을 resolver가 망친 것이 아니라, 완결 입력을 읽은 V-only 원판정부터 대부분 항목을
0으로 내어 recall이 낮았다. EXP326 resolver는 이를 회복하지 못하고 v22 FP를 6개까지 늘렸다.

EXP323은 non-absence positive evidence validity `.933333`, validation warning 1건이었다.
V-only arm의 빈 evidence warning은 계획된 diagnostic 한계다. EXP324는 약 13배 빨랐지만
label F1이 절반 가까이 떨어졌으므로 evidence 후처리를 설계할 quality gate를 통과하지 못했다.

항목별로 EXP323만 v1 `.8`, v2 `.5`, v3 `.6667`, v4 `.8`, v22 `1.0`, v23 `1.0`을 냈고
나머지 18개 항목은 fast positive를 회복하지 못했다. EXP324는 v4와 v23까지 잃었다. 반복
V-only도 v4를 되살리지 못했다.

## 결정

V-only single/multiple-read와 V-only evidence 후처리 방향은 중단한다. 이번에는 과거 card v6가
아니라 source-grounded v26 완결 입력에서도 같은 방향의 실패가 재현됐다. pass 수, majority,
AND/OR vote, draft wording을 더 조정하지 않는다. 현재 output owner는 V/E가 맞다.

다만 v26 V/E `.198611`은 기존 v10 direct의 **순수 model output** `.198016`과 거의 같다.
v26의 상세 기준이 전체적으로 성능을 파괴했다고 볼 수는 없지만, 정보 완결만으로 recall을
높이지도 못했다. 다음 최소 변화는 기존 fast/holdout/dev200에서 일관되게 이겼던 one-stage
`relation_checklist_after_source_v1`을 v26에 적용해, 추가 호출 없이 원문 직후 관계 대조를
다시 활성화하는 것이다.
