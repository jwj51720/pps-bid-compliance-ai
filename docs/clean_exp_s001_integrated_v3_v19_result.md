# EXP-S001 v3/v19 통합 실행 결과

작성일: 2026-09-22

상태: PASS — stored-response dev200 조합 검증 및 별도 submission ZIP 생성

## 품질 결과

| cohort | Macro positive-F1 |
|---|---:|
| fast20 | 0.7277777778 |
| holdout20 | 0.4305555556 |
| dev200 | **0.8151465658** |

- dev200 200행 × 49열
- C005D final과 다른 cell: 0
- v3: TP 8 / FP 1 / FN 0, F1 `0.9411764706`
- v19: TP 6 / FP 4 / FN 0, F1 `0.75`
- v3/v19 task hash: 기존 실제 Gemma 응답과 모두 MATCH
- v3 최초 invalid 2건은 저장된 attempt 1에서 모두 회복
- v19 semantic-invalid: 0
- v19 positive evidence 미해결 2건은 B fallback을 보존

이 점수는 새로 OpenRouter를 호출한 결과가 아니다. 동일 prompt/task의 기존 실제 응답을 task hash로
검증한 뒤, 새 실행 구조의 owner 결합식을 적용한 replay다. 따라서 품질 조합은 검증됐지만 evaluator
vLLM wall time을 검증한 결과는 아니다.

## 호출 topology와 입력 감사

dev200 initial logical calls:

| owner | calls |
|---|---:|
| r10 | 200 |
| C24 | 200 |
| v19 owner: native 또는 B 중 하나 | 200 |
| conditional v3 specialist | 61 |
| 합계 | **661** |

v19는 기존 B 200회 위에 native 165회를 더하는 765+ 구조가 아니다. candidate 165건은 native가
초기 owner이고, no-candidate 35건만 B가 초기 owner다. dev 응답과 같은 unresolved가 발생한다면
B fallback 2회가 추가된다. batch size 128은 이 logical call 수를 줄이지 않는다.

저장 usage를 이 topology에 대입한 초기 token 근사치는 prompt `3,264,981`, completion
`230,481`이다. L41 3-arm보다 prompt는 약 9% 줄지만 specialist structured output 때문에 completion은
크게 늘어난다. 따라서 호출 수만 보고 2시간 이내라고 판단할 수 없다.

공급 문서 374개를 모두 selector에서 검사했다. 유형별 수는 공고문 201, 규격서 63,
과업지시서 53, 제안요청서 57이다. v3 exact window가 선택된 문서는 공고문 36,
제안요청서 27, 과업지시서 5이며, v19 exact window가 선택된 문서는 공고문 145,
규격서 16, 과업지시서 16, 제안요청서 48이다. 상세 token/call 감사는
`outputs/clean-exp-s001-integrated-v3-v19-v1/submission_preflight.json`에 있다.

rendered prompt와 semantic contract는 동일 task hash의 원 실험 산출물을 재사용했다.

- v3: `outputs/clean-exp-c004r-v3-keyed-full-fast-v11/dev200/rendered_inputs/`
- v19: `outputs/clean-exp-c005d-v19-dev200-promotion-v1/dev200/rendered_inputs/`
- base 3-arm: `outputs/clean-reference-l41-openrouter-dev200-v1/rendered_inputs/`

## 재시도·격리 계약

- 모든 task는 initial attempt 후 invalid인 task만 최대 2회 재시도한다.
- 정상 task는 재호출하거나 실패 task의 결과로 덮지 않는다.
- backend batch 예외는 재귀 이분하여 단일 실패 입력만 invalid placeholder로 격리한다.
- v3는 keyed semantic parser, v19는 requirement semantic parser, base arm은 JSON/schema 검증으로
  invalid를 결정한다.
- v3가 끝까지 invalid이면 r10 v3 cell을 보존한다.
- v19가 끝까지 invalid이거나 positive evidence를 원문에 resolve하지 못하면 그 공고만 B를 호출한다.
- run-level 예외에도 full-ID 49열 CSV를 쓰는 최후 안전 경로를 유지한다.

fault test에서 정상 task는 1회만 호출되고 실패 task만 총 3회(initial + retry 2) 호출됨을 확인했다.
batch exception test에서도 정상 응답이 보존됐다.

## 제출 파일

- 새 후보: `dist/pps_20260922_153225.zip`
- SHA256: `72e3c1d65ec342b3d58e1cc5f99ee0c4a9ccfb1972d111df0fa488a5a0fce4df`
- compressed size: 153,080 bytes
- staged archive mock: 10 records, 49 columns, unique IDs, PASS
- ZIP integrity: PASS
- submission batch size: 128
- invalid response retries: 2

기존 `dist/pps_20260922_145728.zip`은 변경하지 않았다. 그 SHA256은
`5cfe82085286b6c95179c419d4df4439a0b22bb098bd891143d12aeadc213af7`로 유지된다.

제출 ZIP에는 실행 코드, requirements, runtime config만 있으며 실험 계보·출처 설명 문서는 넣지
않았다. 계보 설명은 이 저장소 문서에만 둔다.

## 검증 명령

```text
python scripts/preflight_experiment.py --config experiments/manifests/clean_exp_s001_integrated_v3_v19_v1.json
python scripts/run_integrated_v3_v19_replay.py --config experiments/manifests/clean_exp_s001_integrated_v3_v19_v1.json
python scripts/package_integrated_submission.py
python -m pytest -q
unzip -t dist/pps_20260922_153225.zip
```

전체 pytest: 167 passed.

## 제한

이 후보는 dev200 품질 조합과 staged mock은 검증됐지만 실제 evaluator GPU/vLLM 2시간 wall-time은
검증하지 못했다. initial call 수가 661이고 두 specialist의 입력은 짧지만, 과거 600-call 후보도
2시간을 초과했으므로 timeout 위험은 여전히 크다. 품질 후보와 runtime-safe 후보를 동일시하면 안
된다.
