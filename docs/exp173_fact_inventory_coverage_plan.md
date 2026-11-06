# EXP173 source-first fact-inventory coverage ablation

작성일: 2026-09-09 (dev / mac)

## 출발점

EXP171 source-first/full-final은 complete-source one-stage control EXP172보다 dev200 macro
positive-F1이 `0.307962` 대 `0.259281`로 높았다. 두 정책의 차이는 1차 source-only factual
navigation뿐이다. final은 둘 다 card v6, 21 organizer metadata field, friendly exact product
fact, 모든 실제 공고 원문, V/E schema, same decoder/postprocess를 사용한다.

현재 navigation은 7개 truth-domain category마다 각 source pack에서 최대 **3개**의 unchanged
원문 후보만 반환한다. EXP171의 gold evidence(부재항목 제외) 54개에 대한 사후 진단에서는
candidate 안에 gold evidence 전체가 그대로 있는 경우가 7건, 연속 부분이 겹치는 경우가
41건이었다. 이것은 label을 보고 category를 보정하는 근거가 아니라, candidate cap이
원문 사실을 요약적으로만 남긴다는 관측이다.

## 가설과 단일 변경

EXP173은 `fact_inventory_full_final_v2`에서 **category당 source pack별 최대 후보 수만
3→4로 바꾼다.** 1차는 여전히 0/1, 법령 해석, metadata 값, 예외 결론을 출력하지 않고
원문 연속 문자열만 수집한다. final은 이전과 동일하게 complete source를 다시 읽고,
navigation null/누락을 Python 0으로 조립하지 않는다.

예상 가능한 결과는 양방향이다.

- 더 넓은 navigation이 첨부의 자격·제품·일정·금액 사실을 가시화해 FN을 줄일 수 있다.
- 반대로 final context가 길어지거나 부차적 조건이 늘어 FP가 증가할 수 있다.

따라서 headline macro만 보지 않고 candidate 개수, final pack 수, parser/evidence warning,
per-item TP/FP/FN을 EXP171과 함께 기록한다. card text, raw law/RAG, metadata renderer,
product lookup, final output schema, merge, frozen rule, model/decoder, source-selection은
변경하지 않는다.

## 실행 순서와 gate

1. mode/versioned schema를 구현하고 unit test로 v1=3, v2=4 cap 및 non-final contract를
   검증한다.
2. fast20에서 exact tokenizer admission, semantic-input contract, short/attachment/overflow
   rendered messages, mock parser/CSV, regression suite를 통과한다. final source omission은
   반드시 0이다.
3. valid 20/20 fast probe에서 EXP171 fast counterpart보다 quality/evidence 방향이
   개선되면 independent holdout20을 같은 policy로 실행한다. fast-only 상승은 dev200이나
   submission 승격 근거가 아니다.
4. holdout도 support할 때만 dev200을 실행하고, 그때 EXP171/172와 three-way로 비교한다.

이 실험은 “더 많은 법령/문서”를 넣는 것이 아니라 이미 final에 존재하는 source의
**non-final attention navigation density**만 바꾸는 single-variable ablation이다.

## 유료 전 검토 (2026-09-09)

Preflight는 EXP167 대비 선언된 `staged_run.mode` v1→v2 한 차이만 확인했다. exact
Gemma tokenizer admission은 dev200 전체에서 source 374/374, metadata 21/21, active
cards 24/24, over-budget 0을 확인했고 final pack 분포는 1회 186·2회 12·3회 2건이다.
semantic-input contract은 24/24 PASS다.

사람 검토는 `outputs/exp-173-source-first-full-final-v2-fast-panel-c4-mock/
staged_input_examples.md`의 PPS-DEV-062(단문), PPS-DEV-169(첨부+overflow), PPS-DEV-01
(다중 사실)에서 수행했다. Stage 1에는 raw source와 “최대 4개” source-only contract만,
final에는 cards·friendly metadata/CSV·complete original source·명시적 non-final
navigation이 있다. navigation 빈 값은 final 0이 아니다. mock은 20/20, parser/CSV
완료였고 regression suite는 144 passed다.

이 검토 중 v2 inventory capacity를 staged artifact에 기록하는 field가 mock 단계에서
빠진 것을 발견했다. provider 호출 전 바로 수정하고 mock·rendered review·tests를 새로
통과했다. 이 변경은 결과 label/merge가 아니라 experiment provenance만 보강한다.

## EXP173 무효화와 EXP174 재시도

EXP173 remote fast20은 20/20 transport/JSON completion을 했지만 **유효한 coverage
ablation이 아니다.** schema와 stage-1 prompt는 4 candidates를 허용했는데
`parse_fact_inventory_response()`가 v1의 `len(values) > 3` 검사를 유지했다. 20건 중
14건의 stage-1 source pack이 정상 4개 후보를 반환한 뒤 parser error로 그 pack 전체를
빈 navigation으로 바꿨다. 실제 navigation은 중앙 0개(기존 v1 중앙 12개)였다.

따라서 관찰된 macro `0.331944`는 결과표·비교·승격 근거에서 제외한다. EXP173 config는
`lifecycle: invalidated`로 고정해 재실행을 금지한다. parser가 max 3/4을 schema와 동일하게
받도록 수정했고, 4-item response를 parse하고 v1 parser가 거부하는 regression test를
추가했다. 새 config ID인 EXP174에서 사전 gate를 전부 다시 실행한다. 이 사건은
“schema만 바꾸고 parser/observability를 같이 바꾸지 않은” 실험 결함이며, 이후 capacity
변경의 mock은 empty arrays뿐 아니라 **새 upper bound를 실제로 채운 response**를 반드시
검증해야 한다.

## EXP174 valid fast-20 결과

EXP174는 repaired v2 parser로 20/20 complete, stage-1 parse error 0, final recovery 0,
CSV validation PASS였다. navigation은 notice당 중앙 **15개**(v1 12개), 최대 **32개**
(v1 21개)로 실제로 증가했다. 따라서 v2 coverage change는 이번에는 구현·선택되었다.

그러나 macro positive-F1은 **0.269444**로 EXP167 v1의 0.286111보다 -0.016667이었다.
호출 수는 모두 47회, runtime은 159.5초(v1 165.0초), total tokens는 662,688(v1 659,207)로
거의 같았다. v2는 v12 FP 하나와 v9/v17 FP를 줄였지만, v8 FP 하나·v23 TP 하나 손실과
v24 FP 하나가 더 커졌다. evidence validity는 .778(v1 .700), warning은 4건(v1 6건)으로
낫지만 headline decision quality를 상쇄하지 못했다.

결론: category candidate cap 3→4는 **validly reject**한다. independent holdout/dev200으로
확대하지 않는다. 이는 “원문 사실을 더 많이 넣으면 항상 낫다”는 가설을 지지하지 않으며,
source-first의 향상은 simple density 증가보다 fact-navigation의 형태/attention ordering에
의존할 가능성을 남긴다.
