# Post-EXP231 exploration plan

작성: 2026-09-14, dev / mac

## 현재 결론

현재 최고 dev200 결과는 EXP208의 all-item relation-checklist 판정에 EXP221
v4-only와 EXP231 v5-only 결과를 순서대로 field replacement한 `0.329265`다.

점프는 하나의 원인으로 설명되지 않는다.

- EXP209 direct `0.257457`에서 EXP208 relation checklist `0.292959`로의
  `+0.035502`는 카드와 입력을 고정한 채, 원문 뒤에서 주체·역할·조항·날짜·대응
  metadata 관계를 다시 확인시킨 효과다.
- EXP208에서 EXP221 v4 composition `0.306117`로의 `+0.013158`은 잘못된 v4
  금액 적용범위 수정과 all-item attention 분리를 함께 포함한다.
- EXP221에서 EXP231 v5 composition `0.329265`로의 추가 개선은 v5-only 집중과
  빠져 있던 수치 비교 operand를 카드에 넣은 효과다.

따라서 `기존 카드 전체가 나빴다`고 일반화하지 않는다. v2, v3, v21은 dev200 F1
1.0이고 v22는 0.909다. 반면 v4에는 organizer-law source와 충돌하는 적용범위 gate가
있었고, v5에는 `고시금액 이상`을 판정할 실제 숫자 operand가 없었다. v15/v17의
법적으로 더 정확한 카드 수정은 independent holdout에서 성능 개선으로 이어지지 않았다.

현재 입력 완결 감사에서는 374/374 source documents, cards, 필요한 human-readable
metadata, exact-code product facts와 organizer semantics가 모두 final rendered input에
존재한다. 남은 주 병목은 입력 누락보다 다음 두 가지다.

1. 일부 item card의 실제 truth-condition 불완전성 또는 적용범위 충돌.
2. Gemma가 긴 원문에서 찾아낸 사실을 24개 카드의 동일 주체·역할·수치·예외 관계로
   안정적으로 결합하지 못하는 문제.

## 우선순위 1: 수정 v5 카드를 all-item base에 직접 적용

### 가설

EXP231의 개선 중 수치 operand 완결 효과가 item-only attention 없이도 유지된다면,
EXP208의 219-call topology 안에서 v5 recall과 precision을 회복할 수 있다.

### 최소 실험

- base: EXP208.
- active items, prompt mode, V/E schema, source admission, metadata/product facts, merge,
  postprocess와 provider parameters를 고정한다.
- v5 외 card text가 byte-equivalent인 card artifact를 사용한다.
- 유일한 허용 policy change는 `prompt.decision_cards_path`다.
- fast20에서 v5와 전체 macro/TP를 확인하고, independent holdout 방향이 같을 때만
  dev200으로 확장한다.

이 실험이 성공하면 v5 specialist 200 calls를 제거할 수 있다. 실패하면 all-item card
문구를 반복 조정하지 않고 v5의 attention isolation이 필수였다고 기록한다.

## 우선순위 2: v4와 v5 specialist를 한 호출로 통합

### 가설

이미 fast/holdout/dev200에서 각각 검증된 두 item만 같은 subset prompt에서 판단해도
서로의 recall/precision을 훼손하지 않는다면 현재 dev200 topology를 619 calls에서 약
419 calls로 줄일 수 있다.

### 최소 실험

- base output은 EXP208으로 고정한다.
- active items는 정확히 `[v4, v5]`다. 전체 v-grouping으로 확대하지 않는다.
- v4 corrected scope와 v5 numeric operand를 동시에 보존하는 결합 card artifact를
  사용한다. v4/v5 외 card text는 바꾸지 않는다.
- output은 v4/e4와 v5/e5만 model-owned field replacement한다. OR, majority 또는 Python
  label inference를 사용하지 않는다.
- 먼저 별도 specialist 합성과 비교해 v4/v5 TP/FP/FN, malformed, evidence validity와
  exact call topology를 측정한다.
- fast와 independent holdout에서 두 item 모두 방향을 유지할 때만 dev200으로 간다.

419 calls도 이전 438-call 후보가 evaluator 120분을 초과했다는 점에서 안전하지 않다.
이 후보는 현재 최고 quality를 압축하는 중간 단계이며 runtime 통과를 보장하지 않는다.

## 우선순위 3: v5의 명시적 수치 관계 판정

