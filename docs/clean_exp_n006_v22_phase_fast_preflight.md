# N006 v22 phase-relation fast20 preflight

작성일: 2026-09-22

결론: PASS. N005D의 절차 단계 표현 결함만 바꾼 v2 task를 fixed fast20
20회에 실행한다.

- base: `clean_exp_n005r_v22_binary_projection_replay_v1.json`
- declared changes: v2 task/schema와 audit path, phase binary owner,
  저장 response replay에서 실제 fast 실행으로 전환
- fixed: source view, v31 card, metadata, evidence gate, provider/model/
  temperature/seed, tokenizer budget
- manifest undeclared differences: 0
- dev200 audit: 200 records, 374/374 documents, 900 exact spans,
  gold e22 5/5, max 13,349 tokens, overflow 0
- fast20: 20 records, 35 documents, 90 spans, max 10,749 tokens,
  logical calls 20, overflow 0
- mock invalid 0

short/attachment/largest와 양성 `PPS-DEV-26`, `PPS-DEV-135`, N005D FP
`PPS-DEV-171`, `PPS-DEV-193`의 실제 rendered messages를 읽었다.
양성에는 참가자격/제출 전 사업설명회 제한이, 두 FP에는 접수 후
제안발표·평가 세션과 평가대상 제외 문구가 exact span으로 포함된다.
v2 system은 두 행사를 동시에 따로 관측하며 evaluation session이
`pre_submission_bar`를 만들지 않는다고 명시한다.

fast gate는 TP=1, FP=0, FN=0, invalid=0이다. 통과할 때만 동일 정책을
independent holdout20으로 확장한다.
