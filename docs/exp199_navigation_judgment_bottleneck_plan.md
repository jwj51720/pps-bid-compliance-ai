# EXP199 — navigation versus final-judgment bottleneck diagnostic

작성: 2026-09-11, dev / mac

## 가설

EXP171의 낮은 양성 recall이 1차 source navigation의 사실 탐색 실패 때문인지, 이미 찾은
사실을 final이 0으로 판정하는 적용·관계·카드 단계 때문인지 분리한다. gold evidence가 있는
양성에 한해, 저장된 1차 원문 후보가 gold span을 포함하거나 gold span에 포함되는지를
whitespace-normalized containment로 측정한다.

이 검사는 gold를 prompt, card, rule 또는 submission에 넣지 않는다. 저장된 EXP171 결과를
읽는 label-aware 사후 진단이며 새 provider call과 정책 변경은 없다.

## Base와 허용 변경

- base artifact: `outputs/exp-171-source-first-full-final-dev200-c4/predictions.jsonl`
- labels: organizer `data/raw/open/dev_labels.csv`
- `allowed_policy_changes`: 없음
- source, prompt, cards, product facts, merge, evidence, model parameters: 불변

## 판정

- navigation hit + final FN이 많으면 광범위한 새 추출 schema보다 final 적용/관계 판단을
  우선한다.
- navigation miss + final FN이 많으면 해당 item의 source relation extraction 후보가 된다.
- blank gold evidence는 navigation quality의 분모에 넣지 않고 별도로 센다.
- frozen Python postprocess가 만든 TP는 model-owned 결과와 분리한다.

출력에는 item별 gold positive, nonblank/blank evidence, navigation hit/miss, model/final
TP/FN quadrant와 해당 record ID를 보존한다.
