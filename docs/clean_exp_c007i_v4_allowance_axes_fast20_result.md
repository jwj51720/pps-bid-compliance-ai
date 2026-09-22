# Clean EXP-C007I v4 allowance-axes fast20 result

작성일: 2026-09-21

결론: **fast20 gate 실패; holdout20/dev200 확대 중단**. 이 결과는 v4 관계
진단이며 C005D 품질 기준선 또는 제출 정책을 바꾸지 않는다.

| fast20 | v4 TP/FP/FN | v4 F1 | Macro positive-F1 | invalid |
| --- | ---: | ---: | ---: | ---: |
| C007D parent-scope | 3/0/0 | 1.000000 | 0.736111 | 0 |
| **C007I allowance axes** | **3/1/0** | **0.857143** | **0.730159** | **0** |

새 발주기관 허용축 `i`를 추가한 실행은 18개 candidate notice에 18번의
새 Gemma call을 사용했다. 20개 공고, 35/35 원문 문서, 57개 exact candidate,
overflow 0, 출력 invalid 0, positive v4 근거 누락 0, 다른 23개 v 변화 0이다.
3개 fallback 중 2개는 candidate가 없는 공고이며, 하나는 미해결 관측이다.
OpenRouter 측정 35.142초, prompt/completion 합계 63,819/4,532 tokens였다.
이 시간으로 evaluator vLLM 시간을 추정하지 않는다. 검증기에서 보고한 v15
positive-without-evidence 1건은 상속된 비-v4 baseline 셀이며 C007I label
mutation은 0이다.

유일한 새 v4 오탐은 `PPS-DEV-049`다. C007D는 후보 R001을 서류·증빙 양식
`r=F,m=N`으로 보았지만, C007I는 **같은 exact 후보와 제목 이력**을
`r=Q,m=Y,x=S,i=N,a=N,n=N`으로 분류해 positive quote를 만들었다.
원문은 제출서류 절 아래 실적증명서·제안서 서식 목록이다. 따라서 입력 누락,
후보 누락, 근거 문자열 복원, merge 오류가 아니라 **역할/의무성 의미 분류의
불안정성**이 직접 원인이다. 프롬프트가 `평가표·제출서류·실적증명서 양식을
참가자격으로 바꾸지 않는다`고 명시해도 이 사례에서는 지시가 충분하지 않았다.

사전 가설은 053의 발주기관 제한과 사업내용 동등 허용을 분리하는 것이었다.
하지만 053은 독립 holdout 공고이므로 fast20의 049 회귀를 무시하고 holdout을
보는 것은 계획의 gate를 위반한다. 이번 schema/prompt 변경을 canonical로
승격하지 않는다. 다음 단계는 v4 단일 항목을 더 다듬기 전에, 독립 native
baseline의 prompt/owner 재구축과 전체 dev200 재측정이라는 상위 목표로
우선순위를 되돌리는 것이다.

재현 명령:
`.venv/bin/python scripts/run_v4_requirement_experiment.py --config experiments/manifests/clean_exp_c007i_v4_allowance_axes_fast_v1.json --cohort fast20`

결과: `outputs/clean-exp-c007i-v4-allowance-axes-fast-v1/fast20/`의
`run_report.json`, `observations.json`, `metrics.json`, `responses/`,
`submission.csv`, `preflight.json`, `semantic_contract.json`, `rendered_inputs/`.
