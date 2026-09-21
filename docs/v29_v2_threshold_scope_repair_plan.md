# v29 — v2 고시금액·적용범위 source 교정

작성: 2026-09-18, dev / mac

## 목적

이 작업의 목적은 점수 최적화가 아니라 `판정에 필요한 정보가 온전히 들어간 카드`를 만드는
것이다. v28의 v2는 지방계약 실적제한에 지역제한용 시행규칙 제24조의 기관별 금액 분기를
재사용했다. 그러나 organizer source의 지방 제한입찰 운영요령은 물품제조·용역 실적제한을
`기획재정부장관 고시금액 이상`이면서 `특수한 설비·기술이 요구되는 경우`로 한정한다.
지역제한의 행안부 고시금액·5억원 분기는 v2의 실적제한 selector가 아니다.

## source contract

- 국가계약법 시행규칙 제24조제2호: 물품 제조·구매·용역의 고시금액.
- 국가계약법 시행규칙 제25조제2항: 제조·용역의 실적제한은 추정가격이 고시금액 이상인
  계약에 한정.
- 지방자치단체 입찰 및 계약 집행기준 제4장 제2절: 물품제조는 기재부 고시금액 이상이면서
  특수한 설비·기술, 용역은 기재부 고시금액 이상이면서 특수한 기술이 요구되는 경우.
- organizer 고시금액 파일: 국가 일반 물품·용역 2억3천만원, 공기업·준정부기관
  계약사무규칙 적용 물품·용역 7억1천만원.

카드는 실제 참가자격 실적, 입찰추정가격, 적용 계약법·기관 규칙, 특수 설비·기술 필요를
각각 확인한다. 불명 사실은 추정하지 않는다. 법령 원문 자체는 prompt에 넣지 않는다.

## 변경 통제

- base artifact: `decision_cards_v28_v5_local_threshold_selector.json`
- candidate artifact: `decision_cards_v29_v2_threshold_scope.json`
- allowed change: v2 `prompt_text` 하나
- v1, v3–v24, output schema, source scope, metadata/product renderer, merge, provider는 고정
- Python label rule이나 금액 override를 추가하지 않는다.

## 검증

생성 후 v28→v29 delta가 v2 하나인지 검사한다. exact tokenizer source coverage와 actual-value
delivery audit, short/attachment/overflow rendered-input review, 24-item semantic-input contract,
exact mock를 수행한다. 유료 실행은 완결성 보수의 완료 조건이 아니며 별도 승인 없이 실행하지
않는다.

## 구현·전달 검증 결과

- v29 asset을 생성했고 v28→v29 delta는 v2 하나다.
- preflight PASS: effective policy difference는 `prompt.decision_cards_path` 하나다.
- decision-card tests: `19 passed`.
- exact tokenizer dev200: 200 records, organizer 제공 문서 374개, omission 0;
  168×1 + 21×2 + 11×3 = 243 final calls.
- actual-value delivery audit: 200 records / 243 contexts PASS. upstream 미제공으로 이미 표시된
  외부 문서 10개 외에 pipeline omission은 없다.
- semantic-input contract: short 062, attachment 194, overflow 143, fast v5-positive 049,
  holdout v5-positive 046에서 24/24 PASS.
- exact fast20 mock: 20 rows, parse error 0, 49열 validation PASS.

따라서 v29에서 v2 기준과 현재 organizer가 제공한 notice별 값·원문은 실제 final 입력까지
전달된다. 이 검증은 Gemma의 판정 성능이나 organizer가 애초 제공하지 않은 외부 첨부 내용을
보증하지 않는다. 유료 실행은 하지 않았다.
