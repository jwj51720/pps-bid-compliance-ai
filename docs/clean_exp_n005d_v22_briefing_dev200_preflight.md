# N005D native v22 dev200 preflight

작성일: 2026-09-22

결론: PASS. fast20과 independent holdout20에서 각각 v22 F1 1.0을
기록한 동일 정책을 dev200 200회로 확장한다.

- base: `clean_exp_n005h_v22_briefing_holdout_v1.json`
- declared changes: cohort를 dev200 전체 입력으로 변경하고 panel 제거
- prompt/view/schema/provider/decision changes: 0
- manifest undeclared differences: 0
- 200 records, 374/374 documents inspected, 900 exact spans
- exact audited task hash match: 200/200
- prompt tokens: min 1,618, max 13,194, sum 1,103,937
- logical calls: 200; overflow: 0
- mock: 200 binary outputs, invalid 0

dev200 short/attachment/largest와 양성 5건의 audit-rendered task를 검토했다.
카드 1/0 조건, 낙찰방식, 세 relation axes, 설명회와 제안발표·보고회의
구분, exact evidence 및 provenance가 실제 메시지에 존재한다. raw metadata
JSON, legacy/reference/frozen fallback은 없다.

dev200 목표는 TP=5, FP=0, FN=0, invalid=0, positive evidence validity
100%다. 결과는 v22 단독 native owner 점수로만 보고하며 24-item 독립
Macro로 확대 해석하지 않는다.
