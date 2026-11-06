# A0 실행 계약 audit 결과 v1

실행일: 2026-09-10 (dev / mac)  
계획: [execution_contract_audit_plan.md](execution_contract_audit_plan.md)

## 범위

이 audit은 성능 실험이나 제출 성능 후보 선정이 아니다. 현재 tracked canonical source가
공식 형식 단일-call control을 실제 submission zip까지 같은 정책으로 전달하는지 확인했다.
모델 추론과 네트워크 호출은 하지 않았다.

## 확인한 policy

| 항목 | 확인 값 |
| --- | --- |
| canonical config | `final-exp125a-exact-organizer-control-v1` |
| prompt profile | `official_baseline_v1` |
| document context | `single`, 4,000 characters, overflow split off |
| output | all-item V/E |
| submission grouping | 없음 (`all`) |
| submission batch default | 64 |

`scripts.make_submission.verify_runtime_policy()`는 `config.yaml`과
`submission/runtime_config.json`의 policy fields 및 grouping을 비교해 **PASS**했다.
이 결과는 runtime이 current root policy를 읽는다는 뜻이지, EXP123이나 source-first 같은
historical experiment를 canonical으로 승격한다는 뜻은 아니다.

## 공식 baseline/source parity

다음 회귀 검사를 실행했다.

```text
.venv/bin/python -m pytest \
  tests/test_pipeline.py::test_exact_organizer_control_prompt_matches_organizer_baseline \
  tests/test_submission.py::test_submission_runtime_forwards_official_baseline_metadata_style \
  tests/test_config.py -q
```

결과: **9 passed**.

이는 current exact-control prompt가 organizer baseline의 system/user message contract와
맞고, submission pipeline도 `official_lines` metadata renderer를 실제로 forward함을
검증한다. 과거 EXP109의 metadata JSON forwarding 결함은 current source contract에 없다.

## Fresh staged zip 및 mock

기존 `submission/build/`의 historical directories는 건드리지 않았다. 새 canonical staging
directory `submission/build/final_exp125a_exact_organizer_control_v1/`만 생성했다.

| artifact | 값 |
| --- | --- |
| archive | ignored `dist/pps_20260910_092208.zip` |
| SHA-256 | `573e1a3a566ff19c1347af80fa01b9fe8d66f2ff64c0c0c87e9f32bc1a538caf` |
| zip entries | 25 files: `script.py`, `runtime_config.json`, `requirements.txt`, shared `src/` |
| cards/products static asset | canonical control이 사용하지 않으므로 zip에 없음 |

Staged `script.py`를 temporary `PPS_DATA_DIR`, `PPS_OUTPUT_DIR`, `PPS_MODEL_DIR` contract로
10 notice `--mock` 실행했다. 결과는 다음 모두 PASS다.

- malformed structured retry 0, unrecovered fallback 0
- `submission.csv` 10 rows, unique IDs
- ordered 49 columns (`id`, `v1..v24`, `e1..e24`)
- 모든 v 값 binary
- e10/e11/e16/e18/e20 blank
- UTF-8/NFC validation

## 파일 provenance snapshot

| file | SHA-256 |
| --- | --- |
| `config.yaml` | `6bef775f23c229ea77eb397ff2cfab8bdc492f362ea7c42a2735fb1c8d6e3a90` |
| `submission/runtime_config.json` | `8364717890adafe0ecc6883c88a2a854ba36b65e3432f8378d9aa150398dc16a` |
| `submission/script.py` | `a4c6e734f3861888760f38b4e3fbecf8c83e74620e1b584249f4fb06732d18f0` |
| organizer `baseline/script.py` | `3f410ee6f7c24da25ba25e9bef2501b7715222cfb047363fbe8ab5b57fd17fbb` |

## 결론과 다음 단계

A0가 current exact organizer control의 stale-stage/metadata-forwarding 결함을 발견하지
않았으므로, 이를 local/public 성능차의 설명으로 사용하지 않는다. 현재 source-first의
quality signal과 독립적인 **실행 계약은 검증됐다**.

다음 broad architecture exploration은 canonical submission을 바꾸지 않은 versioned
candidate에서만 진행한다. 이미 기각된 law/case RAG, item partition, raw V-only, full-split
multiplication을 되풀이하지 않고, source-first v1의 attention benefit을 설명할 수 있는
새로운 source-observation operation이 semantic-input contract와 exact rendered-input gate를
통과할 때만 paid fast20으로 진행한다.
