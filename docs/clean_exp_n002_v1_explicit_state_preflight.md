# N002 v1 explicit-state fast20 preflight

작성일: 2026-09-22

결론: PASS. N001 대비 source view, card, schema shape, fast20 IDs,
provider/generation을 고정하고 system output 의미만 v3로 바꿨다.
manifest diff의 선언 변경은 `prompt.task`와 그 task hash를 가리키는
`data.source_audit_path`뿐이다.

- dev200 no-call audit: 200/200 fit, 374문서 scan, 971 exact spans,
  max 13,413 tokens, gold/C005D nonempty e1 1/1·7/7.
- fast20: 20건, 35문서, 102 spans, logical calls 20, overflow 0,
  max 10,701 tokens, audited task hash 20/20 match.
- mock: 20/20 parse, invalid 0.
- frozen/reference/legacy input: 없음.

short/attachment/largest actual rendered message는 각각
`outputs/clean-exp-n002-v1-explicit-state-fast-v1/fast20/rendered_inputs/`
아래 PPS-DEV-062/131/165 파일에서 읽었다. v31 카드의 적용·1·0
조건, 모든 문서 scan에서 나온 exact source, 그리고 다음 계약이
명시돼 있다: Y=위반, N=비위반, U=충돌/실제 불충분, N/U quote=null.
largest의 user source는 N001과 동일 task view이고 system만 선언된
v3로 변경됐다. overflow task는 없다.

유료 승인은 fast20 20회에 한정한다. gate는 invalid 0, positive
quote exact 100%, TP>=2, FP<=2, U<=4다. 실패하면 holdout/dev200을
실행하지 않는다.
