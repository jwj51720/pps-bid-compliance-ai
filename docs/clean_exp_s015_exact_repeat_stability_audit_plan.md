# S015 — 동일 task 독립 재호출 안정성 감사 계획

상태: zero-call stored-response reproducibility 진단

## 질문

S014의 coarse covariate shift는 local-public 괴리의 약 9.42%만 설명했다. 남은 후보 중 하나는
OpenRouter dev 생성과 evaluator offline INT8 vLLM 생성의 차이다. evaluator 응답은 없으므로 직접
비교할 수 없지만, 저장된 실험 중 같은 task를 fast20과 dev200에서 독립 호출한 v3/v19 overlap을
사용해 exact prompt에서 생성 내용과 최종 verdict가 얼마나 안정적인지 측정할 수 있다.

## 변경 통제

- base config: `experiments/manifests/clean_exp_s014_covariate_shift_stress_v1.json`
- allowed change: `exact_repeat_stability_audit` 추가만
- external calls: 0
- prediction/submission 변경: 없음
- output: `outputs/clean-exp-s015-exact-repeat-stability-audit-v1/`

## authoritative repeat pairs

1. v3 keyed specialist
   - fast20: C004R fast20 responses
   - dev200: C004R dev200 responses
   - overlap: 10 tasks
2. v19 requirement specialist
   - fast20: C005 fast20 responses
   - dev200: C005D dev200 responses
   - overlap: 17 tasks

각 pair는 preflight의 SHA-256 task hash가 같은 경우만 포함한다. response file이 있다는 사실만으로
동일 prompt라고 간주하지 않는다.

## 지표

- exact content equality
- finish reason / invalid / parser validity
- typed observation field disagreement
- reducer final V disagreement
- positive predicate disagreement
- prompt/completion usage와 latency 차이

quote 표면 차이는 별도로 세고 semantic field 차이와 섞지 않는다. v3는 동일 baseline cell과 v2
basis reducer, v19는 동일 relaxed quote parser와 relation reducer를 사용한다.

## 해석 gate

- repeat final disagreement가 0이라고 evaluator parity를 주장하지 않는다.
- small overlap의 비율을 전체 200건 신뢰구간처럼 사용하지 않는다.
- 동일 prompt repeat가 없는 r10/B/C24에는 결론을 외삽하지 않는다.
- specialist final 안정성이 높고 response content만 다르면 typed reducer의 robustness 증거로 본다.
- base arm의 안정성이 미검증이면 다음 최소 유료 진단은 exact base task repeat micro다.
