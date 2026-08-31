# EXP-010: Decision Cards + Exact Competition-Product Facts, First 20

## 질문과 방법

대회 제공 `중기부고시_경쟁제품_세부품명.csv`의 `세부품명번호`를 정적 index로 변환하고,
공고 metadata의 `세부품명번호목록` 및 문서에 명시된 10자리 세부품명번호를 CSV와 **exact
match**했다. 유사도·임베딩·외부 데이터는 사용하지 않았다.

공고별 조회 fact는 다음 세 상태 중 하나다.

- `matched`: 하나 이상의 명시 코드가 CSV에 있음
- `not_matched`: metadata에 명시 코드가 있지만 CSV에 없음
- `unknown`: metadata 코드가 없음

각 full-split pass의 user message에 같은 fact를 넣고, v10/v11/v13에는 `matched`일 때만
경쟁제품 적용성을 인정하며, v16/v18의 일반제품 전제에는 `matched`를 쓰지 말도록
지시했다. CSV fact는 evidence가 아니므로 제출 근거는 계속 대상 source-document
substring만 허용했다. EXP-009와 context/카드/merge/모델 조건은 동일하다.

## 사전 검증

제공 CSV에서 유효한 세부품명번호 615개를 `data/derived/competition_products_v1.json`으로
생성했다. 첫 20건의 조회 결과는 `matched` 7건, `not_matched` 5건, `unknown` 8건이었다.
41개 full-split pass 모두 product fact를 포함했고, Gemma tokenizer 기준 최대 input은
26,594 token으로 30,268-token prompt budget을 넘지 않았다.

## 결과

| 실험 | Macro positive-F1 | TP / FP / FN | 양성 예측 | Evidence span F1 | API 비용 |
|---|---:|---:|---:|---:|---:|
| EXP-009: cards | **0.17312** | **8 / 43 / 14** | 51 | **0.26316** | $0.06099 |
| EXP-010: cards + exact product fact | 0.14028 | 7 / 51 / 15 | 58 | 0.18324 | $0.05431 |

이 최초 주입 방식은 채택하지 않는다. macro F1은 -0.03284, FP는 +8, TP는 -1로
악화됐다. 모든 항목을 한 번에 생성하는 Gemma prompt에 product fact를 추가한 것만으로는
v10/v11/v13의 적용성 gate가 결정적으로 실행되지 않았고, 관련 없는 항목에도 generation
변동을 유발했다.

| 눈에 띄는 변화 | EXP-009 → EXP-010 |
|---|---|
| v5 | FP 1→0 (개선) |
| v15 | TP 0→1 (개선) |
| v1 | TP 1→0, FP 0→1 (악화) |
| v8 | TP 1→0 (악화) |
| v10/v11/v16/v18 | FP가 각각 1~2개 증가하거나 유지 |

`not_matched`였던 PPS-DEV-19에서 v13 FP가 제거된 것은 기대한 방향의 사례다. 그러나
PPS-DEV-18에서는 반대로 v13 FP가 새로 생겼고, `unknown` 공고에서도 부재탐지 FP가
증가했다. 즉 `status` 설명을 prompt에 넣는 것만으로는 item-specific policy enforcement가
되지 않는다.

## 결론

CSV exact match 자체는 재현 가능하고 향후 반드시 유지할 가치가 있다. 다만 다음 실험은
CSV fact를 모든 24개 판정의 자유 텍스트 보조정보로 쓰면 안 된다. v10/v11/v13과 v16/v18에
대해 먼저 Python에서 `matched/not_matched/unknown`별 **허용되는 최종 상태**를 명시한
결정적 gate를 만들고, `unknown`은 경쟁제품이 아님으로 단정하지 않는 별도 경로로 처리해야
한다. 그 gate는 모든 공고에서 실제 Gemma 호출을 계속 수행하고, evidence 규칙을 바꾸지
않는 범위에서만 적용한다.

## 재현

```bash
.venv/bin/python scripts/build_competition_product_index.py
.venv/bin/python scripts/run_experiment.py \
  --config configs/config.exp010-full-split-cards-products-first20.yaml \
  --dump-inputs
```
