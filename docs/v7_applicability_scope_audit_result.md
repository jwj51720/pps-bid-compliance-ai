# v7 적용범위 독립 감사 결과

작성: 2026-09-11, dev / mac

## 결론

기존 card v7의 `v6의 지방 소액수의 적용 유형` 선행조건은 주최 측 항목표와 배포 법령
원문이 지지하지 않는다. 국가·지방 제한입찰의 인접 지역 확대 규정이 기본 적용영역이고,
지방 2인 이상 견적 수의계약은 인접 확대를 명시적으로 허용할 수 있는 별도 계약영역이다.

`decision_cards_v10_v6_v7_scope.json`은 v9에서 v7만 바꾼다. Python 지역 판정이나 label
override는 추가하지 않았다.

## 출처 판정

- 국가계약 시행규칙 제25조제3항: 시·도 관할구역이 원칙이며, 현장·납품지가 인접 시·도에
  걸치거나 적격자가 10인 미만일 때 인접 시·도를 포함할 수 있다.
- 지방계약 시행규칙 제25조제3항: 시·도 관할구역이 원칙이며, 현장이 걸친 경우,
  인접 지역에 납품지·관리시설이 있는 경우, 적격자가 10인 미만인 경우 등을 허용한다.
- 지방 수의계약 운영요령: 2인 이상 견적 수의계약에서는 관할 시·군과 인접 시·군·자치구,
  관할 시·도와 인접 시·도의 제한을 명시적으로 허용한다.

따라서 비고 `지방 + 소액수의 가능`은 전체 적용 전제가 아니라 허용 여부를 판단할 때
확인할 별도 분기다.

## EXP195 검증

- config: `configs/config.exp195-v7-scope-card-fast-panel-c4.yaml`
- base: EXP193; 허용 차이는 `prompt.decision_cards_path` 하나
- card artifact 재생성 일치: PASS
- exact tokenizer: 20건, 23 calls, 18×1 pack·1×2·1×3
- dev200 제공 source 374개 omission 0, metadata/card omission 0, over-budget 0
- semantic-input contract: 24/24 PASS
- short/attachment/overflow/v7 관련 rendered message 검토: PASS
- mock 20건, 49열·ID·evidence validation: PASS
- 실제 runtime: 48.599초
- parse error: 0
- macro positive-F1: EXP193 `.224306` → EXP195 `.241667` (`+.017361`)
- v7: 양성 2건에 `TP 0 / FP 0 / FN 2`, changed cell 0
- off-target changed cell: 7개(교정 6, 회귀 1)

## 판정

v7 카드의 출처 정합성 오류는 교정했다. 그러나 target v7은 전혀 움직이지 않았고 headline
상승은 모두 off-target 호출 변동에서 왔으므로 성능 개선 증거로 승격하지 않는다. 이는
v7의 다음 병목이 적용범위 문구 자체가 아니라 기준 지역↔추가 지역 관계, 인접성, 허용 사유를
원문에서 연결하는 단계일 가능성을 높인다. 관계 추출을 시도한다면 v7 하나의 source-only
사실 정확도부터 측정해야 한다.
