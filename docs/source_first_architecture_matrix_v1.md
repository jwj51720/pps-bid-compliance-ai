# Source-first 이후 아키텍처 탐색 매트릭스 v1

작성일: 2026-09-10 (dev / mac)

## 목적

이 문서는 credit 복구 뒤의 다음 유료 실험을 결정하기 위한 **사전 설계 문서**다. 작은
문구 수정·카드 수정·dev 오답별 규칙 추가를 반복하지 않는다. 각 후보는 현재 공고의
원문 사실을 빠뜨리지 않으면서 Gemma가 24개 법률 판단을 수행하기 쉽게 만드는가만
검증한다.

공통 고정 조건은 다음과 같다.

- 원문 법령 RAG, 20,000건 사례 RAG, dev label 기반 Python 보정은 넣지 않는다.
- decision card v6, human-readable metadata, exact organizer product fact, EXP123의
  동결 v2/v3/v21 후처리는 변경하지 않는다.
- final V/E 판단과 evidence 확정은 Gemma가 실제 공고 원문을 읽고 한다. navigation의
  null/후보없음은 Python 또는 final label의 0이 아니다.
- final 단계는 exact-token 32k admission으로 **모든 supplied notice source**를 받는다.
  4,000자 final anchor는 이 branch에서 사용하지 않는다.

## 이미 얻은 구조적 증거

| 후보 | final 원문 범위 | stage-1 역할 | 결과 | 판정 |
| --- | --- | --- | --- | --- |
| EXP152/154 one-stage | complete source | 없음 | 32k fast20 0.241667 | 기준선 |
| EXP155/156 item group final | complete source를 group마다 반복 | 그룹별 최종 V/E | 0.237500 / 0.213889 | 종료 |
| EXP150 triage | 4k | route가 final item을 좁힘 | 0.277020 vs control 0.291071 | 종료: positive coverage 부족 |
| EXP151 strict locator | 4k | 항목별 exact snippet | 0.248016 | 종료: 32/380 중 14개만 non-empty |
| EXP153 inventory → final | complete source → 4k | 24개 항목별 한 구절/null | 0.280556 vs 4k control 0.291071 | 종료: final source 축소 + coverage 6/38 |
| EXP167/168/171 source-first v1 | complete source | 7개 사실 범주 × 최대 3구절 | fast +.023611, holdout +.018056, dev200 0.307962 | complete-source incumbent |
| EXP172 matched one-stage | complete source | 없음 | dev200 0.259281 | source-first v1보다 -0.048681 |
| EXP174 source-first v2 | complete source | 범주당 4구절 | fast 0.269444 | 종료 |
| EXP175 source-first v3 | complete source | 같은 navigation을 source 앞에 배치 | fast 0.263889 | 종료 |
| EXP176/177 source-first v4 | complete source | 예외 범주 1개 추가 | fast 0.287500, holdout 0.166667 | 종료: holdout 반대 방향 |
| EXP180 timeline supplement | complete source | v23 날짜 역할 추가 | fast 0.241667 | 종료: v23 TP 손실 + call 증가 |
| EXP182/183 procedure ledger | complete source | 7개 관계형 field로 교체 | fast 0.319444, holdout 0.125000 | 종료: holdout 반대 방향 |
| EXP186 V-only draft → V/E | complete source | V-only 초안 1회 | fast 0.206944 | 종료 |
| EXP187 V-only ×2 → V-only resolver | complete source | 2개 V-only 초안 + 모델 resolver | fast 0.097917 | 종료: recall/call topology 모두 악화 |

핵심 결론은 두 가지다.

1. 전문을 final에서 빼면 안 된다. EXP153의 항목별 inventory가 나쁜 결과를 낸 원인을
   항목별 탐색 자체로 단정할 수 없다.
2. source-first v1의 이득은 navigation 자체에서 왔을 가능성이 높지만, 더 많이 뽑기,
   앞에 놓기, 범주를 하나 더 늘리기로는 재현되지 않았다.

## 다음 후보: EXP188 item-aware navigation + complete-source final

