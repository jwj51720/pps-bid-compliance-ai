# v31 — v4 organizer 정의 충돌 해소

작성: 2026-09-18, dev / mac

## 확인된 회귀

v30은 v4 항목명의 `고시금액 이상`을 적용 gate로 채택했다. 그러나 이 선택은 다음 organizer
evidence와 동시에 성립하지 않는다.

- 정부·지방 계약 집행기준의 특정기관 발주실적/특정명칭 실적 금지는 금액 조건 없이 별도
  금지관계로 서술된다.
- organizer dev의 v4 양성 6건은 `PPS-DEV-06,042,051,053,059,062`다.
- 그중 입찰추정가격은 7.4818억원, 0.6126억원, 2.4545억원, 0.2269억원, 0.8345억원,
  2.2727억원이다. 일반 물품·용역 2.3억원 미만도 네 건이며 모두 organizer v4=1이다.
- `PPS-DEV-06`은 요구 실적 4억원이 추정가격 7.4818억원보다 작아 v3=0이지만, 국가기관
  발주 국제회의 실적으로 한정하여 v4=1이다. 따라서 v4는 v2/v3 금액·배수와 독립된
  특정기관/특정실적 범주다.
- v26의 금액 비의존 v4 card는 fast20 v4 `TP/FP/FN=2/0/1`; v30의 금액 gate card는 같은
  fast20에서 `0/0/3`이다. independent holdout의 v4 양성도 v30에서 0으로 놓쳤다.

이는 개별 label에 맞춘 Python rule이 아니라 organizer가 제공한 법령, labels, evidence,
metadata의 범주 정의를 함께 대조해 source conflict를 해소한 것이다.

## 변경 통제

- base: `decision_cards_v30_full_source_concordance.json` / EXP333.
- candidate: `decision_cards_v31_v4_organizer_definition_resolution.json`.
- sole card change: v4 `prompt_text`.
- v4는 금액 gate를 제거하고, 실제 참가자격 역할 → 특정기관/특정명칭 실적 한정 → 구체적
  기술·공법·성능·품질 필요의 순서만 적용한다.
- v1–v3/v5–v24, metadata/product rendering, source admission, schema, merge, provider,
  Python labels는 고정한다.

## 검증 순서

1. v30→v31 changed set가 정확히 `{v4}`인지 테스트한다.
2. preflight, dev200 exact source coverage/value delivery, short/attachment/overflow exact rendered
   semantic audit, fast20 mock를 통과한다.
3. fast20 V/E를 EXP333과 비교한다. v4 recall 회복과 다른 item의 손실을 함께 본다.
4. gain이 있으면 policy-identical holdout20을 EXP337과 비교한다.
5. 두 panel 방향이 일치할 때만 dev200으로 확장한다.

V-only는 EXP334–338에서 재기각됐으므로 이 실험에 섞지 않는다.

## 결과

### 입력·실행 gate

- v30→v31 changed set `{v4}` 확인.
- preflight card path only.
- dev200 exact admission: 200 notices / 374 supplied documents / 243 contexts / omission 0.
- actual-value delivery 200/200, 243/243 PASS; upstream unavailable external docs 10개는 별도 한계.
- 062/194/143/049/046 exact rendered semantic audit 24/24 PASS.
- fast20 mock 20 rows 및 validation PASS.

### Fast20 EXP339

- macro `.122917` versus EXP333 v30 `.142361` (`-.019444`).
- v4는 `0/0/3`, F1 0에서 `2/0/1`, F1 `.8`로 회복했다.
- 그러나 변경하지 않은 v2는 `.6667→.4`, v3는 `1.0→.75`, v22는 `1.0→0`으로 바뀌어
  v4 gain을 상쇄했다. sole card change가 unrelated items를 바꾼 것은 24-item generation의
  cross-item/provider variability이며 v4 정의 정정의 반증이 아니다.
- runtime 93.2s, prompt/completion `528,124/19,327`, parse/validation error 0.

### Independent holdout20 EXP340

- macro `.166667` versus EXP337 v30 `.125000` (`+.041667`).
- 그러나 v4는 양쪽 모두 `0/0/1`, F1 0으로 회복되지 않았다. macro gain은 변경하지 않은 v2가
  `0/0/1`에서 `1/0/0`으로 바뀐 데서만 발생했다.
- runtime 142.1s, prompt/completion `481,458/16,699`; positive evidence validity `.8`, warning 1.

## 결정

- organizer source 정의상 금액 gate 제거는 옳으므로 v31 카드 보수 자체는 유지한다.
- 하지만 all-24 prompt에서 v4 실행 gain은 fast에서만 나타나고 holdout에서 재현되지 않았다.
  EXP339/340의 macro 변화도 v4가 아닌 unrelated item 변동에 크게 좌우됐다.
- 따라서 이 all-item v31 arm을 dev200 성능 실험으로 확장하지 않는다. 이미 같은 금액 비의존
  v4 기준의 item-local EXP219/220/221은 fast/holdout/dev200에서 v4 recall을 모두 회복했으므로,
  남은 문제는 기준 누락이 아니라 **all-item attention interference**다.
- 다음 구조는 v4 문구를 다시 조정하는 것이 아니라, 24개를 24호출로 곱하지 않으면서 item별
  판단 attention을 보존하는 bounded ownership 구조여야 한다.
