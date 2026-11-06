# N005D native v22 dev200 result

작성일: 2026-09-22

결론: **dev200 보존 gate 실패; independent native owner로 승격하지 않는다.**

| cohort | TP / FP / FN | v22 positive F1 | invalid |
| --- | ---: | ---: | ---: |
| fast20 | 1 / 0 / 0 | 1.000000 | 0 |
| independent holdout20 | 1 / 0 / 0 | 1.000000 | 0 |
| dev200 | 5 / 2 / 0 | **0.833333** | 0 |

dev200은 200 logical calls, prompt 1,104,337 tokens, completion 6,423
tokens, remote wall time 204.793초였다. 모든 5개 양성을 회수했고 positive
evidence는 exact source substring이다. 그러나 음성 2건을 양성화했다.

두 FP는 동일한 관계 오류다.

- `PPS-DEV-171`: `제안서 설명회(평가)에 참여하지 않은 제안자는
  평가에서 제외함`
- `PPS-DEV-193`: `제안설명회에 참가하지 않은 업체는 ... 평가대상에서
  제외`

둘 다 입찰·제안서 **제출 전 사업·현장설명회**가 아니라 제출된 제안서를
평가하는 발표·설명회다. prompt에는 이 제외가 있었지만 schema는 이를
`briefing` 한 축에 압축해 모델이 단계 관계를 잃었다. source omission,
metadata, parser, evidence 오류는 아니다.

frozen L41 v22 F1 1.0을 이 owner로 교체하면 단독 Macro 손실은
`(0.833333-1)/24 = -0.006944`다. 독립 baseline 허용 손실 -0.010147의
대부분을 한 항목이 사용하므로 승격하지 않는다.

다음 v22 후보를 만들 경우 `설명회 존재`를 다시 강조하는 prompt-only
수정이 아니라, organizer truth condition의 단계 관계를 별도 observation
(`PRE_SUBMISSION_BRIEFING` 대 `PROPOSAL_EVALUATION`)으로 표현하는 최소
schema가 필요하다. 이는 두 dev 오류 문자열을 Python rule로 처리해서는
안 된다. 새 후보는 다시 fixed fast20 → independent holdout20 → dev200
순서를 지킨다.

근거: `outputs/clean-exp-n005d-v22-briefing-dev200-v1/dev200/run_report.json`
