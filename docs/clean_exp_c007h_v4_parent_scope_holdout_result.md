# Clean EXP-C007H v4 parent-scope holdout20 result

작성일: 2026-09-21

결론: **holdout target 실패; dev200 확대 중단**. C007D는 fast20에서
v4 `3/0/0`을 달성했지만 독립 holdout20의 유일한 v4 양성 053을
회수하지 못했다. C005D stored baseline과 같은 FN이며 오탐은 없다.

| holdout20 | v4 TP/FP/FN | v4 F1 | Macro positive-F1 |
| --- | ---: | ---: | ---: |
| C005D stored baseline | 0/0/1 | 0 | 0.430556 |
| C007H parent-scope | 0/0/1 | 0 | 0.430556 |

## 호출과 품질 gate

- 20 records, 7 candidate notices, 30 candidates, 7 live specialist calls.
- invalid 0, fallback 13(후보 없음), overflow 0.
- 다른 23개 label/evidence 변경 0, v4 positive-without-evidence 0,
  evidence-validator label mutations 0.
- OpenRouter 15.077초, prompt 29,299 / completion 1,886 tokens.
  evaluator vLLM 시간으로 환산하지 않는다.
- C005D 상속 v24 positive-without-evidence 2건은 이번 v4 변경이 아니다.

## 실패 위치: source omission이 아닌 관계축 혼합

053의 공고문 후보에는 실제 참가자격 제목, 의무 참가 문구, 한 공공기관군이
발주한 실적만 인정하는 조건이 모두 들어 있다. 모델의 저장 응답은
`r=Q, m=Y, x=I, a=E, n=N`이다. 즉 역할·의무·발주기관 제한은
정확히 구조화했지만, 같은 문장에 **유사·동등한 사업내용도 허용**한다는
표현 때문에 범용 `a=E`를 냈다. 기존 reducer는 `a=E`라면 기관군 제한도
해소된 것으로 취급해 `NEGATIVE_PROOF`로 계산했다.

이는 허용의 대상축이 서로 다른 문제다. 사업내용의 동등성을 허용해도
발주기관군의 제한이 해제되지는 않는다. 현재 `a` 한 필드는
`발주기관 허용`과 `사업내용 허용`을 구별하지 못한다. 이 진리조건은
현재 schema에 온전히 표현되지 않는다. 본문에 필요한 원문이 없어서가
아니며, 제목 이력의 추가만으로 해결할 수 있는 문제도 아니다.

저장된 fast20+holdout20 응답을 확인했을 때 `a=E` 관측 10개 중
`r=Q,m=Y,x=I,a=E`는 053 한 건이었다. 이 작은 표본만으로
`x=I이면 a=E를 무시`하는 Python label override를 정당화하지 않는다.
다음 단계는 v4 한 항목에서만 허용축을 분리한 source-grounded 관측 schema를
설계·검증하는 것이다. 금액 scope 충돌은 여전히 별개다.

Reproduction:
`.venv/bin/python scripts/run_v4_requirement_experiment.py --config experiments/manifests/clean_exp_c007h_v4_parent_scope_holdout_v1.json --cohort holdout20`

Artifacts: `outputs/clean-exp-c007h-v4-parent-scope-holdout-v1/holdout20/`의
`responses/`, `observations.json`, `metrics.json`, `run_report.json`,
`submission.csv`, `preflight.json`, `semantic_contract.json`, `rendered_inputs/`.
