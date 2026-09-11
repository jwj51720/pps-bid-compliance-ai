# EXP196: EXP171 입력 의미 완결 통합 계획

작성: 2026-09-11, dev / mac

## 목적

EXP171의 source-first/full-final 구조를 유지하면서 Astra 감사에서 확인되고 각각 독립적으로
수정된 세 입력 결함을 한 후보에서 통합한다.

1. 제품 exact-code 매칭 행의 `특이사항`과 사람이 읽을 수 있는 코드 출처를 final에 전달한다.
2. 주최 측 README의 익명화 토큰 의미를 stage-1과 final의 모든 admitted pack에 전달한다.
3. 국가·지방 제한입찰을 지방 소액수의 선행조건으로 잘못 좁힌 v6·v7 카드를 교정한다.

이 실험은 세 변경의 개별 인과효과를 추정하는 ablation이 아니라, 알려진 입력 결함을 모두
제거한 end-to-end integration candidate다. 개별 효과는 EXP192–195 결과로 따로 관리한다.

## 기준과 허용 변경

- `experiment.base_config`: `configs/config.exp179-source-first-full-final-repeat-fast-panel-c4.yaml`
- `experiment.allowed_policy_changes`:
  - `prompt.decision_cards_path`
  - `prompt.competition_product_context_mode`
  - `prompt.organizer_input_semantics_mode`
- 고정: source-first 7범주, full-source final, 문서 범위·순서, output schema, merge,
  frozen historical rule, model/provider 파라미터, concurrency

## 입력 계약

- 카드: `decision_cards_v10_v6_v7_scope.json`
- 제품: `competition_products_v1.json`, `conditions_and_provenance_v2`
- 익명화 의미: `anonymization_v1`
- 원문: 제공된 공고문·규격서·과업지시서·제안요청서·예외공표서 전부
- metadata: active v에 필요한 human-readable official lines만 사용
- raw metadata JSON, internal status/code array, 법령 원문·법령 bundle·case RAG는 넣지 않는다.

## 유료 실행 전 gate

1. preflight에서 위 세 변경 외 차이 0
2. dev200 complete-fact admission에서 제공 source omission 0, metadata/card/제품/익명화 누락 0
3. 조건부 제품 매칭 35건의 모든 final pack에 `특이사항` 전달
4. exact tokenizer admission과 call topology 기록
5. short complete, attachment, overflow, 지역 익명화, 조건부 제품 사례의 실제 rendered message 검토
6. 24-v semantic-input contract PASS
7. fast20 mock과 49열·ID·evidence validation PASS

fast20 결과는 통합 후보의 실행 가능성과 회귀 신호만 본다. 세 변경이 함께 있으므로 headline
차이를 어느 한 변경의 효과로 귀속하지 않는다. fast gain이 확인돼야 holdout20으로 확장한다.
