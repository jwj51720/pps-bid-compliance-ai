# EXP-012: Product Applicability Decision Cards v2, First 20

## 질문과 방법

EXP-011의 친화적인 경쟁제품 조회 문맥은 유지하되, 그 해석을 공통 prompt 지시가 아니라
item-table-linked card에 넣었다. `decision_cards_v2.json`은 v10~v18 중 경쟁제품/일반제품
전제가 필요한 항목에 다음 일반 원칙을 명시한다.

- 경쟁제품 전제(v10/v11/v13): 경쟁제품 적용대상 확인이 먼저 필요하다.
- 일반제품 전제(v12/v14~v18): 제공 고시에서 경쟁제품으로 확인된 경우 일반제품 위반으로
  판단하지 않는다.
- 조회가 확인 불가인 경우에는 어느 제품군도 추측하지 않는다.

이는 dev ID나 라벨을 대상으로 한 Python 강등 규칙이 아니다. 대회 제공 CSV와 공고
metadata의 관계를 24개 항목 카드 중 제품분류가 법적 전제인 항목에 일관되게 적용한
prompt policy다. EXP-009와 같은 strict full split·absence AND·Gemma 설정으로 첫 20건을
재호출했다.

## 결과

| 실험 | Macro positive-F1 | TP / FP / FN | 양성 예측 | Evidence span F1 | 비용 |
|---|---:|---:|---:|---:|---:|
| EXP-009: decision cards v1만 | **0.17312** | 8 / 43 / 14 | 51 | 0.26316 | $0.06099 |
| EXP-010: v1 + raw product fact | 0.14028 | 7 / 51 / 15 | 58 | 0.18324 | $0.05431 |
| EXP-011: v1 + friendly product context | 0.09881 | 6 / 75 / 16 | 81 | 0.17253 | $0.08972 |
| EXP-012: **v2 cards + friendly context** | 0.14583 | **6 / 9 / 16** | **15** | **0.29571** | $0.05434 |

EXP-012는 EXP-009보다 macro F1이 -0.02728이므로 현재 optimal을 교체하지 않는다. 그러나
FP는 43→9(-79.1%)로 크게 줄었고 evidence span F1도 가장 높다. 카드의 제품 적용성
지침이 부재탐지 과잉판단을 실제로 억제했다는 신호다.

반대급부는 FN 증가다. 특히 v16의 TP 1건이 사라졌고, v3와 v8에서도 각각 TP 1건을
잃었다. v10/v11/v18/v20 FP는 모두 0이 되었지만, 그 항목군의 first-20 gold positive를
찾지는 못했다. 따라서 이 정책은 high-precision variant로 보관하되, 현재의 card-v1
full-split 정책보다 낫다고 결론 내리지 않는다.

## 입력 검토

모델이 받은 실제 text는 `--dump-inputs-markdown`으로 별도 저장했다. JSONL transport
wrapper 대신 system message와 user message만 Markdown fenced block에 담는다. 예시 공고
PPS-DEV-01(경쟁제품 확인)과 PPS-DEV-02(고시 exact-match 없음)는
`outputs/exp-012-product-cards-v2-first20-mock/input_examples.md`에서 확인할 수 있다.

## 재현

```bash
.venv/bin/python scripts/build_decision_cards.py --version v2
.venv/bin/python scripts/run_experiment.py \
  --config configs/config.exp012-product-cards-v2-first20.yaml \
  --dump-inputs --dump-inputs-markdown --fresh
```
