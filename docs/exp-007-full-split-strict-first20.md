# EXP-007: Strict Target-Document Evidence, First 20

## 질문

EXP-006의 full split-and-merge에서, Gemma가 대상 source document 조각 안의 근거만
사용하도록 친절하고 엄격한 정부계약 컴플라이언스 지침을 주고, Python도
non-absence positive의 evidence가 그 조각에 없으면 0으로 강등하면 FP가 줄어드는가?

## 실행

`configs/config.exp007-full-split-strict-first20.yaml`로 `PPS-DEV-01`~`20`을 실행했다.
문서 pass·모델·표본·generation settings는 EXP-006과 같고, system prompt에 strict
계약을 추가했다. 20개 ID와 41개 pass가 모두 완결됐으며 malformed JSON은 없었다.

| 실험 | Macro positive-F1 | TP / FP / FN | Positive 수 | Evidence validity |
|---|---:|---:|---:|---:|
| EXP-006 기존 full split OR | 0.12980 | 7 / 29 / 15 | 36 | 0.88889 |
| EXP-007 strict target evidence | 0.14861 | 10 / 83 / 12 | 93 | 1.00000 |

표면적으로 macro F1은 +0.01881이지만, 이는 채택 가능한 개선이 아니다. 전체 FP가
29개에서 83개로 거의 세 배가 됐고, predicted positive도 36개에서 93개로 늘었다.

## 원인: 부재탐지와 문서별 판정의 충돌

strict prompt는 non-absence item에는 의도대로 “대상 문서 안의 exact evidence가 없으면
0”을 지시하고 Python에서도 강제했다. 그러나 `v10`, `v11`, `v16`, `v18`, `v20`은
증거문구가 없는 것이 위반인 부재탐지 항목이라 evidence 강등의 예외다. prompt가
이 예외를 “이 문서 조각에 문구가 없으면 1”로 해석하면서 여러 document pass에서
positive를 냈다.

| 항목 | EXP-006 TP / FP / FN | EXP-007 TP / FP / FN | EXP-007 F1 |
|---|---:|---:|---:|
| v10 | 0 / 0 / 1 | 1 / 12 / 0 | 0.14286 |
| v11 | 0 / 0 / 1 | 1 / 12 / 0 | 0.14286 |
| v16 | 0 / 0 / 1 | 1 / 12 / 0 | 0.14286 |
| v18 | 0 / 0 / 0 | 0 / 13 / 0 | 0.00000 |
| v20 | 0 / 0 / 0 | 0 / 13 / 0 | 0.00000 |

첫 20개에서는 positive-class macro F1이 gold-positive가 없는 v18/v20의 FP를 벌점으로
거의 반영하지 않는다. 반면 v10/v11/v16은 각 1개 TP를 얻어 0에서 0.14286이 된다.
이 세 항목의 작은 F1이 macro 평균을 끌어올린 것이므로, macro F1 상승만 보고 정책을
선택하면 안 된다.

## 결론

1. **non-absence positive의 대상-document evidence 강제**는 설계 원칙으로 유지할
   가치가 있다. 이는 EXP-006에서 확인된 anchor-derived positive를 막는 유일하게
   명확한 귀속 계약이다.
2. **부재탐지 항목에는 적용하면 안 된다.** “없음”은 문서 하나가 아니라 공고의 모든
   관련 문서를 확인한 뒤에만 판정할 수 있다. 문서별 OR에 이 항목들을 넣는 것은
   논리적으로 잘못이다.
3. 따라서 EXP-007 전체 수치는 full split 전략의 성능 개선 증거가 아니다. 다음 버전은
   non-absence document-local pass를 OR로, 부재탐지 항목은 문서별 “없음” 판단의 AND로
   결합해야 한다. `없음·없음·있음·없음·없음`은 최종 위반이 아니다.

## 재현

```bash
.venv/bin/python scripts/run_experiment.py \
  --config configs/config.exp007-full-split-strict-first20.yaml \
  --dump-inputs
```
