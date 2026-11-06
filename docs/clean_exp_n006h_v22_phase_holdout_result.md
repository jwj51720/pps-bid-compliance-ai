# N006H v22 phase-relation holdout20 result

작성일: 2026-09-22

결론: PASS. independent holdout20에서 TP/FP/FN 1/0/0, v22 F1 1.0,
invalid 0이었다. fast20과 holdout20이 같은 방향이므로 동일 정책을
dev200으로 확장한다.

이 결과는 v22 단독이며, N005D에서 발견된 평가설명회 FP 두 건은 두 panel에
없으므로 해결 여부는 아직 dev200에서 확인해야 한다.

근거: `outputs/clean-exp-n006h-v22-phase-holdout-v1/holdout20/run_report.json`
