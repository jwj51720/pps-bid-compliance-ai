# Source-first shared execution refactor result

작성: 2026-09-11, dev / mac

## 결론

EXP171의 정책 조립 중 로컬 pipeline과 submission script에 중복돼 있던 사실 inventory
parse, 원문 substring 검증, document-id 연결·중복 제거, final exact-token packing을
`src/pipeline.py`의 공용 경로로 통합했다. submission에는 global batch scheduling, retry와
record-index 대응만 남겼다.

이 변경은 입력 내용이나 판정 정책을 바꾸지 않는다. source scope, category cap, prompt,
schema, call topology, merge, evidence, frozen postprocess 모두 그대로다.

## 공용 계약

- `collect_validated_fact_inventory(...)`
  - malformed pack은 빈 contribution으로 처리
  - 다른 pack의 유효 후보는 보존
  - 원문에 없는 문자열은 제거
  - whitespace variant는 실제 원문 span으로 복원
  - 원 문서 `doc_id`에 연결하고 중복 제거
- `BaselinePipeline.fact_inventory_final_plan(...)`
  - navigation을 advisory context로 추가
  - 모든 제공 source를 exact tokenizer budget으로 다시 admission
  - local과 submission이 동일한 context/message plan 사용

## 검증

- shared aggregation 단위 검증: PASS
- malformed 독립성 및 hallucinated excerpt 제거: PASS
- 기존 직접 구성과 final contexts/messages byte-equal: PASS
- full pytest: `192 passed`
- fresh archive: `dist/pps_20260911_161652.zip`
- exact staged entrypoint mock, organizer test sample 10건:
  - input 10 notices / 23 documents
  - stage 1 15 requests / final 15 requests
  - retry 0 / unrecovered pass 0
  - 10 rows / 49 columns / 10 unique IDs / evidence validation PASS
  - output: `outputs/_tmp_exp171_shared_staged_mock/submission.csv`

## 제한

fresh archive는 구조 parity 확인용인 현재 root canonical EXP171이다. EXP171은 public에서
120분 timeout이 이미 발생했고, 현재 root에는 EXP197의 human-readable metadata 교정이나
EXP198의 model-owned label 정책이 승격되지 않았다. 따라서 이 archive의 기술 검증을
재제출 권고 또는 runtime 해결로 해석하지 않는다.
