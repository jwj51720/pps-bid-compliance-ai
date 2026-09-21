# EXP-C005R v19 positive-only quote resolution replay 계획

작성일: 2026-09-21  
상태: 0-call replay 구현 승인, provider call 금지

## 진단

C005 fast20은 17 candidate calls를 완료했지만 `invalid_responses=14`, status `INCOMPLETE`였다.
모든 실패 이유는 `quoted_text_not_exact`였다.

- candidate observations: 40
- byte-exact quotes: 18
- 공백만 제거하면 원문에 유일하게 매칭: 5
- 원문에 없는 요약/`N/A`/`UNKNOWN`: 17
- FN `PPS-DEV-036`: semantic field를 모두 올바르게 출력했고 quote만 줄바꿈/공백 차이

036 observation은 다음을 정확히 보존했다.

```text
requirement_role = BID_OR_PROPOSAL_QUALIFICATION
document_kind = EXTERNAL_SUPPLY_OR_TECH_ASSURANCE
external_issuer_explicit = YES
bidder_must_obtain_or_hold = YES
obtain_before_bid_deadline = YES
bidder_must_submit = YES
submit_after_bid_or_contract = YES
```

따라서 C005의 성능 결과는 아직 관측되지 않았다. 무관한 negative candidate가 `N/A`를 quote로
냈다는 이유로 그 공고의 모든 typed observation을 버린 것이 serialization/evidence gate 결함이다.

## 가설과 허용 변경

Base는 exact stored tasks/responses의 C005 fast20이다.

- base manifest: `clean_exp_c005_v19_requirement_instances_v1.json`
- base responses:
  `outputs/clean-exp-c005-v19-requirement-instances-v1/fast20/responses/`
- provider calls: 0
- prompt/schema/semantic fields/reducer predicate/source candidates: 변경 금지
- 허용 변경:
  - negative observation의 quote는 label 계산에 사용하지 않고 validity만 기록
  - positive predicate를 충족하는 candidate에만 evidence resolution을 필수화
  - byte-exact match 우선
  - 실패 시 공백 문자만 제거한 문자열이 candidate source에 **정확히 한 번** 나타날 때 원문의
    시작/끝 offset으로 역매핑하여 변경 없는 substring을 반환
  - 0회 또는 2회 이상이면 unresolved로 처리하고 해당 notice는 C004S baseline v19/e19 fallback

대소문자, 문장부호, 철자, Unicode 문자, 생략부호, 유사도 편집은 허용하지 않는다. 공백 외 문자가
하나라도 다르면 매칭하지 않는다. 이 resolver는 evidence/source 연결만 수행하며 semantic field나
label을 생성하지 않는다.

## identity와 gate

1. C005 task hashes 17/17 exact match
2. stored response files 17/17, provider calls 0
3. response content SHA를 보존
4. negative invalid quote는 observation diagnostic에 남기되 response 전체를 invalid로 만들지 않음
5. positive predicate 중 resolved evidence가 없는 notice는 baseline fallback
6. non-v19 changed cells 0, output 49 columns, evidence unchanged substring <=500
7. fast gate는 원 계획과 동일: TP>=1, FP<=1, semantic/transport invalid 0

통과하면 C005R 결과를 C005의 실질 fast 결과로 간주하고, 동일 quote policy를 고정한 별도
holdout manifest를 만든다. 실패하면 holdout을 실행하지 않는다.
