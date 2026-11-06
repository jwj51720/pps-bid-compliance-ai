# EXP244 — v10-only V-only absence specialist

작성: 2026-09-14, dev / mac

## 진단과 가설

EXP208 dev200은 v10의 gold-positive 7건을 모두 0으로 판정해 TP/FP/FN `0/0/7`이다.
v10은 중소기업자간 경쟁제품·직접구매 적용대상인데 필요한 직접생산 확인 조건이 공고 전체에
없는지를 판정하는 absence item이다. 이 항목은 competition rule상 e10이 항상 빈칸이므로,
V-only 출력은 evidence 정보를 제거하지 않는다.

가설은 complete all-item prompt에서 24개 판정에 묻힌 적용성/whole-notice absence 판단을
v10 하나에 집중시키면, exact-code competition-product fact와 모든 admitted source를 함께
대조해 양성을 회복할 수 있다는 것이다. Python은 제품 코드의 matched/not-matched/condition
fact를 label로 바꾸지 않고, model-owned v10만 frozen base에 field replacement한다.

## 통제 정책

- base: `configs/config.exp205-relation-checklist-after-source-fast-panel-c4.yaml`.
- candidate: `configs/config.exp244-v10-only-vonly-fast-panel-c4.yaml`.
- allowed changes: `prompt.active_items`, `prompt.profile`, `prompt.mode`,
  `prompt.output_mode`.
- v10 card, human-readable metadata, condition-aware exact-code product fact, organizer semantics,
  all admitted original source, exact tokenizer admission, provider/model parameters와 frozen
  postprocess는 유지한다.
- `complete_fact_subset_v1`과 `baseline`은 inactive item 지시를 제거하고 v10만 출력하기 위한
  기존 subset serialization이다.
- e10은 원래 항상 blank이므로 algorithmic evidence 생성이나 source substring 추정은 하지
  않는다.

## 유료 전 gate와 승격 규칙

preflight가 선언된 네 serialization change 외 차이를 거부해야 한다. dev200 exact source/
token admission, short/attachment/overflow 실제 rendered review, active v10 semantic-input
contract, exact mock, 49-column merge validation과 전체 tests를 먼저 통과시킨다.

fast20은 `configs/dev_fast_panel_v1.json`만 사용한다. EXP205의 v10 `0/0/2`보다 F1이 개선되고
malformed/input failure가 없을 때만 동일 정책을 independent holdout20으로 옮긴다. holdout도
같은 방향일 때만 dev200으로 확장한다. 실패하면 다섯 absence item을 한꺼번에 묶거나 card,
schema, merge를 동시에 바꾸지 않는다.

## 결과와 새 입력 진단

- preflight는 선언한 네 subset/output serialization change만 확인했다.
- exact dev200 admission은 200 records, 374/374 documents, omission/over-budget 0,
  200×1 calls였다.
- short/attachment/overflow rendered review에서 v10 card, human-readable metadata,
  condition-aware product fact, organizer semantics와 전체 source가 확인됐다. mock 20건의 49열
  validation과 216 tests도 통과했다.
- provider call은 20 calls, 21.0초, prompt/completion 250,576/180 tokens, parse error 0이었다.
- Gemma는 v10을 20건 모두 0으로 냈다. EXP205와 changed v10 cells가 0이고 v10 TP/FP/FN은
  `0/0/2`, merged macro도 `.325000`으로 동일하다.

따라서 v10 실패는 V/E 출력 부담이나 24-item attention만으로 설명되지 않는다. 더 중요한
입력 결손은 경쟁제품 적용성이다. dev200 v10 gold-positive 7건 중 exact-code product fact가
`matched`인 것은 1건뿐이며 나머지 6건은 organizer metadata와 문서에 대조 가능한 10자리
세부품명 코드가 없어 `unknown`이다. fast positive `PPS-DEV-062`, `PPS-DEV-069`도 모두
unknown이다. 두 공고는 실제로 공연/행사대행 용역을 설명하지만, 현재 prompt는 주최 측
경쟁제품 목록의 `기타행사기획및대행서비스`와 그 `추정가격 10억원 미만` 조건을 전달하지
않는다.

이는 source-document 누락 버그가 아니라 semantic reference incompleteness다. exact-code가
존재하는 경우의 입력 계약은 검증됐지만, 코드가 없는 공고에서는 v10 적용대상을 결정할
주최 측 제품 지식이 final message에 없다. dev 문구를 Python rule로 바꾸지 않고, organizer
product rows를 model-readable 후보로 제공하는 별도 EXP245 diagnostic으로 넘어간다.
