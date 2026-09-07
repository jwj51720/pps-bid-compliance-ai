# Execution-contract audit A0 결과

계획: [execution_contract_audit_plan.md](execution_contract_audit_plan.md)

## 확인한 결함과 수정 상태

historical EXP109/staged tree는 organizer baseline과 달랐다. metadata를 JSON block으로 렌더했고,
submission entrypoint도 `metadata_style`/`item_catalog_style`을 pipeline으로 전달하지 않았다.
이는 historical 결과를 소급 수정하지 않고, source와 canonical runtime만 수정했다.

현재는 다음 regression test가 이 계약을 고정한다.

- `tests/test_pipeline.py::test_canonical_official_baseline_prompt_matches_organizer_baseline`:
  같은 dev record의 system/user message가 organizer `baseline/script.py`와 byte-level로 일치한다.
- `tests/test_submission.py::test_submission_runtime_forwards_official_baseline_metadata_style`:
  submission runtime의 `official_lines` metadata가 shared pipeline으로 실제 전달되고 JSON으로
  fallback하지 않음을 확인한다.

## Fresh staged zip 검증

`python scripts/make_submission.py`로 fresh staging과
`dist/pps_20260907_111636.zip`을 만들었다. 이 zip은 이전 stale staged tree가 아니라 현재
`submission/script.py`, `runtime_config.json`, `src/`, requirements에서 생성됐다.

| 확인 | 결과 |
| --- | --- |
| canonical prompt policy = runtime policy = zip runtime policy | 일치 |
| zip source files | 18개, `src/` 전체 포함 |
| fresh staged entrypoint mock | 성공 |
| PPS sample input | 10/10 records 처리 |
| malformed JSON retry / unrecovered pass | `0 / 0` |
| `submission.csv` | 49 columns, source-evidence validation 통과, warnings 0 |
| regression tests | pipeline/submission/config/experiment-control 59 passed |

## 의미와 한계

이 결과는 **제출 재현성 결함을 고친 것**이지, 새로운 성능 향상 실험이 아니다. exact organizer
prompt의 fast-20 EXP122A는 historical JSON EXP109 subset보다 낮았고, provider variation이 섞인
작은 cohort이므로 current source contract를 dev200 성능 우위라고 주장하지 않는다.

반대로, 앞으로 historical EXP109의 local score를 “exact organizer baseline”이라고 부르면 안 된다.
새 policy의 생성 실험은 이 fresh staged contract를 control로 삼아야 하며, output schema, metadata
renderer, evidence resolution, tokenizer admission, decoder가 우연히 같이 바뀌는 일을 금지한다.

## 다음 결정

S0C self-label precedent는 source-fact localization AUC 0.521로 중단했고, A0는 execution parity를
확정했다. 이제 생성 호출을 하기 전 남은 안전한 큰 작업은 동료의 0.32734 source/zip을 확보할 수
있는지 확인하는 것이다. 그것을 받을 수 없다면 새 prompt experiment는 exact current control에서
**한 가지 내용 변화만** 선언한 independent fast cohort로 시작해야 한다. Law RAG, casebook RAG,
item-level override, full-split×grouping은 다시 열지 않는다.
