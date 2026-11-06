# N006 v22 phase-relation fast20 result

작성일: 2026-09-22

결론: PASS. fixed fast20에서 TP/FP/FN 1/0/0, v22 positive F1 1.0,
invalid 0이었다. 20 logical calls, prompt 124,691 tokens, completion 978
tokens, remote wall time 24.123초였다.

양성 `PPS-DEV-26`은 `negotiated=Y`, `pre_submission_briefing=Y`,
`pre_submission_bar=Y`로 관측됐고 exact evidence는 공고문과
제안요청서 source span에 모두 연결됐다. 이 결과만으로 N005D의 dev200
FP가 해결됐다고 주장하지 않는다. prompt/schema/decision을 고정하고
independent holdout20으로 확장한다.

근거: `outputs/clean-exp-n006-v22-phase-fast-v1/fast20/run_report.json`
