# EXP-C005HS v19 compact serialization target probe 계획

작성일: 2026-09-21  
상태: one-target serialization-only probe 승인

## 근거

C005H의 v19 label 방향은 fast와 holdout에서 일치했지만 `PPS-DEV-192__p01`이 동일 verbose
schema로 두 번 연속 같은 whitespace loop를 냈다. 동일 task의 추가 반복은 중단한다. Partial JSON은
세 semantic field와 closing braces가 없어 Python default로 복구할 수 없다.

## 가설

의미 field, source candidate, prompt의 법률/역할 지시, reducer predicate는 그대로 유지하고 response
JSON의 key와 enum 표현만 짧은 code로 바꾸면 Gemma의 pathological serialization trajectory를
피할 수 있다.

Verbose-to-compact mapping은 versioned constant로 고정한다.

```text
requirement_role -> r (integer enum)
document_kind -> k (integer enum)
external_issuer_explicit -> x (0=NO, 1=YES, 2=UNKNOWN)
bidder_must_obtain_or_hold -> h (same tri-state)
bidder_must_submit -> s
obtain_before_bid_deadline -> b
submit_with_bid_or_proposal -> w
submit_after_bid_or_contract -> a
quoted_text -> q
```

Python adapter는 code를 기존 verbose observation으로 1:1 역변환하고 기존
`reduce_v19_with_quote_resolution`만 호출한다. 새 label rule, default, phrase override는 없다.

## 통제와 실행

- base: C005H manifest/task
- target: `PPS-DEV-192__p01` 한 건
- calls: 최대 1
- normal 17 responses: 재호출 0
- candidate text/order/hash: 동일
- system의 semantic instructions와 user source/card: byte-identical
- 변경 허용: output serialization instruction, response schema, compact adapter/parser
- provider parameters: 동일
- output은 diagnostic probe이며 complete strategy result로 부르지 않는다.

## gate

1. target user message SHA와 semantic system prefix SHA가 C005H와 일치
2. compact schema는 기존 9 field 모두를 required로 유지
3. unit test로 모든 enum round-trip과 missing/extra key rejection
4. probe response stop + schema valid + adapter valid
5. adapted target와 stored normal 17 responses를 동일 reducer로 assembly
6. final invalid 0, non-v19 change 0, v19 holdout FP 0 또는 최대 1

Probe가 실패하면 C005 family는 transport completeness 미해결로 종료하고 dev200을 실행하지 않는다.
성공하면 이 serialization policy로 dev200 전체를 실행하기 전에 fast stored responses를 offline
adapt할 수 있는지와 dev200 call topology/runtime을 별도로 preflight한다.