EXP231의 네 false positives는 카드와 rendered metadata에 임계값과 입찰추정가격이 모두
있는데도 Gemma가 명백한 `추정가격 < 임계값`을 무시한 사례다. 이는 추가 입력 문제가
아니라 관계 실행 문제다.

다음 후보는 v5 하나에서만 다음 observable fields를 가장 작게 요구한다.

1. 적용 법체계와 organizer-provided 기관 분기.
2. 입찰추정가격.
3. 적용 임계값.
4. 두 금액의 대소 관계.
5. 실제 참가자격 지역 제한의 존재.
6. model-owned final v5/e5.

Python은 원문/metadata provenance와 parse만 검증하고 비교 결과로 label을 계산하거나
override하지 않는다. 동일 응답의 큰 reasoning schema가 논리 일관성을 강제하지 못한
EXP222를 반복하지 않도록, enum과 필드는 v5 truth condition에 필요한 최소치로 제한한다.

## 후순위: item별 source/card audit

현재 zero-F1 item을 일괄 specialist화하지 않는다. v6, v7 및 absence items를 포함한 각
항목에 대해 다음 순서로 하나씩 진단한다.

1. gold evidence와 필요한 organizer fact가 actual rendered prompt에 존재하는가.
2. card가 organizer law source의 적용범위·1 조건·중요 0 조건을 충실히 압축했는가.
3. 오류가 참가자격·평가·제품·시설·제출서류 등 semantic role 혼동인가.
4. absence item이면 적용대상 확인과 whole-notice presence inversion 중 어느 단계가
   실패했는가.

source로 입증된 card defect가 있는 가장 작은 item만 수정한다. v15/v17처럼 법적 문구는
개선됐지만 independent holdout이 실패할 수 있으므로, card 정확성과 모델 성능을 별도
결론으로 기록한다.

## 중단 및 승격 규칙

- full-split x v-group, source-first x grouping, 반복 V-only consensus, raw-law RAG와
  Python label rules는 재시도하지 않는다.
- 한 실험에서 card, schema, merge, provider parameter와 routing을 섞지 않는다.
- 모든 후보는 complete semantic input, 모든 admitted original source와 final source
  recheck를 유지한다.
- paid run 전 preflight, exact tokenizer admission, short/attachment/overflow rendered
  review, active-item semantic contract, mock와 isolated output을 완료한다.
- fast20은 고정 panel만 사용하고 independent holdout 확인 후에만 dev200으로 확장한다.
- local quality와 evaluator runtime을 별도로 판단한다. batch size는 호출 수를 줄이지 않는다.

## 2026-09-15 V-only / v10 verification update

최신 v18 audit 후속 EXP314–318: source-correct 카드의 fast recall 회복은 holdout에서
FP4→11, F1 `.333333→.153846`으로 악화했다. V-only fast F1은0. 원문/카드/금액을
모두 담은 한pass에서도 명시 제한과 금액 적용범위를 어기는 raw label이 확인됐다.
카드 출처 정확성과 모델 개선을 구분하고 v18 재문구/repeat/dev200 확대를 중단한다.
상세 `docs/exp314_exp316_v18_absence_card_plan.md`. 남은 구조 탐색에서 이 실패를
기각된 큰 observable schema나 Python label rule로 재포장하지 않는다.

- v5-only V/E와 V-only는 같은 labels를 냈고, V-only는 completion만 줄였다. v4에서도 같은
  결론이었다. 출력 형식 자체의 품질 이득은 확인되지 않았다.
- full catalog + structured v10 V-only는 fast/holdout/dev200에서 zero recall을 회복했지만
  dev200 `TP 4 / FP 66 / FN 3`, F1 `.103896`으로 precision이 너무 낮았다. 현재 최고
  EXP231 composition에 단순 replacement한 연구 상한은 `.333594`지만 submission 후보가 아니다.
- structured review에서 full catalog만 제거한 EXP250은 fast v10이 다시 all-zero가 되어,
  unknown exact-code 공고의 organizer-grounded product-name mapping이 실제 필요함을 입증했다.
- 같은 complete input을 두 번 읽는 v10 V-only final-owner EXP251은 fast F1을
  `.444444 -> .500000`으로 올렸지만, policy-identical holdout EXP252는
  `.285714 -> .200000`으로 악화했다. EXP187의 all-item consensus, EXP225/226 v4 결과와 함께
  반복 V-only 검증을 일반 성능 lever로 기각한다. pass 수·투표·wording을 반복 조정하지 않는다.