### 가설

현재 v1 범주는 원문을 넓게 보여 주지만, 한 범주 안의 서로 다른 v의 사실을 같은 세
구절 슬롯이 경쟁한다. 이는 단순 추측이 아니다. label-blind EXP171 stage artifact audit에서
`제출서류_확약서` 90.3%, `일정_설명회` 74.5%, `금액_메타대조` 88.4%,
`참가자격_실적_지역` 56.5%가 source-pack별 3개 상한에 닿았다. 특히 v3/v19/v22/v23/v24가
필요로 하는 category는 metadata-only eligible notice의 87.1~92.7%에서 상한 압력을 보였다
(`outputs/exp181-source-first-relation-capacity-audit/relation_capacity.json`).

EXP188은 이를 **각 v에 최대 하나의 source-only relation candidate**로 바꾼다. 각 key는
v 이름이지만 0/1·위반·법률·예외결론은 반환하지 않고, 해당 카드가 요구하는 관계의 endpoint를
가장 잘 보존하는 변경 없는 원문 하나 또는 빈 값만 반환한다. final Gemma는 candidate를 자동
판정으로 신뢰하지 않으며 card v6·friendly metadata/product fact·모든 admitted 원문을 다시
읽고 V/E를 단독 확정한다.

이는 EXP153의 재실행이 아니다. EXP153은 item inventory 뒤 final을 4,000자 anchor로 축소했고
gold-evidence coverage도 6/38에 그쳤다. EXP188은 stage도 raw-source only이며 final은 모든
tokenizer-admitted source pack을 다시 읽는다. candidate가 null이어도 final은 원문과
metadata/card를 독립적으로 전부 판단한다. EXP180/182의 결과 때문에 날짜·절차 field를
추가하는 방식은 하지 않으며, EXP188은 그 field들을 **교체하지 않고** slot allocation만
item별로 바꾸는 단일 topology다.

### 아직 유료로 실행하지 않는 이유

EXP153은 24개 항목별로 문서 묶음당 한 구절만 요구했을 때 gold evidence 38개 중 6개만
navigation과 겹쳤다. 이 결과만으로 item-aware full-final이 실패한다고 결론낼 수는 없지만,
출력 부담이 너무 큰지 먼저 label-blind하게 확인해야 한다.

### 유료 전 단계: 효율 우선 feasibility experiment

다음 검사를 먼저 수행한다. 이 검사는 dev labels/predictions을 읽지 않는다.

1. 24개 item의 card에서 요구하는 사실 유형과 required document type을 추출한다. candidate
   prompt는 card 원문·법령·metadata를 보지 않는다.
2. 24-key × one-excerpt schema의 actual max serialized response와 final navigation burden을
   exact tokenizer로 profile한다. 24개의 candidate를 모두 채운 synthetic upper bound에서
   source omission 0 및 EXP171보다 작은 admission-only call variance를 보여야 한다.
3. 실제 stage prompt/schema의 empty, 24-key full, malformed, duplicate, source-outside excerpt,
   absence-item null candidate를 mock으로 검증한다. 여기서 Python은 exact substring/doc-id만
   다루며 candidate로 label을 만들지 않는다.
4. short/attachment/overflow에서 exact stage/final input을 export/read하고 24-item semantic
   contract을 final rendered prompt에서 audit한다.
5. 위 검사가 모두 통과할 때만 fast20을 실행한다. 이 feasibility experiment는 provider나 dev
   labels를 읽지 않으므로, output burden이 과도하면 유료 호출 없이 종료한다.

### EXP188 synthetic capacity result — 2026-09-10

`scripts/profile_exp188_item_aware_feasibility.py` used the exact Gemma chat-template tokenizer
and all dev200 notices, but no labels, predictions, or provider calls. It appended the conservative
upper bound of all 24 slots filled with a 180-character candidate before exact final packing.
`outputs/exp188-item-aware-feasibility-v1/profile.json` reports 226 final calls (batch-64 four
rounds), versus EXP171's 219 final calls, with 178/18/4 notices requiring one/two/three packs and
zero source-document omissions. Maximum admitted prompt is exactly 30,268 tokens.

