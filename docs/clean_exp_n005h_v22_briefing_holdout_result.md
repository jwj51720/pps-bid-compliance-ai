# N005H native v22 holdout20 result

작성일: 2026-09-22

결론: PASS. 독립 holdout20에서도 native v22 binary owner가 완전일치했다.

| 결과 | 값 |
| --- | ---: |
| TP / FP / FN | 1 / 0 / 0 |
| v22 positive F1 | 1.0 |
| invalid / final U | 0 / 0 |
| logical calls | 20 |
| prompt / completion tokens | 112,551 / 610 |
| remote wall time | 22.607초 |

양성 `PPS-DEV-135`는 세 축 모두 Y였고, evidence는 source `S004`의
변경 없는 원문 substring이다. fast20의 1/0/0과 independent holdout20의
1/0/0이 일치했으므로, 동일 정책을 dev200으로 승격한다. 이 결과는 v22
단독 점수이며 다른 23개 frozen cell과 합친 Macro를 주장하지 않는다.

근거: `outputs/clean-exp-n005h-v22-briefing-holdout-v1/holdout20/run_report.json`