다음 우선순위는 반복 호출이 아니라 zero-F1 item의 truth condition을 organizer source에서
검증하고, 그 관계가 일반 7-category/checklist로 표현되지 않는 가장 작은 item 하나만 구조화하는
것이다. v13은 dev200 gold 6건 중 exact-code matched 4건으로 v10보다 적용성 입력이 낫고,
공식 기준도 `경쟁제품 적용 → 소기업·소상공인만의 참가자격 제한 → 소액수의/별도 허용 사유`
관계로 명확하다. 따라서 다음 후보는 v13-only V/E observable schema가 우선이다. e13은 필요한
항목이므로 V-only 뒤 알고리즘 생성으로 바꾸지 않고, model evidence를 기존 substring validator로
검증한다. full catalog 필요성은 matched/unknown을 분리해 먼저 감사하고 prompt에는 raw code/status를
노출하지 않는다.

## 2026-09-15 later item/V-only update

- EXP269–271은 v1 card 범위를 조직·상시인력·보유시설·서비스망까지 source-grounded하게
  보완하고 V/E와 V-only를 비교했지만 세 arm의 v1 labels가 완전히 같았다. V-only completion은
  92.9% 줄었으나 label gain은 없었다.
- EXP272–274는 v23의 계약법·계약방식·금액구간·최소일수·날짜역할·계산일수·예외를 한 응답의
  observable proof로 완결했다. ordinary V/E F1 `.142857`에서 proof V/E `.125000`, proof
  V-only `.105263`으로 악화했다. 모델은 국가계약/비협상과 최소일수 이상을 스스로 기록하고도
  모든 review를 `1조건충족`으로 냈다.
- 따라서 V-only는 지금까지 v4, v5, v6, v1에서 V/E와 동률, v10 repeated verification과
  v23 quantitative proof에서는 열위다. completion 절감은 반복 호출/evidence recovery를 정당화할
  label-quality 증거가 아니다. v23의 발췌/checklist/partial-proof/full-proof branch도 종료한다.

다음 탐색은 이미 실패한 proof 문구를 늘리지 않는다. model output이 아니라 organizer 입력에서
아직 적용성 사실이 불완전한 zero-recall item을 하나씩 감사한다. 부재탐지 중에서는 v11 gold
6건 가운데 exact document-code 경쟁제품 match가 3건, unknown이 3건이고 현재 card는 적용 불명을
자동 0으로 둔다. 그러므로 v11은 `경쟁제품 적용성 → 실제 중소기업자간 경쟁 참가제한의 존재/부재
→ 명시 예외`를 source와 CSV로 먼저 감사할 다음 후보지만, v10의 full-catalog 과호출을 그대로
복제하지 않고 matched/unknown 분리를 선행한다.

## 2026-09-15 v12/v7 후속 결과

- v12의 실제 구매대상↔고시후보↔특이사항↔직생요구 관계를 source-correct card와 structured
  review로 보완한 EXP298~300은 existing-card fast F1 `.6667`보다 모두 나빴다. V/E review는
  `0/3/1`, V-only review는 `0/7/1`이었다. 모델은 `경쟁제품적용=적용`이라고 관찰하고도
  `1조건충족`을 내므로 card/checklist를 더 늘리지 않는다.
- v7-only existing-card EXP306은 fast `1/0/1`, `.6667`; EXP312 dev200은 `3/2/4`, `.5`로
  all-item zero recall을 일부 회복했다. EXP262 composition에 v7만 교체한 local research upper
  bound는 `.3746082750`이다.
- 그러나 EXP306/309는 과거 EXP223/224와 정책이 같다. holdout positive의 actual request JSON은
  byte-identical인데 과거에는 0, 이번에는 1이었다. 이는 temperature 0 OpenRouter repeat
  variability이며, 새 independent confirmation이나 반복 호출의 성능 근거로 세지 않는다.
- v7 corrected threshold card와 V-only는 existing-card V/E와 fast labels가 모두 같았다.
  V-only completion 절감만으로 다중 V-only/evidence recovery를 만들지 않는다.

현재 quality 방향은 검증된 item-isolation 효과를 specialist 200-call씩 쌓는 것이 아니라,
한 bounded final에서 attention을 보존하는 구조를 찾는 것이다. 동일 prompt repeat/majority는
provider 변동에서 좋은 결과만 선택하게 만들 위험이 있으므로 계속 금지한다.