This clears **only** the capacity gate: a one-candidate-per-item implementation may proceed, but
may not increase the per-slot length, add a second candidate, add another stage, or claim quality.
The actual source-only schema, parser, mock, rendered review, and semantic-contract audit remain
required before any paid call.

### EXP188 implementation gate — 2026-09-10

`configs/config.exp188-item-inventory-full-final-fast-panel-c4.yaml` declares EXP179 as base and
only `staged_run.mode` as an allowed change. Its stage prompt gets the public item names solely as
source-navigation directions; it gets no cards, metadata, product facts, law text, labels, or
final V/E task. Each v returns one unchanged 180-character-or-shorter source candidate or null.
Python resolves only original substrings/doc ids and never maps a candidate to a label.

The mock completed 20/20 and direct regression covers a normal full 24-key string/null payload,
its source provenance, null handling, and full-source final navigation. `pytest -q` passed 151.
Semantic contract audit passed all 24 items for short `PPS-DEV-062`, attachment `PPS-DEV-046`, and
overflow `PPS-DEV-082`; exact messages are under
`outputs/exp188-semantic-contract-audit-v1/rendered_inputs/`. Those messages were reviewed: stage
is source-only and final retains card v6, friendly metadata/product fact, all original source, and
an advisory item navigation section. The only permitted next action is the versioned fast20 run.

### EXP188 fast20 result — rejected (2026-09-10)

`outputs/exp-188-item-inventory-full-final-fast-panel-c4/` completed 20/20 with source-stage parse
errors 0, final recovery 0, and CSV validation pass (one positive-evidence warning). Macro
positive-F1 was `.215278`, below EXP179 `.287500` (`-.072222`), so no holdout or dev200 run is
allowed. Remote elapsed `186.5s` is not evaluator runtime evidence.

The failure is not malformed output or source omission. The one-slot constraint returned only
1/3/7 candidates at min/median/max per notice, whereas source-first v1 typically supplies a much
broader cross-category factual map. It removes 11 EXP179 positives, including TPs at v1, v4, v8,
v9, v12, v23, and v24; its only new positives are two v22 FPs. Thus item allocation did not make
the full-source final more selective in a useful way—it caused broad recall loss despite final
source availability. Evidence validity for its 12 positive evidence cases is `.9167`, so the score
loss is a decision-quality failure rather than substring validation failure.

**Decision: reject EXP188.** Do not increase candidates per item, tune item names, add selected
item slots, or combine this navigation with a verifier. Those would be density/item-group variants
already ruled out by EXP174/155/156 and would not repair this topology's recall loss.

## Architecture-search stop criterion — 2026-09-10

The complete-source branch has now tested every presently evidenced way to alter source navigation:
category cap, placement, exception taxonomy, conditional timeline relations, relation-ledger
replacement, item slots, and V-only/model-review loops. Only EXP171's original seven-category
source-first/full-final topology has same-direction fast, holdout, repeat, and dev200 evidence.
The other topology changes either lower fast quality or reverse on holdout. Repackaging any rejected
variant as a different candidate count, field name, verifier trigger, or v subset is not a new
structural hypothesis.

Accordingly, do not spend additional provider tokens on this family before one of the following
new evidence sources exists: (1) public feedback for the already submitted EXP171 archive, (2) a
real evaluator-vLLM runtime measurement that makes a different call topology feasible, or (3) a
label-blind source/provenance audit demonstrating a truth relation that seven categories cannot
represent and which is not the v23/procedure/item-slot family already tested. Until then,
`dist/pps_20260910_100059.zip` and its EXP171 tracked policy remain the incumbent; no change to
submission assets is warranted.

기존 계획의 다음 항목은 implementation 이후에만 수행한다.

1. item-aware schema의 worst JSON 크기, exact tokenizer admission, stage/final pack 수,
   1,853건 runtime 상한을 계산한다.
