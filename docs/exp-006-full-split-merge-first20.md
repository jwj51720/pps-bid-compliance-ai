# EXP-006: First-20 Full Split-and-Merge

## 질문

문서가 길 때에만 분할하는 adaptive full-context 대신, 공고의 각 실제 source
document를 독립적으로 판정하고 OR-merge하면 앞 20개 DEV 공고의 성능이 좋아지는가?

## 통제 조건

세 조건 모두 `PPS-DEV-01`부터 `PPS-DEV-20`까지 같은 20개, 같은 baseline prompt,
metadata, paid `google/gemma-4-26b-a4b-it`, temperature 0, seed 20260826,
2,500 completion-token reserve를 사용했다. 법령 reference는 넣지 않았다.

| 조건 | 문서 전달 방식 | Macro positive-F1 | Evidence span F1 | TP / FP / FN |
|---|---|---:|---:|---:|
| 4,000자 historical | 첫 4,000자 cap | 0.09028 | 0.21908 | 5 / 26 / 17 |
| Full context | 모든 문서를 한 pass | **0.13214** | 0.25688 | 7 / 25 / 15 |
| Full split-and-merge | 문서별 pass 후 OR merge | 0.12980 | **0.33881** | 7 / 29 / 15 |

따라서 full split-and-merge는 4,000자보다 +0.03952 높았지만, 같은 full-context보다
-0.00234 낮았다. 판단 TP/FN은 full-context와 완전히 같고, 예측 positive만 32개에서
36개로 늘어 FP가 4개 증가했다. 반면 생성된 positive evidence의 validity는 0.84375에서
0.88889, span F1은 0.25688에서 0.33881로 상승했다. 즉 문서 단위 문맥은 evidence
위치를 더 짧고 정확하게 고르는 데는 도움이 되었지만, 이 표본에서는 위반 판단의
precision을 높이지 못했다.

## 문서 pass와 비용

20개 공고에서 총 41개 pass가 생성됐다. 문서 수 분포는 1-pass 공고 3개, 2-pass
13개, 3-pass 4개였고, 이번 표본에서는 단일 문서가 토큰 예산을 넘어 추가로
잘린 경우는 없었다. 모든 pass의 최종 system/user 메시지는 로컬 Gemma tokenizer로
입력 예산을 확인했으며, 실행 전 `inputs.jsonl`에 저장했다.

| 조건 | Prompt tokens | Completion tokens | Total tokens | OpenRouter cost | Runtime |
|---|---:|---:|---:|---:|---:|
| Full context | 282,789 | 14,333 | 297,122 | $0.03369 | 199.8s |
| Full split-and-merge | 364,617 | 29,075 | 393,692 | $0.05765 | 131.6s |

split mode는 총 token이 32.5% 늘고 비용이 71.1% 늘었다. 이번 실행의 wall-clock은
concurrency 4의 provider route 영향을 받으므로 처리량 우열 근거로 해석하지 않는다.

## 항목별 변화

full-context 대비 split 결과의 480개 binary cell은 `00=437`, `01=11`, `10=7`,
`11=25`였다. 의미 있는 F1 변화는 다음과 같다.

| 항목 | Full context F1 | Split-and-merge F1 | 변화 원인 |
|---|---:|---:|---|
| v3 | 0.571 | 0.800 | TP 2 유지, FP 3→1 |
| v5 | 0.400 | 0.333 | TP 1 유지, FP 3→4 |
| v9 | 1.000 | 0.800 | TP 2 유지, FP 0→1 |
| v13 | 0.200 | 0.182 | TP 1 유지, FP 8→9 |
| v15 | 0.000 | 0.000 | FP 1→2, FN 2 유지 |
| v21 | 0.000 | 0.000 | gold positive 0인데 FP 3→6 |

나머지 항목의 F1은 같았다. 따라서 이 결과는 “첨부문서를 독립 pass로 보면 recall이
올라간다”는 가설을 지지하지 않는다. 현재 표본에서는 full context가 이미 모든
gold-positive 7개를 찾았고, 분할은 추가 positive를 주로 false positive로 만들었다.

## 결론과 재현

기본 제출 정책은 계속 `context_strategy: single`로 둔다. `full_split_merge`는
정상 동작하고 overflow가 생겨도 문서 단위로 안전하게 이어지지만, 현 결과만으로
더 비싼 기본 정책으로 승격하지 않는다. 향후 법령 reference를 추가해 full context가
자주 overflow할 때, 또는 항목별 law-group 호출 실험의 비교 기준으로 다시 사용한다.

```bash
.venv/bin/python scripts/run_experiment.py \
  --config configs/config.exp006-full-split-merge-first20.yaml \
  --dump-inputs
```

원시 pass 입력은 `outputs/exp-006-full-split-merge-first20/inputs.jsonl`, 병합 예측은
`predictions.jsonl`, 지표는 `metrics.json` 및 `per_item_metrics.csv`에 있다.

## 사후 진단: 짧은 context인가, OR 병합인가?

### 검증한 분석 단위

이 진단은 `id × pass_index × v-item` 단위로 한다. 20개 ID, 실제 source document
41개, 저장한 입력 41개, 각 prediction의 `pass_judgments` 41개가 일대일로 맞고,
parse error는 0건이었다. 즉 이 결과의 차이는 checkpoint 누락이나 malformed JSON이
아니라 모델 판단과 병합에서 나온 것이다. 이번 20개에는 한 source document가 다시
token fragment로 나뉜 사례도 없다.

