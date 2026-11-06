# EXP-011: Friendly Competition-Product Context, First 20

## 질문과 방법

EXP-010의 raw lookup JSON(`status`, code arrays, doc IDs)을 Gemma에 그대로 주는 대신,
Python의 `format_competition_product_context()`가 다음 의미만 한국어로 전달하게 바꿨다.

- 경쟁제품으로 확인됨: 확인된 세부품명만 나열
- 경쟁제품으로 확인되지 않음: metadata 품명이 고시에 정확 일치하지 않음
- 확인 불가: 정확 대조 식별정보가 없음

모든 경우에 v10/v11/v13에만 적용하고, 근거문구가 아니며 v16/v18의 일반제품 전제로 쓰지
말라고 지시했다. CSV exact matching, decision card, full split, strict source evidence,
absence AND, 모델 및 first-20 표본은 EXP-010과 같다.

## 결과

| 실험 | Product context 표현 | Macro positive-F1 | TP / FP / FN | 양성 예측 | Evidence span F1 | 비용 |
|---|---|---:|---:|---:|---:|---:|
| EXP-009 | 없음 | **0.17312** | **8 / 43 / 14** | 51 | **0.26316** | $0.06099 |
| EXP-010 | raw JSON fact | 0.14028 | 7 / 51 / 15 | 58 | 0.18324 | $0.05431 |
| EXP-011 | 친화 한국어 context | 0.09881 | 6 / 75 / 16 | 81 | 0.17253 | $0.08972 |

친화 표현은 raw JSON보다 읽기 쉬운 입력을 만들었지만, 성능상으로는 추가 악화됐다.
EXP-009 대비 FP가 +32, macro F1은 -0.07431이다. 비용도 completion 증가 때문에 가장 컸다.

## FP 원인

75 FP 중 69개(92.0%)가 부재탐지 항목이다.

| 항목 | EXP-009 FP | EXP-011 FP |
|---|---:|---:|
| v10 | 7 | 14 |
| v11 | 6 | 14 |
| v16 | 6 | 13 |
| v18 | 7 | 14 |
| v20 | 7 | 14 |

친화 context의 “경쟁제품으로 확인되지 않았거나 확인할 수 없으면 … 위반으로 판단하지 말라”는
v10/v11에만 해당하는 적용성 조건이지만, full-split의 문서별 부재 판정·AND 결합과 모델
수준에서 안정적으로 분리되지 않았다. 특히 제품 조회와 관련 없는 v16/v18/v20까지 동시에
양성화된 것이 확인된다. 따라서 자연어 표현 자체의 품질 문제가 아니라, 24개 항목을 한
호출로 판정시키면서 prompt instruction으로 부재탐지 적용성을 제어하려 한 구조의 한계다.

## 결론

`competition_product_fact → friendly context` 계층은 입력 가독성·감사 가능성을 위해 보존한다.
그러나 친화 context를 현재 24항목 전체 prompt에 활성화하는 정책은 채택하지 않는다.

경쟁제품 CSV를 성능에 쓰려면 다음 단계는 prompt wording 재시도가 아니라 item-level
결정적 적용성 처리다. 실제 Gemma 호출과 evidence 검증은 그대로 유지하되, `not_matched`인
명시 metadata 코드가 있는 경우 v10/v11/v13을 Python에서 0으로 강등하는 후보를 별도
ablation해야 한다. `unknown`에는 이 규칙을 적용하지 않는다. 이는 CSV가 제공하는 확실한
negative fact만 쓰며, 코드가 없다는 사실을 비경쟁제품으로 오인하지 않는다.

## 재현

```bash
.venv/bin/python scripts/run_experiment.py \
  --config configs/config.exp011-friendly-competition-context-first20.yaml \
  --dump-inputs --fresh
```
