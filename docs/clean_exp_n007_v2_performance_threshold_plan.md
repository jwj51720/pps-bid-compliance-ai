# N007: native v2 performance-role and threshold owner

작성일: 2026-09-22

## 수학적 우선순위

v22 완성 후 남은 frozen 완전일치 항목 v2/v5/v7/v8/v15/v21은 각각
독립 baseline에서 Macro `1/24 = 0.0416667`을 지탱한다. 동일한 최대
보존가치에서 panel 검증력은 다음과 같다.

| item | fast positives | holdout positives | 주요 추가 자유도 |
| --- | ---: | ---: | --- |
| v2 | 3 | 1 | 실적 역할, 고시금액, 지방 특수기술 예외 |
| v5 | 1 | 1 | 다중 공사/용역 금액표, 지역 역할 |
| v7 | 2 | 1 | v5 금액표 + 복수지역 관계 + 예외 |
| v15 | 1 | 1 | 경쟁제품 조건/특이사항 + 기업규모 예외 |
| v8 | 1 | 0 | 지역·실적 AND + 수의/특수 예외 |
| v21 | 2 | 0 | 공동방식·지분 역할·수치 조정 |

따라서 양성 recall을 fast와 holdout 양쪽에서 볼 수 있고 v5/v7보다 금액
분기가 적은 v2를 다음 owner로 선택한다. 목표는 frozen v2 dev200
TP/FP/FN 7/0/0, F1 1.0을 독립 재현하는 것이다.

## 가설과 역할 분리

v2는 “실적” 단어 탐지가 아니라 아래 관계의 conjunction이다.

1. 과거 완료 실적의 금액·규모·수량이 실제 입찰 참가자격인가
2. 물품 제조·구매/공급·용역의 실제 업무와 허용 제한 근거가 무엇인가
   (v31의 `물품제조·용역이 아님 → 0`은 주최측 조항 및 양성 사례와
   충돌하므로 별도 card 버전에서 수정한다)
3. 입찰추정가격이 실제 적용 고시금액 미만인가
4. 지방계약이면 특수 설비·기술 필요에 직접 연결된 허용 제한인가

Python은 organizer metadata의 `입찰추정가격` 정수와 card에 고정된
2억3천만원/7억1천만원 비교만 계산한다. 7억1천만원은 공기업·준정부기관
계약사무규칙이 문서상 실제 적용된다는 Gemma observation이 Y일 때만
선택한다. 기관명이나 `소관구분`만으로 선택하지 않는다.

Gemma observation 초안:

- `performance_participation`: 과거 완료 실적을 참가자격으로 요구
- `procurement_role`: 실제 제조·구매/공급·용역 중 어느 업무이며,
  실적 제한을 허용하는 명시적 근거가 있는가
- `enterprise_rule_applies`: 7억1천만원 기관규칙이 실제 적용됨
- `local_special_exception`: 지방 물품제조의 특수 설비·기술 또는
  지방 용역의 특수 기술 필요에 직접 연결된 허용 제한
- `quote`: performance_participation=Y인 원문 substring

final 1은 performance가 Y이고 적용 기준 미만이며, 원문상 명시적
허용 근거가 없을 때만 가능하다. 제조·용역의 특수 기술 허용범위는
별도로 확인한다. 필요한 semantic fact가 U이면 0으로 투영한다.
Python은 실적 keyword나 dev ID로 label을 만들지 않는다.

## 입력과 검증

- 모든 organizer document를 scan한다.
- 각 문서 시작부, 참가자격 anchor, 실적 anchor 주변 exact span을 bounded
  view로 만든다.
- metadata는 v2 item fields만 human-readable form으로 렌더링한다.
- v31은 재현용으로 보존하고, v2 범위를 고친 별도 card 버전을
  선언한다. raw law/reference text는 prompt에 넣지 않는다.
- N007 후보 card는
  `data/derived/decision_cards_v32_v2_purchase_scope.json`이며,
  `scripts/build_v32_v2_purchase_scope_card.py`가 v31에서 v2 문구만
  파생한다. 실제 Gemma observation task는 아직 미구현이다.
- legacy/reference/frozen import·response fallback은 금지한다.

단계별 gate:

1. dev200 no-call source/provenance/token audit, gold e2 7/7 coverage,
   200/200 admission
2. rendered short/attachment/largest, fast 양성 3건, holdout 양성 1건 검토
3. fixed fast20 TP=3, FP=0, FN=0, invalid=0
4. independent holdout20 TP=1, FP=0, FN=0, invalid=0
5. dev200 TP=7, FP=0, FN=0, evidence validity 100%

source view와 semantic schema를 동시에 바꾸지 않는다. 먼저 no-call source
view를 고정하고, 그 audit hash 위에서만 task를 실행한다.

## 점수 확인 주기

의미 계약이 해소되고 유료 실행 전 검증을 통과하면, 각 단일 변경마다 고정
`configs/dev_fast_panel_v1.json` fast20을 실행해 v2 TP/FP/FN/F1,
24항목 Macro에 대한 예상 기여, malformed rate, evidence validity, call 수와
시간을 기록한다. fast20이 목표에 못 미치면 원인 사례를 보고 다음 한 가지
변경만 한다. fast20은 후보 선별용이므로 좋은 점수만으로 정책을 고정하지
않고, 독립 `configs/dev_prompt_holdout_v1.json` holdout20을 통과한 후보만
dev200으로 확장한다. 같은 panel을 반복 수정해 얻은 최고값은 독립 검증
점수처럼 보고하지 않는다.

2026-09-22 no-call 결과: bounded v2 view는 200/200 reserve admission과
gold e2 7/7을 통과했다. `PPS-DEV-02`의 물품 공급 양성과 v31 카드의
범위 충돌은 [별도 대조 문서](clean_native_v2_scope_resolution.md)에
주최측 법령 조항과 함께 기록했다. card 후보 버전과 실제 rendered
semantic-input contract를 고정하기 전에는 paid fast20을 실행하지 않는다.

v32 no-call 재감사 결과: 200건·374개 문서 검사, gold e2 7/7 보존,
envelope 최대 10,482토큰, task용 1,200-token reserve 200/200이다.
`outputs/clean-native-v2-performance-view-v32/dev200/audit.json`과
`rendered_inputs/`에 short, attachment, largest, scope-conflict 및
fast/holdout 양성 사례의 source envelope가 있다. `145 passed`.
이 수치는 model call 0건의 coverage 검사이지 fast20 점수가 아니다.

실제 observation system/user/schema를 조립한 별도 no-call audit도
`outputs/clean-native-v2-performance-task-v1/dev200/audit.json`에 남겼다.
200/200 exact tokenizer admission, 최대 10,897토큰, gold e2 7/7이다.
short·attachment·longest 메시지를 직접 읽었다. longest 사례에서는
과업 실적과 제안 평가 실적이 참가자격과 구분되어 있어야 함을 확인했다.
v2 semantic-input contract review는
[`clean_exp_n007_v2_semantic_input_review.md`](clean_exp_n007_v2_semantic_input_review.md)에
별도로 기록하며 아직 진행 중이다. 이 review와
manifest/preflight/mock/decision-result 검증이 완료되기 전 paid fast20은
실행하지 않는다. 현재 점수는 아직 없다.
