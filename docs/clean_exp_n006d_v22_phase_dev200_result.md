# N006D native v22 phase-relation dev200 result

작성일: 2026-09-22

결론: **PASS. v22 독립 native final owner로 승격한다.**

| cohort | TP / FP / FN | v22 positive F1 | invalid |
| --- | ---: | ---: | ---: |
| fast20 | 1 / 0 / 0 | 1.000000 | 0 |
| independent holdout20 | 1 / 0 / 0 | 1.000000 | 0 |
| dev200 | 5 / 0 / 0 | **1.000000** | 0 |

dev200은 200 logical calls, prompt 1,135,331 tokens, completion 10,071
tokens, remote wall time 204.707초였다. 200 final outputs 모두 binary이며
모든 양성 evidence가 exact source span에 연결된다.

N005D의 두 FP는 의도한 관계로 교정됐다.

| ID | pre-submission briefing | pre-submission bar | proposal evaluation |
| --- | --- | --- | --- |
| PPS-DEV-171 | N | N | Y |
| PPS-DEV-193 | N | N | Y |

즉 Python keyword correction 없이 Gemma가 접수 후 제안평가 세션과 제출 전
사업·현장설명회를 분리했다. 양성 5건은 모두 negotiated/pre-submission
briefing/pre-submission bar가 Y였고, source view·v31 card·낙찰방법·
evidence gate는 N005D와 동일하다.

이 결과는 frozen/reference를 읽지 않은 v22 단독 owner 완성 근거다. 아직
24-item 독립 pipeline이나 submission runtime에 통합된 것은 아니다.
현재 topology를 항목마다 곱하면 runtime이 증가하므로, 다른 owner를 만들
때는 품질 검증용 item call과 최종 공통-call 통합을 구분해야 한다.

근거: `outputs/clean-exp-n006d-v22-phase-dev200-v1/dev200/run_report.json`
