# EXP192: 경쟁제품 조건·출처 전달 복구

작성: 2026-09-11, dev / mac

## 목적

`competition_products_v1.json`에 보존된 주최 측 CSV의 `특이사항`과 exact-code 발견
출처가 현재 model-facing fact에서 사라지는 결함을 고친다. Python은 조건을 해석하거나
경쟁제품 적용 여부를 결정하지 않는다. 모델이 제품 행의 조건, 실제 구매대상, 금액 및
공고 원문을 대조할 수 있도록 사람 친화적 사실만 전달한다.

이 실험은 카드, 원문 범위, output schema, merge, 모델 파라미터 및 후처리를 바꾸지 않는다.

## 가설

조건부 제품을 단순히 `고시에 등재`되었다고 렌더링하면 v10–v18의 경쟁제품/일반제품
분류가 잘못 고정될 수 있다. 다음 정보를 손실 없이 전달하면 조건부 행에서 분류 오류가
줄고, 조건이 없는 행의 기존 판단은 보존될 것이다.

- 매칭 제품명
- 주최 측 CSV 행의 `특이사항` 원문 또는 `별도 적용조건 없음`
- exact code가 나라장터 세부품명 목록, 어느 문서 유형, 또는 양쪽에서 확인됐는지
- exact-code 일치는 행을 찾은 사실이며 실제 적용은 조건과 구매대상을 대조해야 한다는 설명

코드 번호, 내부 status, doc-id는 prompt에 노출하지 않는다.

## 변경 통제

EXP192 fast20:

- `experiment.base_config`: `configs/config.exp169-complete-source-2500-fast-panel-c4.yaml`
- `experiment.allowed_policy_changes`: `prompt.competition_product_context_mode`
- 변경값: `names_only_v1` → `conditions_and_provenance_v2`

후속 holdout20은 EXP170, dev200은 EXP172를 각각 base로 하며 같은 필드만 변경한다.
fast20은 반드시 `configs/dev_fast_panel_v1.json`을 사용한다.

## 구현 계약

1. `load_competition_product_index()`는 제품명과 `특이사항`의 문자열 형식을 검증한다.
2. `competition_product_fact()`는 매칭된 제품의 CSV 행 사실과 metadata/document provenance를
   보존한다. 기존 audit용 필드도 유지한다.
3. `names_only_v1`은 역사적 실험 재현을 위해 기존 렌더링을 그대로 유지한다.
4. `conditions_and_provenance_v2`만 조건·출처를 렌더링한다.
5. 조건 적용, 금액 비교, 구매대상 관계, 최종 v는 Gemma가 카드·metadata·원문과 함께 판정한다.
6. 제품 조회 사실은 evidence가 아니며 e에는 사용하지 않는다.

## 사전 검증

- unit test: 조건/무조건 제품, metadata-only, document-only, 양쪽 출처, 코드/status/doc-id 비노출
- 과거 mode 회귀: `names_only_v1` 메시지 불변
- exact tokenizer admission 및 source coverage profile
- exact rendered messages:
  - short complete: fast panel에서 선정
  - attachment: fast panel에서 선정
  - overflow: dev200에서 선정
  - 조건 경계 반례: `PPS-DEV-054`
- 24개 semantic-input contract audit
- 조건부 매칭 35개 공고에서 모든 `특이사항`이 실제 final message에 존재하는 별도 delivery audit
- mock 실행 및 isolated output
- `scripts/preflight_experiment.py`에서 선언 외 차이 0개

fast20의 조건부 매칭은 `PPS-DEV-199`, `PPS-DEV-169` 두 건이며 둘 다 10억원 미만 조건을
충족한다. 따라서 fast20은 회귀·형식·부작용 gate이지 조건 경계의 충분한 성능 검증이 아니다.
holdout20에는 조건부 매칭 4건이 있으며 금액 외 제품 속성 조건도 포함한다. 조건 경계의
방향성은 별도 diagnostic panel로 보고하고 fast20 결과로 과장하지 않는다.

## 승격 기준

fast20에서 malformed/evidence/source coverage 회귀가 없어야 한다. 그 뒤 동일 변경만 적용한
holdout20으로 확인하고, 두 결과가 허용 가능한 경우에만 dev200을 실행한다. 점수 외에 v10–v18
TP/FP/FN, 조건부 공고별 변화, parse error, call 수, runtime을 함께 기록한다. canonical 및
submission 설정은 dev200과 runtime 검증 전에 변경하지 않는다.
