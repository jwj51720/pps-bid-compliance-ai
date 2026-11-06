# N003 v1 restriction-axis fast20 preflight

작성일: 2026-09-22

결론: PASS. N002의 실적·지역 FP 원인을 직접 표현하는 두 축 관측을
fast20 20회에 한해 실행한다.

- declared changes: prompt task/schema와 해당 dev200 source-audit path.
- fixed: source view v2, v31 card, input/panel, model/temperature/seed/token.
- dev200 200/200 fit, max 13,501; fast20 20/20 fit, max 10,789.
- fast20 35문서 전부 scan, 102 exact spans, task hashes 20/20 match,
  logical calls 20, overflow 0, mock invalid 0.
- rendered short/attachment/largest PPS-DEV-062/131/165 전문을 읽었다.
  target이 기관/조직/자체 인력·시설 축이며 실적·지역·법정등록·제품·
  기술·평가·이행은 N이라는 계약, allowed의 동일 제한 관계, quote
  null/exact 계약, v31 1/0 조건, provenance가 모두 존재한다.
- frozen/reference/legacy import와 label/ID rule은 없다.

Python reducer는 `target=Y, allowed=N`만 1로 투영하고 target=N은
0, 나머지는 U로 유지한다. 유료 gate는 invalid 0, TP>=2, FP<=2,
U<=4다. fast 통과 전 holdout/dev200은 금지한다.
