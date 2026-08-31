# EXP-013/014: Decision Cards, Full Dev-200

## 목적과 공통 조건

first-20 결과만으로 card 정책을 선택하지 않도록, 같은 dev 200개에 대해 다음 두 정책을
완전 재실행했다. 두 실행은 Gemma 4 26B A4B IT, 동일 generation 설정, `full_split_merge`,
`strict_document_evidence: true`, `absence_detection_strategy: per_pass_and`를 공유한다.
즉, 문서별 pass의 non-absence 양성은 그 대상 문서의 변경되지 않은 근거 문구가 있을 때만
OR-merge될 수 있고, 부재탐지 항목은 모든 문서 pass에서 부재가 확인될 때만 양성이다.

- **EXP-013**: decision card v1만 사용. 경쟁제품 CSV lookup은 prompt에 주지 않는다.
- **EXP-014**: card v2와 경쟁제품 CSV의 친화형 적용성 문장을 사용. raw status/변수명/코드는
  모델에 노출하지 않으며, 제품문맥을 포함한 실제 prompt 토큰으로 문서 pack admission을 한다.

EXP-014의 제품문맥까지 admission 계산에 포함하도록 수정한 뒤 실행했으며, 따라서 이전
first-20 EXP-012와 달리 pack budget 누락이 없다.

## 결과

| 실험 | Macro positive-F1 | Macro P / R | TP / FP / FN | 양성 예측 | Evidence validity | Evidence span F1 | 입력+출력 토큰 | 실행시간 / 비용 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| EXP-001 초기 4,000자 | 0.22042 | 0.30993 / 0.27555 | 43 / 207 / 110 | 250 | 0.79508 | 0.32211 | - | - |
| EXP-004 기존 adaptive full context | 0.21383 | 0.26126 / 0.33656 | 52 / 273 / 101 | 325 | 0.83228 | 0.36883 | - | - |
| EXP-013 card v1 | 0.17417 | 0.15099 / 0.33209 | 51 / 457 / 102 | 508 | **1.00000** | 0.27458 | 4,455,286 | 834.8초 / $0.44856 |
| EXP-014 card v2 + 제품문맥 | **0.22802** | 0.30101 / 0.27644 | 42 / 91 / 111 | 133 | **1.00000** | 0.36508 | 4,659,174 | 1,305.1초 / $0.46221 |

`Macro positive-F1`은 24개 v 항목의 양성 클래스 F1 평균이며 대회의 핵심 비교 지표다.
EXP-013/014의 evidence validity가 1인 것은 strict document evidence gate 이후 남은 모든
양성 evidence가 원문 substring 검증을 통과했다는 뜻이다.

## 직접 비교와 결론

EXP-014는 EXP-013에 비해 macro F1이 **+0.05385** 올랐다. 핵심 변화는 FP **457→91
(-80.1%)**이고, 이를 위해 TP는 **51→42**, FN은 **102→111**이 되었다. v2의 제품 적용성
카드는 특히 full-split에서 부재탐지를 무분별하게 양성으로 합치는 현상을 줄였다. 반대로
놓친 실제 양성도 늘었으므로, card v2는 정밀도 우선 정책이며 recall 개선은 별도 가설로
검증해야 한다.

이번 비교에서 full-200의 최선은 **EXP-014**다. 초기 4,000자 EXP-001보다 macro F1이
`+0.00760`, 기존 full context EXP-004보다 `+0.01420` 높다. 다만 실험 시점의 코드/프롬프트
정책도 다르므로, 이 수치는 정책 이력 비교이며 단일 변수 ablation으로 과해석하지 않는다.

라벨 수준에서 v2가 v1의 과잉 양성을 크게 낮춘 예는 v10(75→1 FP), v11(70→1),
v16(89→3), v18(84→3), v20(71→1)이다. 동시에 v10/v11/v13/v18의 TP도 줄었으므로,
특정 dev 라벨만 겨냥한 Python 강등 규칙은 도입하지 않는다. 향후 개선은 item-table-linked
card에 대회 제공 법령/고시의 명시 근거를 추가하거나, 제품 적용성별 card를 더 명확히 하는
방식으로만 다룬다.

## 재현

```bash
.venv/bin/python scripts/build_decision_cards.py --version v1
.venv/bin/python scripts/run_experiment.py \
  --config configs/config.exp013-cards-v1-full200.yaml --dump-inputs --fresh

.venv/bin/python scripts/build_decision_cards.py --version v2
.venv/bin/python scripts/run_experiment.py \
  --config configs/config.exp014-product-cards-v2-full200.yaml --dump-inputs --fresh
```

결과물은 각각 `outputs/exp-013-cards-v1-full200/` 및
`outputs/exp-014-product-cards-v2-full200/`에 config, 파생 데이터 스냅샷, prompt input,
예측, 라벨별 지표, runtime/usage를 함께 보관한다.
