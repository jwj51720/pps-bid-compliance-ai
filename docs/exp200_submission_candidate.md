# EXP200 corrected-input submission candidate

작성: 2026-09-11, dev / mac

## 목적과 선택

사용자 요청에 따라 EXP200 repaired 정책을 현 시점 제출 후보로 패키징한다. 이 후보는
EXP171의 source-first/full-final 구조를 유지하면서 확인된 입력 의미 누락을 교정한다.

- cards: `decision_cards_v10_v6_v7_scope.json`
- competition product rendering: `conditions_and_provenance_v2`
- organizer input semantics: `anonymization_v1`
- metadata: `official_lines_human_v2`
- staged mode: `fact_inventory_full_final_v1`
- final은 navigation과 tokenizer-admitted 원문 전체를 다시 읽는다.
- v-item grouping은 사용하지 않는다.
- postprocess는 재현된 EXP200 점수와 동일한 historical `exp123_v1`을 유지한다.

`config.yaml`과 `submission/runtime_config.json`을 위 정책으로 일치시킨 후, 패키징
검사와 exact staged mock을 수행한다.

## 근거와 한계

EXP200 repaired dev200 macro positive-F1은 `.324798`로 EXP171 `.307962`보다
`+.016836` 높았다. 다만 frozen rule 전 모델 자체 점수는 `.249542`로 EXP171
`.250070`보다 소폭 낮다. 따라서 상승을 입력 교정만의 안정적 모델 개선으로 해석하지 않는다.

예상 topology는 stage 1 217 + final 221 = 438 calls이다. 435 calls였던 EXP171 제출이
120분 제한을 초과했으므로 이 후보도 evaluator runtime 위험이 높다. 로컬 환경에는 대회
GPU/vLLM이 없어 실제 runtime 성공을 검증할 수 없다. 이 패키징은 정책·입력·출력 완결성
검증이며 2시간 내 실행 가능성을 보증하지 않는다.

## 패키징 결과

- ZIP: `dist/pps_20260911_185826.zip`
- SHA-256: `5836c52e361672488ce3ee85555ddd249257598088bd1c5ad7fef802706cef7f`
- compressed size: 108 KiB
- archive: 27 files, 501,434 uncompressed bytes
- runtime batch size: 128
- static assets: corrected decision cards와 competition-product index 포함 확인
- exact ZIP extraction mock: organizer-format 10 records / 23 documents
- mock topology: stage 1 15 requests + final 15 requests
- output: 10 rows / 49 ordered columns / ID·label·evidence validation PASS / warning 0
- preflight: controlled difference 0, required artifacts present
- focused tests: 110 passed
- full tests: 198 passed

실제 대회 GPU/vLLM 실행은 이 환경에서 수행하지 않았다. 따라서 archive는 제출 가능한 형식과
정책 일치는 검증됐지만, 120분 runtime 제한 통과는 미검증이다.
