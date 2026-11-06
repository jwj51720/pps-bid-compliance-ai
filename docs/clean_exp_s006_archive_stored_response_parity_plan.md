# S006 — 제출 ZIP 저장응답 재실행 parity 감사 계획

상태: zero-call 실행경로 감사 계획

## 가설

S001의 dev200 `0.8151465658`은 clean experiment 조립기가 기존 OpenRouter 응답을 재생해
계산한 값이다. 실제 제출된 `dist/pps_20260922_153225.zip`은 별도의 self-contained entrypoint,
초기 B 라우팅, specialist invalid 재시도, 조건부 B fallback, evidence 정리를 수행한다.
동일한 dev200 원문·ranking·저장응답을 ZIP entrypoint에 주입했을 때 S001의 49열 결과와
완전히 같아야만 local-public 차이를 일반화 문제로 해석할 수 있다.

이 감사는 새 LLM/BGE 응답을 만들지 않는다. 제출 ZIP을 임시 디렉터리에 풀고 공개된
`run(..., runner_factory=..., ranking_builder=...)` 주입 지점으로 저장응답과 ranking을 공급한다.
제출물의 코드를 고치거나 active import root로 사용하지 않는다.

## 변경 통제

- base config: `experiments/manifests/clean_exp_s001_integrated_v3_v19_v1.json`
- allowed change: `archive_stored_response_parity_audit` 추가만
- LLM/BGE calls: 0
- output: `outputs/clean-exp-s006-archive-stored-response-parity-v1/`
- 비교 기준: `outputs/clean-exp-s001-integrated-v3-v19-v1/submission.csv`

## 입력과 저장응답

- archive: `dist/pps_20260922_153225.zip` (실행 전 SHA-256 고정)
- base r10/B/C24: `outputs/clean-reference-l41-openrouter-dev200-v1/responses/`
- v3 primary: `outputs/clean-exp-c004r-v3-keyed-full-fast-v11/dev200/responses/`
- v3 invalid-only recovery: `outputs/clean-exp-c004rr-v3-keyed-recovery-v1/response_attempts/`
- v19 primary: `outputs/clean-exp-c005d-v19-dev200-promotion-v1/dev200/responses/`
- retrieval: `outputs/clean-reference-l41-openrouter-dev200-v1/rankings.json`

응답은 task ID만으로 주입하지 않고 archive가 실제 만든 message와 schema의 canonical
fingerprint에 연결한다. 그러므로 ZIP의 prompt/task가 실험 때 저장된 task와 달라지면 fail closed한다.

## 판정 gate

다음을 모두 만족해야 PASS다.

1. dev200 200개와 49개 ordered columns가 완전하다.
2. archive가 요청한 모든 fingerprint에 정확히 하나의 저장응답이 있다.
3. archive 실행 중 API, Gemma, BGE call은 0이다.
4. S001과 `v1-v24`, `e1-e24`의 cell difference가 모두 0이다.
5. archive가 보고한 initial/retry/fallback call topology를 기록한다.

불일치가 있으면 public regression을 Python 과적합으로 단정하지 않고 먼저 package/runtime
조립 차이를 수정한다. 일치하더라도 OpenRouter와 evaluator vLLM의 생성 동등성까지 증명하지는 않는다.
