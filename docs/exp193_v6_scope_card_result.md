# EXP193: v6 적용범위 카드 결과

작성: 2026-09-11, dev / mac

## 결론

국가·지방 시행규칙 제25조를 다시 추적한 결과, 기존 card v6의 `지방
소액수의` 선행 적용조건은 출처가 지지하지 않는다. 이 범위 오류를 v6 하나에서
바로잡은 `decision_cards_v9_v6_scope.json`은 출처 정합성 개선이다.

하지만 Gemma fast20은 EXP169 `.262500`에서 EXP193 `.224306`으로 하락했고,
v6은 `TP 0 / FP 1 / FN 1`이었다. 기초자치단체 제한이 익명화 토큰으로
나온 DEV072를 놓치고, 광역 단위 두 지역을 나열한 DEV039를 v6으로 잘못
판정했다. 범위 교정만으로는 지역 단위와 v6/v7 관계를 모델이 안정적으로
재구성하지 못했다.

## 실행·검증

- config: `configs/config.exp193-v6-scope-card-fast-panel-c4.yaml`
- output: `outputs/exp-193-v6-scope-card-fast-panel-c4/`
- cohort: `configs/dev_fast_panel_v1.json`, 20건
- call: 23
- runtime: 46.874초
- parse error: 0
- semantic-input contract: 24/24 PASS
- target v6: gold 1, predicted positive 1, TP 0, FP 1, FN 1, F1 0

전체 12 cell이 바뀌었고 v6 외 변경이 다수였다. 이들은 단일 card 변경이
원인이라고 단정할 수 없으며, target v6의 동일-ID 결과와 off-target 변동을 분리해
보고해야 한다.

## 추가로 확인된 입력 결함

주최 측 `data/raw/open/README.md`는 다음을 명시한다.

- `[지역:r1|단위=기초|광역=경기도]`에는 지역 계층이 보존된다.
- `단위=기초`는 기초자치단체 단위임을 알려준다.
- 같은 문서의 `r1`과 `r2`는 서로 다른 지역이다.

현재 rendered prompt에는 이 표기 규약의 설명이 없다. DEV072의 원문은
`단위=기초`를 포함하지만 모델은 그 의미를 명시적으로 제공받지 못했다.
따라서 EXP193은 승격하지 않고, 카드 문구에 README 사실을 숨겨 섞기보다
주최 측 입력 표기 규약을 별도의 versioned context로 전달하는 실험을 먼저 한다.
