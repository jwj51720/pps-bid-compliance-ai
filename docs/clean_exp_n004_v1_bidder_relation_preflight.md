# N004 v1 bidder-relation fast20 preflight

작성일: 2026-09-22

결론: PASS. N003의 relation 오류만 고친 v5 task를 고정 fast20 20회에
한해 실행한다.

- base: `clean_exp_n003_v1_axis_fast_v1.json`
- declared changes: `prompt.task`, 그 task의 dev200 source-audit path
- fixed: source view v2, v31 card, axis schema, Python reducer, evidence gate,
  input/panel, model, temperature, seed, token budget
- dev200: 200/200 fit, 374 documents inspected, 971 exact source spans,
  max 13,564 tokens, overflow 0
- fast20: 20/20 fit, 35 documents inspected, 102 exact source spans,
  max 10,852 tokens, logical calls 20, overflow 0
- manifest preflight PASS, mock invalid 0

실제 rendered short/attachment/largest 메시지를 모두 읽었다. 세 메시지에
v31의 1/0 조건, 현재 입찰자 자신과 과거 실적 상대방의 구분, 기업규모
제외, allowed 축, U 조건, exact quote 계약과 source provenance가 존재한다.
첨부 공고는 공고문과 첨부 후보가 함께 렌더링된다. raw metadata dump,
frozen/reference/legacy 입력은 없다.

유료 fast gate는 계획대로 invalid 0, TP=3, FP=0, FN=0, U=0이다. 이
목표를 못 맞추면 holdout/dev200으로 확장하지 않는다.
