# S006 — 제출 ZIP 저장응답 재실행 parity 감사 결과

상태: **PASS** (2026-09-23, zero-call)

## 결론

실제 제출된 `dist/pps_20260922_153225.zip`을 dev200에서 저장된 OpenRouter 응답과 ranking으로
재실행한 결과, S001 clean replay의 49열 결과와 **cell difference 0**으로 완전히 일치했다.
따라서 현재 확인 가능한 범위에서 데이터 결합, specialist 라우팅, conditional B fallback,
merge, evidence 정리 또는 ZIP 패키징 누락이 local `0.8151465658` 대 public
`0.6053527995` 괴리의 원인은 아니다.

이 결과는 같은 응답을 넣은 조립 parity를 증명한다. OpenRouter 저장응답과 evaluator의 offline
vLLM 신규 생성이 같다는 뜻은 아니며, dev200과 test의 분포·표현 차이에 대한 일반화도 증명하지 않는다.

## 재현 결과

- archive SHA-256: `72e3c1d65ec342b3d58e1cc5f99ee0c4a9ccfb1972d111df0fa488a5a0fce4df`
- records: 200
- base task hash: 600/600 MATCH
- v3 task hash: 61/61 MATCH
- v19 task hash: 165/165 MATCH
- registered exact message+schema fingerprints: 826
- stored-response requests consumed: 683
- missing fingerprints: 0
- verdict/evidence cell differences: 0
- dev200 Macro positive-F1: `0.8151465658238104`
- fast20: `0.7277777777777777`
- reused dev holdout20: `0.4305555555555556`
- LLM calls: 0
- embedding calls: 0

ignored artifacts:

- `outputs/clean-exp-s006-archive-stored-response-parity-v1/run_report.json`
- `outputs/clean-exp-s006-archive-stored-response-parity-v1/archive_runtime_report.json`
- `outputs/clean-exp-s006-archive-stored-response-parity-v1/submission.csv`

## 실제 call topology

archive가 기록한 논리 요청 수는 다음과 같다.

- initial: 661
- base invalid retries: 18
- specialist invalid retries: 2
- conditional B fallback: 2
- total: 683

초기 base task는 r10 200 + C24 200 + v19 후보가 없는 notice의 B 35 = 435였고,
specialist는 v3 61 + v19 165 = 226이었다. 이후 v19 positive evidence가 해결되지 않은 2건에
B가 호출됐다.

저장된 C24 응답 중 9건은 구조적으로 invalid여서 각각 두 번 재시도됐지만, replay에서는 같은
invalid 응답을 반복 공급했으므로 최종 unresolved였다. 실제 evaluator에서는 재생성이므로 이 9건의
결과가 달라질 수 있다. 이것은 package assembly 버그가 아니라 provider/runtime 생성 차이가 최종
cell을 바꿀 수 있는 구체적인 경로다.

## 해석과 다음 조치

1. local-public 괴리를 해결하기 위해 packaging을 다시 쓰는 것은 우선순위가 아니다.
2. S004가 확인한 dev200의 계약방식·가격대·specialist route 분포 편향과, frozen Python owner의
   dev 적응 위험을 20,000건 모집단에서 계속 감사한다.
3. C24 malformed 9건처럼 생성 backend에 민감한 항목은 dev의 한 번 저장응답 점수를 그대로
   참값으로 취급하지 않는다.
4. 다음 변경은 다항목 heuristic 보정이 아니라, owner별 population activation과 source-role
   안정성을 먼저 수치화한 뒤 가장 위험한 한 항목부터 controlled ablation한다.
