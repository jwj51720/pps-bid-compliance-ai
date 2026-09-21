# EXP245 — v10 organizer product-catalog completeness diagnostic

작성: 2026-09-14, dev / mac

## 입증된 결손

EXP244는 complete-input v10-only V-only에서도 모든 값을 0으로 냈다. dev200 v10 양성 7건 중
6건은 organizer metadata와 원문에 exact 10자리 세부품명 코드가 없어 현재 product fact가
`unknown`이다. 따라서 모델은 실제 구매대상이 중소기업자간 경쟁제품인지 판단할 주최 측
목록을 받지 못한 채, 카드의 `적용 불명이면 0`을 따르고 있다.

## 최소 가설

v10-only final message에 주최 측 경쟁제품 CSV의 615개 행을 사람이 읽는
`세부품명 (특이사항)` 목록으로 제공하면, Gemma가 공고의 실제 구매대상·금액·규격과 직접
대조하여 적용성을 판정하고 그 뒤 공고 전체에서 직접생산 조건의 부재를 확인할 수 있다.

이 목록은 약 12,093 characters / Gemma tokenizer 8,938 tokens다. raw JSON, internal status,
코드 배열, 법령 원문이나 dev example을 넣지 않는다. exact-code fact는 그대로 앞에 유지하며,
목록 행은 적용 확정이 아니라 model이 source와 비교할 organizer-provided candidates다. Python은
문구 검색, 제품 분류, 조건 적용 또는 label 계산을 하지 않는다.

## 통제 정책

- base: `configs/config.exp244-v10-only-vonly-fast-panel-c4.yaml`.
- sole allowed change: `prompt.competition_product_context_mode`.
- active v10, V-only schema, card, metadata, organizer semantics, all original source, tokenizer
  admission, provider/model parameters, absence merge와 frozen postprocess는 동일하다.
- diagnostic 목적은 full catalog가 최종 설계인지 정하는 것이 아니라, missing product knowledge가
  v10 병목인지 확인하는 것이다. 성공하면 후속에서 fixed BGE-m3로 주최 측 catalog 후보만
  축소하는 runtime 설계를 별도 검증한다.

## gate와 승격

preflight, exact dev200 admission/call topology, short/attachment/overflow rendered review,
active-v10 semantic contract, exact mock, merge validation과 tests를 먼저 통과시킨다. fast20에서
EXP244 v10 `0/0/2`보다 F1이 개선되어야 independent holdout으로 간다. 입력 증가로 source가
누락되거나 malformed가 생기면 실패다. full catalog 성공만으로 곧바로 submission policy로
승격하지 않는다.

## Fast20 결과와 중단 결정

- preflight는 `prompt.competition_product_context_mode` 하나만 달라졌음을 확인했다.
- exact dev200 admission은 374/374 documents, omission/over-budget 0이었다. catalog가 fixed
  context를 약 8,938 tokens 늘려 topology는 168×1 + 18×2 + 14×3 = 246 calls가 됐다.
- 대표 세 rendered message에서 전체 catalog, v10 card, metadata, organizer semantics와 모든
  source가 확인됐다. mock validation과 217 tests가 통과했다.
- provider call은 20 records / 24 source-pack calls, 28.2초, prompt/completion
  552,784/243 tokens, parse error 0이었다.
- v10 TP/FP/FN은 `0/0/2 -> 0/1/2`, F1은 계속 0이다. 유일한 1은 gold-negative
  `PPS-DEV-036`이며 두 fast positive는 여전히 0이다. merged macro는 `.325000`으로 동일하다.

제품 지식의 semantic-input 결손은 실재하지만, 615개 목록을 추가하는 방식은 target recall을
회복하지 못하고 token/call 수와 FP만 늘렸다. 따라서 holdout/dev200으로 승격하지 않고
`full_catalog_v1`은 diagnostic-only로 남긴다. 이 결과만으로 BGE 후보 축소를 구현하지 않는다.
후속 product retrieval은 먼저 모델이 후보가 주어진 양성에서 실제 적용성과 whole-notice
absence를 분리해 수행할 수 있는 더 작은 probe가 있어야 한다.
