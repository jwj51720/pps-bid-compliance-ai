# Source-first shared execution refactor plan

작성: 2026-09-11, dev / mac

## 문제

로컬 `predict_with_fact_inventory_then_full_final()`과 submission의 batched
`_source_first_full_final_rows()`가 같은 정책을 의도하지만 다음 로직을 별도로 구현한다.

- inventory JSON parse/malformed fallback
- 원문 substring 검증과 doc-id 연결·중복 제거
- navigation이 붙은 final message 생성
- exact-token final context packing

배치 실행 자체는 runtime adapter 책임이지만 위 네 가지는 shared inference policy다. 중복 구현은
한쪽만 수정될 때 실험/제출 불일치를 만든다.

## 변경 계약

`src/pipeline.py`에 두 개의 판단 중립 API를 둔다.

1. `collect_validated_fact_inventory(...)`: record별 source/completion을 받아 기존 parser와
   `_clean_evidence`로 변경 없는 substring만 수집하고 parse error를 반환한다.
2. `fact_inventory_final_plan(...)`: inventory를 advisory section으로 붙이고 exact tokenizer로
   모든 source를 final contexts/messages에 admission한다.

로컬과 submission은 같은 API를 사용한다. submission에는 global pending list와 batch call,
retry, 결과의 record-index 대응만 남긴다. prompt, schema, category cap, source scope, merge,
evidence, label, postprocess, call topology는 바꾸지 않는다.

## 검증

- 동일 record/source/completion에서 local/shared aggregation 결과가 동일
- malformed는 빈 contribution이며 다른 pack을 지우지 않음
- final plan의 context/message가 기존 직접 구성과 byte-equal
- local/submission mock call cardinality와 49열 결과
- exact staged ZIP mock 및 full pytest
