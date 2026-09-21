# EXP-C002RB v24 distinct serialization 계획

작성일: 2026-09-21

결과: **one-record probe 실패**. whitespace loop는 제거돼 `finish_reason=stop`, completion 416이었지만
exact duplicate와 unit/role semantic 오류로 local contract가 fallback했다. fast20 전체는 실행하지
않았다. 상세 결과는 `docs/clean_exp_c002rb_v24_serialization_probe_result.md`에 기록한다.

## 목적

C002R fast20의 유일한 fallback은 response가 첫 `value_won` 앞에서 whitespace를 반복해
`max_completion_tokens=1536`에 도달한 serialization failure였다. 또한 정상 response 여러 개가
동일 `source_id/role/value`를 최대 8회 반복해 completion을 낭비했다.

C002RB는 v24 source view와 reducer v2.1의 판단식을 고정하고 response serialization contract만
좁힌다. 먼저 기존 length failure 1건만 diagnostic probe로 실행한다. probe 성공은 품질 성능으로
보고하지 않으며 fast20 전체 실행 승인과도 구분한다.

## base와 허용 변경

- base manifest:
  `experiments/manifests/clean_exp_c002ra_v24_code_provenance_replay_v21.json`
- fixed view:
  `all-documents-table-aware-balanced-exact-windows-v2`
- fixed reducer semantics:
  `field-level-four-digit-code-provenance-v2.1`
- allowed policy changes:
  - `layers.decisions`
  - `layers.assembly`
  - `v24_policy`
- provider/model/temperature/max completion/seed/tokenizer budget: 변경 없음
- diagnostic probe ID: C002R에서 `finish_reason=length`였던 단일 response ID
- performance labels: probe에서 읽지 않음

## serialization-only 변경

1. amount `value_won`: free string/null → non-negative integer/null
2. source ID: free short string → 해당 axis에 실제 제공된 candidate ID enum
3. industry code: free string → exact 4-digit string pattern
4. observation array `maxItems`: 8 → 4
5. system output contract에 동일 `source_id + role + canonical value` 중복 금지 명시
6. final `y`, different, mismatch field는 계속 없음

새 output을 adapter가 C002RA reducer의 기존 atomic representation으로 변환한다. adapter 이후
금액·계약·지역·업종 판단식은 변경하지 않는다.

배열 상한 4는 다음 semantic contract를 따른다.

- 같은 canonical 값의 반복 문구는 하나만 출력한다.
- 서로 다른 공식 값은 최대 4개까지 각각 보존한다.
- source 후보가 4개보다 많다는 이유로 후보를 4개만 보는 것이 아니다. 입력 후보는 동일하고
  output의 distinct official atomic values만 제한한다.

## 단계 1: one-record diagnostic probe

새 manifest는 `diagnostic_probe.ids`에 length failure ID 하나를 versioned config로 둔다.

사전 조건:

- active manifest preflight PASS
- exact source/provenance PASS
- exact tokenizer admission PASS
- actual rendered system/user/schema 사람 검토
- mock structured output parse/reducer PASS

성공 조건:

- external calls: 1
- `finish_reason=stop`
- completion tokens < 1536
- parse/reducer fallback 0
- source IDs 모두 axis-matching enum
- amount integer adapter 이후 exact semantic value 보존

실패하면 원인을 기록하고 전체 fast20을 실행하지 않는다.

## 단계 2: fast20 전체 재실행 gate

단계 1을 통과한 뒤 별도 승인 문서를 남기고 20건 전체를 새 serialization로 실행한다.

- fallback 0
- v24 TP >= 1
- v24 FP <= 3
- 다른 v/e 변경 0
- v24 positive without evidence 0

이 gate를 통과해야만 independent holdout20으로 간다. probe 또는 fast20 일부 결과를 완결 전략의
성능으로 부르지 않는다.

## 금지

- known FP/FN ID나 고유 문구의 예외 rule
- source selector term 변경
- reducer threshold/axis 변경
- invalid output을 positive로 복구
- fallback을 baseline label로 대체
- 기존 response와 새 response를 notice별 성능이 좋아지는 방향으로 선택
