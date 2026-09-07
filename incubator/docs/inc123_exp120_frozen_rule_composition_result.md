# INC-123 — EXP-120 frozen v2/v3/v21 rule composition

## 목적과 고정 조건

EXP-120의 archived full-dev200 prediction에 이미 독립 source audit를 통과한 세
predicate만 교체한다. 새 model call, prompt, threshold search, label-conditioned merge는
없다.

- v2: organizer official 230M 고시금액과 explicit bidder-performance condition
  (INC-040); 7 TP / 0 FP / 0 FN.
- v3: single-amount bidder qualification performance predicate (INC-036);
  8 / 0 / 0.
- v21: jurisdictional default-share predicate (INC-034); 6 / 0 / 0.
- 세 predicate의 positive evidence는 all-dev source substring validation을 이미 통과했다.

## 전체 dev200 재평가

| Policy | Macro positive-F1 | Delta |
|---|---:|---:|
| archived EXP-120 card v6 | 0.248932 | — |
| v2/v3/v21 frozen replacement | **0.317797** | **+0.068865** |

| Item | EXP-120 F1 | Rule F1 | Delta |
|---|---:|---:|---:|
| v2 | 0.428571 | 1.000000 | +0.571429 |
| v3 | 0.736842 | 1.000000 | +0.263158 |
| v21 | 0.181818 | 1.000000 | +0.818182 |

The other 21 label/evidence pairs are immutable in this composition.

## 해석과 다음 gate

이것은 dev200 기반 rule discovery를 포함한 historical evidence이므로 hidden-test score를
보장하지 않는다. 그러나 arbitrary character cutoff나 keyword list가 아니라 organizer law,
metadata, explicit source-role conditions으로 정의됐고, full dev positive coverage 및 negative
audit이 있다. E branch의 dev200 gate는 통과했다.

다음은 rule code를 EXP-120 isolated submission candidate에 통합한 뒤, exact staged-zip mock과
source-evidence validation을 수행하는 것이다. 그 후 제출은 EXP-120 public `0.244317`을
baseline으로 하는 별도 명시적 결정이다.
