# S012 — v19 specialist 모집단 형태·효용 감사 계획

상태: zero-call 일반화·runtime 진단 계획

## 질문과 가설

S001의 v19 specialist는 dev에서 base B owner의 `TP/FP/FN=5/10/1`을 `6/4/0`으로 바꿔
Macro `+0.0114087`을 얻었다. submission에서는 165/200건의 B owner를 native typed observation으로
대체하고 no-candidate 35건만 B를 쓴다. organizer 모집단 route 76.10%를 test 1,853건에 대입하면
약 1,410건이 native task가 된다. 이는 base 위에 추가되는 호출이 아니라 B와 1:1 대체되는 호출이며,
runtime 차이는 주로 prompt/completion 길이와 structured generation 난이도다. public generalization
또는 token 효용이 낮다면 B로 되돌릴 가치가 있다.

반대로 v19 candidate 대부분이 청렴·보안·자기서약·서식이라면 native role 분해가 base B의 FP를
줄이는 구조적 이유가 모집단에서도 유지될 수 있다. S012는 동일 source view를 dev와 비라벨
20,000건에 실행하고, 저장된 dev observation과 base→specialist 셀 전이를 함께 감사한다.

## 변경 통제

- base config: `experiments/manifests/clean_exp_s011_python_owner_stage_attribution_v1.json`
- allowed change: `v19_population_morphology_audit` 추가만
- LLM/BGE calls: 0
- final prediction / pseudo-label: 없음
- output: `outputs/clean-exp-s012-v19-population-morphology-audit-v1/`
- active imports: `src.pps_ai`만 사용

## 사전 고정 morphology

아래 표면형은 source strata 설명에만 사용하고 v19 label이나 role을 계산하지 않는다.

- `external_issuer_surface`: 제조사·공급사·기술지원사·총판·대리점
- `supply_or_tech_surface`: 물품공급·공급확약·기술지원
- `bid_submission_surface`: 입찰서·입찰참가·제안서·제출서류·마감일
- `post_award_surface`: 낙찰·계약체결/계약후·착수·이행단계
- `self_promise_surface`: 청렴·보안·안전·서약·각서·근로·인권·개인정보·준수
- `form_surface`: 서식·양식·별지·붙임
- `status_or_authenticity_surface`: 정품·인증·제조자/대리점/공급 증명

co-occurrence로 `external+supply`, `external+supply+bid`, `self/form without external+supply`,
`post-award without bid`를 별도로 센다.

## gate

1. dev 200/200, population 20,000/20,000과 모든 문서를 검사한다.
2. 입력·view module·저장 observation·base/final CSV SHA-256을 기록한다.
3. notice/candidate 분모를 분리하고 risk ratio와 percentage-point 차이를 기록한다.
4. `abs(rate difference)>=0.10` 또는 RR가 `[0.67,1.50]` 밖이면 large shift로 표시한다.
5. 문서유형 분포와 candidate 수 분포의 total variation을 기록한다.
6. hash 고정 source sample ID만 남기고 원문은 결과 JSON에 복제하지 않는다.
7. dev 저장 observation의 role/kind/positive predicate와 base→final 셀 전이는 별도 표로 기록한다.
8. 모집단 morphology를 accuracy, precision, F1 또는 v19 pseudo-label로 부르지 않는다.
9. v19 제거 판단은 local Macro 손실, 예상 test native/B task 비율, token/runtime 차이와 morphology
   이동을 함께 사용한다. call count 절감이라고 잘못 표현하지 않는다.

S012는 submission 변경이 아니다. 결과가 native owner의 구조적 FP 제거를 지지하면 v19를 유지하고,
runtime은 serialization/owner replacement 방식으로 줄인다. 의미 이동이 크고 local 이득이 취약하면
v19-only revert를 별도 one-change public ablation으로 만든다.
