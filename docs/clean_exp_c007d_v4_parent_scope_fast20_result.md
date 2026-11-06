# Clean EXP-C007D v4 parent-scope fast20 result

작성일: 2026-09-21

상태: **fast20 gate PASS; 독립 holdout 필요**. 이는 relation-only diagnostic이며
organizer v4 항목명의 금액 scope를 해결하지 않았다.

## 결과

| fast20 | v4 TP/FP/FN | v4 F1 | Macro positive-F1 | invalid |
| --- | ---: | ---: | ---: | ---: |
| C005D stored base | 2/0/1 | 0.800000 | 0.727778 | — |
| C007CR quote-recovered | 3/1/0 | 0.857143 | 0.730159 | 0 |
| **C007D parent-scope** | **3/0/0** | **1.000000** | **0.736111** | **0** |

다른 항목 수정은 없다. C007CR과 최종 v4가 달라진 유일한 공고는
`PPS-DEV-049`: 1→0이며 gold 0이다. 후보 원문은 그대로이고, 제목 이력과
role 지시가 추가되자 `NEGATIVE_PROOF`로 분류됐다. 기존 FN 042는
`POSITIVE_PROOF`로 유지됐고 기존 TP도 보존됐다. 따라서 fast20 macro 증가는
C005D 대비 `(1.0-0.8)/24 = 0.0083333333`으로 계산 결과와 일치한다.

## 형식·근거·호출

- 18 candidate notices / 18 live specialist calls / overflow 0.
- invalid 0; fallback 2는 candidate가 없는 notice다.
- non-v4 changed cells 0; v4 positive-without-evidence 0;
  evidence-validator label mutations 0.
- OpenRouter runtime 24.131초; prompt tokens 64,395,
  completion tokens 3,777. 이는 평가 서버 vLLM 시간의 추정 근거가 아니다.
- validator의 상속 v15 positive-without-evidence 1건은 C005D base에도 있는
  비-v4 셀이다.

Reproduction:
`.venv/bin/python scripts/run_v4_requirement_experiment.py --config experiments/manifests/clean_exp_c007d_v4_parent_scope_fast_v1.json --cohort fast20`

Artifacts: `outputs/clean-exp-c007d-v4-parent-scope-fast-v1/fast20/`의
`responses/`, `observations.json`, `metrics.json`, `run_report.json`,
`submission.csv`, `preflight.json`, `semantic_contract.json`, `rendered_inputs/`.

다음 gate는 `configs/dev_prompt_holdout_v1.json`의 독립 holdout20이다.
v4 target은 TP 1 / FP 0 / FN 0, invalid 0. 이를 통과해도 dev200과
금액-scope 충돌 검토 없이는 canonical로 승격하지 않는다.