문서별 pass는 실제로 더 짧았다. token 수는 3,369~23,324였고, 각 공고에서 가장 긴
split pass는 20개 중 19개에서 full-context prompt보다 작았다(중앙값 84.9%). 그러나
공고당 여러 번 시스템 프롬프트·metadata·공고문 앵커·24-item JSON 출력을 반복하므로,
prompt token 합계의 중앙값 비율은 full-context의 129.0%였다. 따라서 이것은 단순히
“전체 context를 더 작은 chunk로 나눈” 실험이 아니라, **짧은 문맥에서 같은 24개
판단을 여러 번 독립 시행하고 OR를 취한** 실험이다.

### 확인된 원인

full-context와 split의 480개 `(공고, 항목)` 판단을 직접 대조하면 `00=437`,
`01=11`, `10=7`, `11=25`이다. 중요한 점은 변한 18개(`01`과 `10`)가 전부 gold 0이다.
양쪽의 TP=7 및 FN=15는 동일하다. 그러므로 이 표본에서는 shorter context가 새
gold-positive를 찾거나 기존 gold-positive를 잃은 흔적이 없으며, 차이는 false positive의
교환이다.

split 결과의 최종 positive 36개는 pass-level positive 52개에서 나왔다.

| 최종 결과 | positive를 낸 pass 수 분포 |
|---|---|
| TP 7개 | 1회 3개, 2회 3개, 3회 1개 |
| FP 29개 | 1회 19개, 2회 9개, 3회 1개 |

즉 OR는 원인 일부이지만 전부는 아니다. FP의 19/29(65.5%)는 이미 단 한 pass에서만
positive였으므로, 단순한 vote threshold로는 일반적으로 제거할 수 없다. 반대로
`PPS-DEV-17/v24`는 3/3 pass 모두 positive여서 unanimity도 막지 못한다.

또한 52개 positive pass 중 32개는 대상 document에서 evidence를 찾았지만, 20개
(38.5%)는 대상 document가 아닌 반복 공고문 앵커에서 evidence를 찾았다. 예를 들어
`PPS-DEV-04/v9`의 FP는 과업지시서 pass에서만 발생했지만 근거 `삼성 NT300E5L-K51G`는
그 대상 문서가 아니라 공고문 앵커에 있었다. 반면 실제 v9 TP 두 건은 모두 규격서
target pass에서 나왔다. 이것은 현재 앵커가 “notice 식별용 문맥”을 넘어서 각 pass의
판단 근거로 재사용되어, OR의 독립적인 FP 기회를 만든다는 직접 증거다.

### 병합 규칙의 반사실 비교

저장된 동일 41개 pass 판단을 재호출 없이 다시 병합했다. 이는 독립 평가가 아닌
가설 생성용 사후 분석이다.

| 병합 규칙 | Macro positive-F1 | TP / FP / FN | 해석 |
|---|---:|---:|---|
| OR (`>=1`) | 0.12980 | 7 / 29 / 15 | 현재 규칙 |
| 2표 이상 | 0.09722 | 4 / 10 / 18 | v5 및 v9 TP를 잃어 부적합 |
| pass 과반 | 0.14259 | 7 / 24 / 15 | 3-pass 공고의 1표 FP 5개만 제거 |
| 만장일치 | 0.09524 | 4 / 11 / 18 | recall 손실이 큼 |

과반은 2-pass 공고에서 1표면 통과하고 3-pass 공고에서만 2표를 요구한다. 그래서
이번 결과는 좋아 보이지만, 효과는 단 4개 3-pass 공고의 FP 5개에 의존한다. 이 20개
라벨을 보고 선택한 규칙이므로 기본 정책으로 채택하면 selection bias다. 특히
positive가 한 문서에만 있어야 하는 실제 위반을 일반적으로 억누를 위험이 있다.

### 교사 관점의 결론

“needle in a haystack” 때문에 context를 줄이는 발상은 타당하지만, 이 문제에서는
문서 간에 흩어진 24개 판정을 **모두 매 pass에 반복**시키는 설계가 그 이점을 상쇄한다.
현재 결과만으로는 context가 짧아서 나빠졌다고도, OR만 바꾸면 좋아진다고도 말할 수
없다. 더 정확한 진단은 다음과 같다.

1. full context가 이 20개 gold-positive를 이미 모두 찾아냈다. 따라서 split의
   판단 F1 하락은 retrieval/needle 문제가 아니라 FP calibration 문제다.
2. OR 병합은 union recall에 적합하지만, 반복 앵커·metadata에 반응한 positive도
   무조건 승격한다. 특히 document-local evidence를 요구하지 않아 anchor-derived
   판단이 섞인다.
3. non-absence item의 positive는 “대상 document 안의 evidence”를 함께 반환하게
   하고, anchor는 판단 근거로 쓰지 말라고 prompt에서 명시하거나 제거하는 실험이
   필요하다. 다만 이를 기계적으로 적용하면 이번 v5 TP 하나도 잃으므로, evidence
   source `doc_id`를 구조화해 기록한 뒤 평가해야 한다.
4. absence 항목과 metadata/cross-document 항목(v24 등)은 문서별 OR의 대상이
   아니다. 전체 문서 coverage를 아는 별도 notice-level pass 또는 결정적 비교로
   분리해야 한다. 현재처럼 모든 항목을 모든 document pass에서 판정하는 것이 가장
   큰 구조적 혼선이다.

다음 구현·실험은 단순 majority 승격이 아니라, `document-local` 항목은 해당 문서
근거가 있을 때만 후보로 모으고, `absence/meta/cross-document` 항목은 별도
notice-level 판단으로 보내는 **항목 역할별 분할**이어야 한다. 이 설계라면 작은
context라는 장점과 merge의 책임 범위를 함께 검증할 수 있다.
