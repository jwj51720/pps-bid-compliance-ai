# N005H native v22 holdout20 preflight

작성일: 2026-09-22

결론: PASS. N005R에서 통과한 prompt/source/schema/binary reducer를
independent holdout20에 20회 실행한다.

- base: `clean_exp_n005r_v22_binary_projection_replay_v1.json`
- declared changes: 저장 fast response 제거, panel/cohort 변경,
  offline replay를 실제 panel observation으로 변경
- prompt/view/schema/provider/decision changes: 0
- manifest undeclared differences: 0
- holdout: 20 records, 41 documents inspected, 90 exact spans,
  logical calls 20, max 13,194 tokens, overflow 0
- mock: 20 binary rows, invalid 0

holdout short/attachment/largest rendered messages와 양성 `PPS-DEV-135`
메시지를 읽었다. v31 card, 낙찰방식, 세 축, presentation/report 제외,
exact quote와 provenance가 모두 있다. 양성의 제안요청서에는
`사업설명회에 참석하지 아니한 업체의 입찰 참가는 허용되지 않습니다`
원문이 exact span으로 포함된다. raw metadata JSON은 없다.

유료 gate는 TP=1, FP=0, FN=0, invalid=0, positive evidence validity
100%다. 통과할 때만 dev200 manifest를 만든다.
