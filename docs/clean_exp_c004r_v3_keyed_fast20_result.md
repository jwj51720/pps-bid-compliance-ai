# EXP-C004R v3 keyed full-fast 결과

실행일: 2026-09-21

## 결론

**PASS.** Candidate-keyed serialization으로 fast20 후보 10건을 모두 새로 호출했고, EXP-C004의
점수 개선을 유지하면서 invalid response를 0으로 만들었다. Independent holdout20으로 승격한다.

- output: `outputs/clean-exp-c004r-v3-keyed-full-fast-v11/fast20/`
- v3 baseline: TP 1 / FP 0 / FN 2 / F1 `0.500000`
- candidate: TP 3 / FP 0 / FN 0 / F1 `1.000000`
- Macro: `0.6791666667 → 0.7000000000`
- specialist calls: 10
- invalid responses: 0
- semantic fallbacks: 5(평가·서식 등으로 baseline 유지, 정상 정책)
- other 23 changed cells: 0
- v3 positive without evidence: 0
- prompt tokens: sum 14,981 / max 2,891
- completion tokens: sum 863 / max 168
- wall time: 14.792초(OpenRouter이며 evaluator vLLM 근거가 아님)

## Holdout 실행 전 검증

- cohort: `configs/dev_prompt_holdout_v1.json`의 고정 20건
- supplied documents inspected: 41/41, uninspected 0
- candidate notices/candidates: 3/5
- specialist calls: 3
- exact tokenizer: min 1,119 / p95=max 1,883 / sum 4,740
- mock: 20 rows, baseline score 재현, output/evidence validation PASS
- rendered:
  - positive/short `PPS-DEV-053`: 실제 참가자격 `단일건 1억 원`, 추정가격 22,690,000원
  - attachment `PPS-DEV-27`: 사업비와 과업실적 서식 후보, 모든 제공 문서 inspected
  - largest `PPS-DEV-121`: 사업금액·사후실적 문구와 추정가격, 모든 제공 문서 inspected

Rendered path:
`outputs/clean-exp-c004r-v3-keyed-full-fast-v11/holdout20/rendered_inputs/`

동일 manifest·동일 source view/prompt/schema/reducer/provider를 사용한다. Holdout gate는 사전 선언한
대로 v3 TP 1 / FP 0 / invalid response 0이다.

