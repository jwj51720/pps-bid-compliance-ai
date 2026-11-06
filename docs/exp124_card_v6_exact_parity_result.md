# EXP124 — exact organizer-format card v6 paired probe 결과

계획: [exp124_card_v6_exact_parity_plan.md](exp124_card_v6_exact_parity_plan.md)  
configs: `configs/config.exp124a-exact-baseline-paired-fast-panel.yaml`,
`configs/config.exp124b-card-v6-exact-paired-fast-panel.yaml`  
raw artifacts: ignored `outputs/exp-124a-exact-baseline-paired-fast-panel/`,
`outputs/exp-124b-card-v6-exact-paired-fast-panel/`

## 사전 검증

- preflight: control→treatment effective policy 차이는 `prompt.decision_cards_path` 하나뿐.
- mock: 양 arm 20/20 완료.
- exact Gemma tokenizer admission: control 최대 4,206 tokens, treatment 최대 7,118 tokens;
  모두 14,848-token budget 안이며 dev200 전체도 notice당 1 pass다.
- 문서 admission, V/E schema, metadata renderer(`official_lines`), decoder, evidence resolver,
  merge, concurrency는 동일했다.

## 실행

| arm | calls | runtime | parse failure | Macro positive-F1 |
| --- | ---: | ---: | ---: | ---: |
| EXP124A exact no-card control | 20/20 | 179.6초 | 0 | **0.16419** |
| EXP124B + card v6 | 20/20 | 58.4초 | 0 | **0.14683** |

Control의 179초는 `PPS-DEV-042` 한 건의 OpenRouter transport 지연(179.47초) 때문에
발생한 것이며 semantic policy/runtime 평균의 비교 근거로 사용하지 않는다. Treatment는 같은
모델 설정에서 그런 지연이 없었다.

## 무엇이 바뀌었는가

card v6는 positive prediction을 37개에서 20개로 줄였다. 35 changed cells 중 26개가 `1→0`,
9개가 `0→1`이었다. gold 기준 cell 개선은 25개, 악화는 10개였지만, macro positive-F1의
중요한 TP를 지워 여러 항목을 F1=0으로 만들었다. zero-F1 항목의 FP 제거는 해당 항목의 F1을
올리지 못하므로 cell accuracy와 macro-F1이 반대로 움직일 수 있다.

| 항목 | control `(TP, FP, FN, F1)` | card v6 | 영향 |
| --- | --- | --- | --- |
| v1 | (2, 1, 1, .667) | (3, 0, 0, **1.000**) | 실제 개선 |
| v4 | (1, 0, 2, .500) | (0, 0, 3, **0**) | 유일 TP 소실 |
| v13 | (1, 5, 0, .286) | (0, 0, 1, **0**) | FP와 유일 TP 동시 제거 |
| v15 | (0, 1, 1, 0) | (1, 1, 0, **.667**) | 실제 개선 |
| v19 | (1, 1, 0, .667) | (0, 0, 1, **0**) | 유일 TP 소실 |
| v23 | (0, 1, 1, 0) | (1, 5, 0, .286) | recall 회복, FP 과다 |
| v24 | (1, 4, 2, .250) | (0, 1, 3, **0**) | TP 소실 |

v5/v6/v17/v21의 FP는 감소했지만 TP가 없거나 회복되지 않아 macro-F1 이득이 없었다.

## Evidence·형식 분석

| 지표 | control | card v6 |
| --- | ---: | ---: |
| non-absence positive evidence validity | 0.784 (37 cases) | 0.850 (20 cases) |
| gold evidence span F1 | 0.332 | 0.249 |
| exact evidence match | 0.250 | 0.167 |
| parse errors | 0 | 0 |

card가 invalid evidence를 줄인 것은 더 적은 positive를 낸 직접 결과다. gold-positive 중
실제 TP가 사라졌으므로 span/joint quality도 좋아지지 않았다. schema 또는 evidence parser가
성능 하락 원인은 아니다.

## 결정

EXP124B는 사전 승격 기준(+0.02 macro, 최소 세 v의 error 개선, non-regression)을 만족하지
못했다. **card-v6를 exact organizer-format policy의 dev200 또는 submission으로 승격하지 않는다.**

이 결과는 v1/v15 문구만 골라 card를 다시 편집하거나, v4/v13/v19/v24를 dev label에 맞춰
되돌리는 근거도 아니다. 그것은 EXP123과 같은 local overfit 경로다. 다음 실험은 이 card
branch의 미세 수정을 중단하고, current exact no-card control에서 구조적으로 다른 하나의
명시적 hypothesis가 생길 때만 설계한다.