2. short complete / attachment / overflow record 각각에서 exact Stage-1 및 final messages를
   export한다. Stage-1은 raw source만, final은 cards/meta/product facts/full source/navigation을
   모두 포함하는지 사람이 읽어 확인한다.
3. mock에서 candidate null, malformed stage-1, duplicated candidate, absence item, final parse
   recovery, unchanged evidence validation을 검증한다.

### 오프라인 profile 결과 (2026-09-10)

`scripts/profile_source_first_full_final.py`를 exact Gemma chat-template tokenizer로 실행했다.
이 결과는 API/label을 사용하지 않으며, 현재 **범주형** navigation이 final admission에 만드는
여유만 측정한다. 산출물은 다음 ignored 경로에 남겼다.

- `outputs/exp178-item-aware-full-final-offline/source_first_v1_fast_profile.json`
- `outputs/exp178-item-aware-full-final-offline/source_first_v1_dev200_profile.json`

| dev-200 scenario | stage-1 calls | final calls | 합계 | final source omission |
| --- | ---: | ---: | ---: | ---: |
| 빈 navigation | 216 | 216 | 432 | 0 |
| 실제 EXP167 fast20 navigation (20건만) | 23 | 24 | 47 | 0 |
| 범주당 160자 1개 synthetic | 216 | 218 | 434 | 0 |
| 현재 schema 상한: 범주당 360자 3개 | 216 | 232 | 448 | 0 |

즉 현재 v1 범주형 schema는 navigation이 최대로 차도 dev-200에서 16회의 final pack만
추가한다. 반대로 이 수치는 **24-item schema의 안전성 증거가 아니다**. item-aware 후보는
실제 schema가 만들어진 뒤 동일 profile을 새로 통과해야 한다. 그 schema가 32k admission을
무너뜨리거나 final call 수를 의미 있게 늘리면, paid run 없이 종료한다.

이 검사가 통과하더라도 item별 v 하나씩 24회를 호출하지 않는다. 기본은 **한 stage-1
호출에서 24 item을 함께 반환**하는 최소 topology다. 이 방식의 schema 부담이 admission 또는
mock 안정성을 해치면 유료 실행 대신 이 후보를 종료한다. item group을 여러 호출로 나누는
확장은 source-first v1보다 call 수가 크게 늘어나므로, fast20에서 quality 이득이 확인되기
전에는 설계하지 않는다.

### 유료 fast20 gate

오프라인 검증을 통과할 때만 20건의 versioned fast panel에서 one-variable probe를 실행한다.

- base config: EXP167.
- allowed change: `staged_run.mode` 하나.
- stage-1은 item별 raw source candidate 또는 null만 낸다. label/판정/evidence 확정은 금지한다.
- final은 EXP167과 같은 full source + V/E output을 유지한다.
- success: parser/CSV 20/20, source omission 0, final recovery 0, evidence warning 악화 없음,
  fast F1이 EXP167보다 높을 때만 independent holdout으로 진행한다.
- fast F1이 낮거나 stage-1 coverage/형식이 나쁘면 항목별 prompt tuning 없이 branch를 종료한다.

## 이번 단계에서 명시적으로 하지 않는 것

- navigation candidate 수를 5개 이상으로 다시 늘리기
- navigation section의 앞/뒤 위치 재변경
- taxonomy 이름을 더 늘리기
- v별 hard-code, dev 오류 예외, Python label override
- full split × item grouping, raw-law RAG, final 4k 축소

위 항목은 이미 같은 원인에 대한 반복이거나 source coverage/runtime contract를 악화시킨다.

## 실행 순서

1. 이 문서의 label-blind architecture audit을 구현/실행하고 결과를 여기에 추가한다.
2. 코드/config가 필요한 경우 mock·preflight·semantic contract·exact rendered input review를
   마친다.
3. 그때만 fast20 paid run을 실행하고, 완료까지 process를 감시한다.
4. fast20이 통과하면 policy-identical independent holdout, 그 뒤에만 dev200으로 확대한다.
