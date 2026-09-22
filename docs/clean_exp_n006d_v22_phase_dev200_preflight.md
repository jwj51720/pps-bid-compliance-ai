# N006D v22 phase-relation dev200 preflight

작성일: 2026-09-22

결론: PASS. N006 fast20과 N006H holdout20에서 모두 F1 1.0인 동일
정책을 dev200으로 확장한다.

- declared changes: holdout panel 제거 및 cohort=dev200
- prompt/view/schema/decision/provider changes: 0
- manifest undeclared differences: 0
- 200 records, 374/374 documents, 900 exact spans
- exact task hashes 200/200
- prompt min/max/sum: 1,773 / 13,349 / 1,134,937 tokens
- logical calls 200, overflow 0, mock invalid 0

short/attachment/largest와 양성 5건, N005D FP 2건의 exact rendered task를
검토했다. 모든 semantic-input contract가 존재하고 legacy/reference/frozen
fallback은 없다.

목표는 TP=5, FP=0, FN=0, invalid=0이다. `PPS-DEV-171/193`은
`proposal_evaluation_session=Y`이면서 `pre_submission_bar!=Y`여야 한다.
