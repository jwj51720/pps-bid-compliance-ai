# Clean reference L41 dev-200 baseline plan

작성일: 2026-09-21

## 목적

`docs/cleanroom_rearchitecture_plan_v1.md`의 B2 frozen-reference 단계다. 제공받은
`dist/reference/submit.zip`의 판정 알고리즘, prompt, schema, item ownership을 변경하지 않고
새 `src/pps_ai` 계층을 통해 dev 200건을 실행한다. 점수 개선 실험이 아니라 새 실행기의
무결성과 참고 baseline의 로컬 점수를 확립하는 실험이다.

## 고정 정책

- reference ZIP SHA-256:
  `a06feff77ffbc4a6f2a47cd0e2d322f341f652ca865d1b9cf53919012c8ca216`
- L41 arms: `r10`, `B`, `C24`; 공고당 정확히 3 logical calls
- L41 FactBuilder, semantic section pool, deterministic solver, last-writer 순서 보존
- BGE-M3 catalog top-10 retrieval 보존
- Gemma temperature 0, seed 20260826, max completion 1,536
- OpenRouter transport concurrency 8, global request-start interval 1초
- exact local Gemma chat template, prompt budget 14,848
- V를 evidence 실패로 변경하지 않음

## 로컬 실행 차이와 제한

참고 제출은 evaluator vLLM의 `int8_per_channel_weight_only`를 사용한다. 이 Mac에는 전체 Gemma
weights와 vLLM이 없으므로 LLM/BGE transport만 OpenRouter로 바꾼다. 따라서 결과는
`clean-reference-l41-openrouter-dev200-v1`이며 참고 제출의 public 0.7+나 evaluator runtime을
재현했다고 부르지 않는다. provider 차이는 유일하게 의도한 실행환경 차이다.

최초 local transport 설정의 concurrency 64는 393/600 응답 이후 OpenRouter 계정의
`in_flight_budget_exhausted` 402를 일으켰다. 완료 checkpoint는 보존했다. 이 오류는 판정 정책이
아니므로 concurrency를 8로 낮추고 해당 402의 `Retry-After`만 transport 재시도 대상으로
추가했다. prompt, schema, generation parameter, item owner에는 변화가 없다.

## 계층과 소유권

새 코드는 역사적 `src.pipeline`, `src.prompt`, `src.config`를 import하지 않는다.

1. strict organizer JSONL ingest
2. immutable document hash/source ledger
3. frozen L41 F1–F6 fact module
4. frozen L41 semantic section view module
5. label-blind BGE-M3 retrieval
6. r10/B/C24 decision modules
7. explicit 24-item final-owner contract
8. evidence validator with zero label mutations
9. 49-column export and dev/fast20/holdout20 evaluator
10. task/token/input/asset hash artifact ledger

알려진 v4 예외 무시, 공고문-only deterministic rule, arm fail-closed 등 reference 결함은 baseline
parity를 위해 고치지 않는다. `docs/reference_submit_l41_analysis_20260921.md`의 known defects로
남기며 후속 corrected experiment에서 한 번에 하나씩 바꾼다.

## paid-run gate와 2026-09-21 사전검증 결과

1. 200 input IDs와 label IDs exact join
2. 24개 final owner 정확히 하나씩
3. 600 tasks exact coverage
4. 모든 task <=14,848 tokens
5. short, attachment, largest-prompt rendered messages export 및 사람 검토
6. BGE ranking은 label-blind이고 200 rows/top-10
7. exact staged mock 10건과 failure/assembly tests
8. OpenRouter key 존재 확인
9. output directory와 response checkpoint 격리

실행 전 새 경로만 사용한 full-dev mock에서 다음을 확인했다.

- dev input/label ID exact join을 유료 호출 전에 검사하도록 실행기에 고정했다.
- 200 records, `r10/B/C24` 600 tasks, final owner 24개를 확인했다.
- arm별 최대 prompt token은 `r10=11,590`, `B=10,399`, `C24=6,831`로 모두
  14,848 이하이며 truncation은 없다.
- 200행 49열 mock CSV, binary V, ID 순서, evidence 무라벨변경 계약을 통과했다.
- 사람 검토 파일은 다음과 같다.
  - `outputs/clean-reference-l41-openrouter-dev200-v1-mock/rendered_inputs/short_PPS-DEV-077.json`
  - `outputs/clean-reference-l41-openrouter-dev200-v1-mock/rendered_inputs/attachment_PPS-DEV-01.json`
  - `outputs/clean-reference-l41-openrouter-dev200-v1-mock/rendered_inputs/largest_prompt_PPS-DEV-143.json`
- 세 표본 모두 system contract, F facts, semantic source IDs/원문 span, C24 exact meta가 실제
  message에 렌더링됐다. attachment 표본은 공고문 외 문서 span을 포함한다.
- source view가 foreign document를 참조한 경우는 0건이다. 단, 5개 공고는 제공 첨부 중 일부가
  어느 semantic section candidate도 만들지 못했다. 이는 파일 누락이나 tokenizer truncation이
  아니라 frozen L41 selector의 recall 한계다. baseline parity 실험에서는 고치지 않고 결과의
  limitation으로 기록한다.

24개 항목별 최종 owner와 입력 계약은
`docs/clean_reference_l41_semantic_contract_20260921.md`에 별도로 고정한다.

## 결과 기록

`outputs/clean-reference-l41-openrouter-dev200-v1/`에 manifest hash, preflight, rendered inputs,
BGE rankings, 600 raw responses, submission, dev/fast/holdout per-item metrics, fallback/evidence/runtime
report를 남긴다. 실행 중단 시 완료된 `(arm,id)` response만 resume한다.
