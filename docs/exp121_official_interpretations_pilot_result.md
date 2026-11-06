# EXP121 공식 해석 card 대조 pilot 결과

## 결론

EXP121B의 v9·v13 공식 해석 card는 승격하지 않는다. 30건 paired pilot에서 목표
positive를 하나도 추가로 잡지 못했고, v13에서 새 false positive 하나를 만들었다.
전체 macro F1도 control 0.22335에서 treatment 0.17103으로 낮아졌지만, 두 arm 간
목표 외 항목의 출력도 다수 달라져 이 전체 차이를 card 두 문장만의 인과효과로
해석하지 않는다.

이 결과는 공식 해석 자체가 틀렸다는 뜻이 아니다. Gemma가 현재 4,000자 단일 호출
구조에서 해당 기준을 실제 판정 행동으로 전환하지 못했다는 증거다. 이 branch에서
추가 card 문구 보정이나 dev200은 수행하지 않는다.

## 가설과 통제

- Control: [EXP121A config](../configs/config.exp121a-card-v6-official-panel.yaml),
  `decision_cards_v6`.
- Treatment: [EXP121B config](../configs/config.exp121b-official-interpretations-panel.yaml),
  v9·v13만 공식 운영 답변과 정합시킨 `decision_cards_v8_official_interpretations`.
- cohort: 30건. 고정 fast-panel 20건과 v9/v13 positive를 함께 둔 진단 panel이다.
  label은 cohort 구성·평가에만 사용했으며 card 문장에는 사용하지 않았다.
- 동일 Gemma, decoding, 4,000자 single context, V/E schema, metadata/product context,
  merge 정책을 유지했다. preflight는 control에 선언되지 않은 정책 변경이 없고,
  treatment에는 `prompt.decision_cards_path` 하나만 바뀐 것을 확인했다.
- 두 config 모두 exact runner의 mock을 통과했다. prompt preview 도구도 실제 pipeline을
  거치도록 수정해, treatment prompt가 v9/v13 card 두 항목만 달라짐을 확인했다.

## 결과

| arm | macro positive-F1 | joint positive quality | evidence-valid rate |
|---|---:|---:|---:|
| EXP121A control | 0.22335 | 0.32527 | 0.68750 (22/32) |
| EXP121B treatment | 0.17103 | 0.27702 | 0.68571 (24/35) |

실행 artifact는 ignored output 아래의
`outputs/exp-121a-card-v6-official-panel/` 및
`outputs/exp-121b-official-interpretations-panel/`에 있다. Control은 약 45초,
treatment는 한 OpenRouter 요청의 재시도로 약 317초가 걸렸지만 30건 모두 완료했고
JSON parse 실패는 없었다.

### 목표 항목 대조

| 항목 | gold positive | control TP / FP / FN | treatment TP / FP / FN | 판정 |
|---|---:|---:|---:|---|
| v9 | 6 | 0 / 0 / 6 | 0 / 0 / 6 | 변화 없음 |
| v13 | 6 | 0 / 0 / 6 | 0 / 1 / 6 | 새 FP 1건 |

v13의 변경은 `PPS-DEV-052`다. gold v13은 0, control은 0, treatment는 1이었다.
공고에는 중소기업·소상공인 확인서 문구가 있으나 metadata의 `조항호내용`은
`[판로지원법 시행령] 중기업,소기업,소상공인 제한`이다. treatment는 경쟁제품
적용대상 확인 없이 그 문구에 과잉 반응했다. 이 사례는 “소기업/소상공인 문구”만으로
v13을 1로 만들면 안 된다는 card의 의도와 반대이므로 승격 불가다.

v9의 여섯 gold positive(`PPS-DEV-09`, `-12`, `-23`, `-050`, `-051`, `-052`)는 양 arm
모두 0이었다. 그중 `-09`, `-12`, `-23`은 gold evidence가 각각 특정 chipset,
제조사·모델명, DJI 배터리 요구로 구체적이지만, 새 문구는 이 양상을 전혀 바꾸지
않았다. 즉 이 panel에서는 v9 기준의 짧은 재서술이 Gemma의 recall 병목을 해소하지
못했다.

## 해석과 다음 경계

1. 공식 운영 답변은 [registry](official_interpretations_v1.md)에 provenance로 보존한다.
   그러나 이 두 항목을 더 길게·더 강하게 쓰는 card 실험은 하지 않는다.
2. 작은 panel의 전체 F1 차이는 목표 외 cell도 바뀌는 원격 inference 변동을 포함한다.
   따라서 효과 판정은 macro 하나가 아니라 목표 item TP/FP/FN으로 했다.
3. E0 원문 관측성 audit와 이번 결과를 함께 보면, 다음 큰 탐색은 raw law/RAG 또는
   항목별 문구 누적이 아니라 **Gemma가 실제 공고의 trigger를 안정적으로 읽게 하는
   실행 단위·표현·self-label 활용의 구조적 가설**이어야 한다. 새 방향도 source
   coverage, prompt diff, small paired pilot을 통과하기 전에는 dev200·제출로 확대하지
   않는다.
