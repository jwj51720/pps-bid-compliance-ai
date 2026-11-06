# EXP-C004R v3 keyed holdout20 결과

실행일: 2026-09-21

## 결론

**PASS.** Independent holdout20의 유일한 v3 양성을 회수하고 FP와 invalid response를 만들지
않았다. dev200으로 승격한다.

- output: `outputs/clean-exp-c004r-v3-keyed-full-fast-v11/holdout20/`
- baseline v3: TP 0 / FP 0 / FN 1 / F1 `0.000000`
- candidate v3: TP 1 / FP 0 / FN 0 / F1 `1.000000`
- Macro: `0.3888888889 → 0.4305555556`
- specialist calls: 3
- invalid responses: 0
- semantic fallbacks: 2
- other 23 changed cells: 0
- v3 positive without evidence: 0
- prompt tokens: sum 4,744 / max 1,884
- completion tokens: sum 305 / max 129
- wall time: 6.665초(OpenRouter이며 evaluator vLLM 근거가 아님)

양성 `PPS-DEV-053`에서 Gemma는 공고문의 실제 입찰참가자격 단일건 `1억 원`을 exact
surface로 반환했다. Python은 이를 100,000,000원으로 검증해 입찰추정가격 22,690,000원보다
큰지만 계산했다.

## Dev200 실행 전 검증

- same manifest/policy/provider
- supplied documents inspected: 374/374, uninspected 0
- candidate notices/candidates: 61/100
- specialist calls: 61; baseline 저장 cell을 포함한 logical topology 표기는 600+61=661
- exact tokenizer: min 1,074 / p95 3,072 / max 3,720 / sum 102,725
- dev200 mock: 200 rows, baseline score 재현, output/evidence validation PASS
- rendered short/attachment/largest와 오류 panel 9건 재검토 완료:
  `outputs/clean-exp-c004r-v3-keyed-full-fast-v11/dev200/rendered_inputs/`
- active tests: 40 passed

Dev200 gate는 계획서의 최소 TP>=6, FP<=1, FN<=2이며 목표는 8/0/0이다. 다른 23개 final
cell은 exact equality여야 하고 invalid response는 0이어야 한다.

## Dev200 1차 실행

- v3: TP 7 / FP 1 / FN 1 / F1 `0.875000`
- Macro: `0.8009804827`
- 다른 23개 changed cells: 0
- invalid responses: 2 (`PPS-DEV-08`, `PPS-DEV-157`)

품질 최소 gate는 통과했지만 invalid=0 조건은 실패했으므로 상태는 INCOMPLETE다. 두 건은
8,192 completion-token whitespace loop이며, `docs/clean_exp_c004rr_v3_keyed_recovery_plan.md`의
exact-task recovery를 통과하기 전에는 완료 결과로 승격하지 않는다.
