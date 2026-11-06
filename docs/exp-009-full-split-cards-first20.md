# EXP-009: Full Split + Decision Cards, First 20

## 질문

`data/항목표.json`과 일대일로 연결한 24개 decision card를 실제 system prompt에 모두
넣으면, 법령 RAG 없이도 문구 하나를 곧바로 위반으로 단정하는 false positive를 줄일 수
있는지 확인한다. EXP-008과 동일하게 `full_split_merge`, 대상 문서 evidence 강제,
non-absence OR 및 absence item의 문서별 AND 결합을 사용했다. 차이는 decision card뿐이다.

## 결과

| 실험 | 문맥/판정 정책 | Macro positive-F1 | TP / FP / FN | 양성 예측 | Evidence span F1 | API 비용 |
|---|---|---:|---:|---:|---:|---:|
| 초기 4,000자 | 단일 pass | 0.09028 | - | - | - | - |
| full context | 단일 pass | 0.13214 | 7 / 25 / 15 | 32 | 0.25688 | $0.03369 |
| EXP-008 | strict full split, absence AND | 0.13423 | 7 / 51 / 15 | 58 | **0.35190** | $0.04900 |
| **EXP-009** | **EXP-008 + 24 decision cards** | **0.17312** | **8 / 43 / 14** | **51** | 0.26316 | $0.06099 |

첫 20건의 gold positive는 22개다. EXP-008 대비 macro F1은 **+0.03889**, TP는 1개
증가하고 FP는 8개, FN은 1개 감소했다. 카드 system prompt가 추가되어 prompt token은
383,164→484,388 (+26.4%), 비용은 약 $0.012 증가했다. 생성은 98.3초, 검증 warning은
0건이었다.

## 항목별 변화

실질적인 변화는 다음 항목에 집중됐다.

| 항목 | EXP-008 (TP/FP/FN) | EXP-009 (TP/FP/FN) | 해석 |
|---|---:|---:|---|
| v5 | 1 / 3 / 0 | 1 / 1 / 0 | 지역제한 문구만으로 양성화하던 FP 2개 제거 |
| v8 | 0 / 0 / 2 | 1 / 0 / 1 | 양성 1개를 새로 검출 |
| v13 | 1 / 6 / 0 | 0 / 1 / 1 | FP 5개 제거했지만 기존 TP 1개도 제거 |
| v16 | 0 / 7 / 1 | 1 / 6 / 0 | 부재탐지 양성 1개를 새로 검출 |
| v21 | 0 / 3 / 0 | 0 / 0 / 0 | 공동계약 최소지분 문구 자체를 위반으로 보던 FP 3개 제거 |
| v2, v6, v24 | 0 / 0 / 2, 0 / 0 / 1, 0 / 1 / 0 | 0 / 2 / 2, 0 / 1 / 1, 0 / 2 / 0 | 카드만으로는 새 FP/FN도 생김 |

v3와 v10/v18/v20은 이 표본에서는 변하지 않았고, v11은 FP가 1개 줄었다. 따라서
개선의 핵심은 적용성·예외를 명시한 v5/v13/v21 카드이며, 모든 항목에 균일하게 효과가
있었다고 해석하면 안 된다.

Evidence validity는 두 실험 모두 1.0이다. 다만 EXP-009의 span F1은 0.35190에서
0.26316으로 내려갔다. 문서 위치 안전장치는 유지됐지만, 생성 모델이 인용하는 정확한
범위가 달라진 결과다. 이 실험의 채택 판단은 macro F1뿐 아니라 evidence 품질도 이후
더 큰 표본에서 재확인해야 한다.

## 결론과 다음 단계

decision card는 RAG와 독립적으로 필요한 정책 계층이며, 이 첫 ablation에서는 과잉판단을
줄이는 방향으로 작동했다. 단, 20건과 단일 generation으로는 v13의 recall 저하 및
generation 변동을 분리할 수 없다. canonical 제출 config에는 아직 반영하지 않는다.

다음 실험에서는 이 card를 고정한 채, v5/v13처럼 공식 금액·제품지정·계약법 적용성의
외부 사실이 필수인 항목에만 대회 제공 법령/고시를 선택적으로 제공한다. 카드에 숫자나
예외를 추정해 넣지 않으며, evidence는 계속 공고 원문에서만 추출한다.

## 재현

```bash
.venv/bin/python scripts/build_decision_cards.py
.venv/bin/python scripts/run_experiment.py \
  --config configs/config.exp009-full-split-cards-first20.yaml \
  --dump-inputs
```
