# N006H v22 phase-relation holdout20 preflight

작성일: 2026-09-22

결론: PASS. N006 fast20 F1 1.0 정책을 변경 없이 independent holdout20에
20회 실행한다.

- declared changes: panel/cohort만 fast20에서 holdout20으로 변경
- prompt/view/schema/decision/provider changes: 0
- manifest undeclared differences: 0
- 20 records, 41 documents, 90 exact spans, task hashes 20/20
- prompt max 13,349, sum 115,611 tokens, overflow 0
- mock invalid 0

holdout short/attachment/largest와 양성 `PPS-DEV-135`의 v2 rendered task를
읽었다. 제출 전 사업설명회, 미참석 입찰금지, 평가설명회 분리, exact
quote와 metadata/provenance가 실제 메시지에 있다.

gate는 TP=1, FP=0, FN=0, invalid=0이다. 통과할 때만 dev200을 실행한다.
