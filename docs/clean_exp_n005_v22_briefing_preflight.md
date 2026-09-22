# N005 native v22 fast20 preflight

작성일: 2026-09-22

결론: PASS. 고정 fast20의 v22 20회만 실행한다.

- base: `clean_native_v22_source_audit_v1.json`
- declared change: `run.mode=source_audit_only → panel_observation`
- manifest diff: undeclared change 0
- dev200: 200 records, 374/374 documents inspected, 900 exact spans,
  gold e22 coverage 5/5, 200/200 one-call fit, max 13,194 tokens
- fast20: 20 records, 35 documents inspected, 90 exact spans,
  20/20 one-call fit, max 10,594 tokens, overflow 0
- mock: invalid 0
- legacy/reference/frozen dependency: 0

실제 short/attachment/largest와 fast 양성 `PPS-DEV-26`, holdout 양성
`PPS-DEV-135`의 rendered task를 읽었다. 모두 v31 v22 1/0 조건,
사람 친화적 낙찰방식, 세 축 `negotiated/briefing/exclusion`, U 조건,
exact quote와 source provenance를 포함한다. `PPS-DEV-26`의 공고문과
제안요청서에는 사업설명회 참석자가 참가자격이라는 원문이 모두 있고,
`PPS-DEV-135`에는 미참석자의 입찰 참가가 허용되지 않는 원문이 있다.

fast gate는 TP=1, FP=0, FN=0, U=0, invalid=0이다. 실패하면 같은
fast panel에 prompt를 반복 적합하지 않고 holdout/dev200을 실행하지 않는다.
