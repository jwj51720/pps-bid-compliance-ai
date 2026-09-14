# Post-EXP208 local quality program

작성: 2026-09-14, dev / mac

## 목표와 현재 기준

목표는 submission packaging이 아니라, corrected complete input을 유지하는 runtime-compatible
구조에서 local Macro positive-F1을 먼저 높이는 것이다.

- quality ceiling control: EXP200 repaired dev200 `.324798`, source-first 438 calls, evaluator
  120분 초과.
- runtime-compatible candidate: EXP208 dev200 `.292959`, one-stage 219 source-pack messages.
- matched direct control EXP209 `.257457`; relation checklist의 순효과는 `+.035502`다.
- 다음 승격 목표는 fast/holdout/dev200의 방향 일치, dev200 `.300000` 초과, EXP208 대비
  zero-TP item 감소와 TP 보존이다. 최종적으로는 EXP200 quality를 219-call 안에서 넘는 것을
  목표로 한다.

## 절대 고정할 semantic input contract

모든 후보는 다음을 실제 final rendered prompt에 유지한다.

1. `decision_cards_v10_v6_v7_scope.json`의 24개 항목별 적용범위, 1 조건, 중요한 0
   조건·예외.
2. 필요한 human-readable organizer metadata와 anonymization semantics.
3. `competition_products_v1.json`의 exact-code, 조건·사람이 읽을 수 있는 provenance 사실.
4. 공고문·규격서·과업지시서·제안요청서·예외공표서의 모든 exact-token admitted 원문.

법령 원문/RAG, generic 사례 RAG, dev 예시, raw metadata JSON/internal status/code, Python
법률·label rule은 넣지 않는다. 어떤 후보도 첨부문서나 0 조건을 줄여서 token을 확보하지 않는다.

## 먼저 답할 진단 질문

EXP208의 모든 FP/FN을 아래 서로 다른 층으로 분해한다.

1. **입력 관측성:** gold evidence가 organizer source와 실제 rendered message에 있었는가.
2. **적용범위/사실 탐색:** 보이는 triggering fact가 있는데도 0인지, gold evidence가 비어 있어
   source만으로 위치를 확인할 수 없는지.
3. **관계 판단:** 같은 주체·역할·조항·AND/OR endpoint를 잘못 연결했는가.
4. **부재 판단:** v10/v11/v16/v18/v20처럼 whole-notice presence check를 수행하지 못했는가.
5. **출력·병합:** overflow pass, malformed response, evidence 생성, frozen postprocess가 label을
   손상했는가.

Gold는 사후 오류 분류와 실험 평가에만 사용한다. routing, prompt example, threshold, rule에는
사용하지 않는다. 자동 감사 뒤에는 대표 FP/FN을 source/card와 사람이 읽고, 확인되지 않은
원인을 단정하지 않는다.

## 후보 순서

### EXP210 — corrected relation-checklist V-only output ablation

- base: EXP205 fast20.
- allowed change: `prompt.output_mode`만 `labels_and_evidence -> labels_only`.
- 목적: 현재 complete input과 검증된 relation checklist에서 evidence 동시 생성이 label recall,
  parse 안정성, attention을 실제로 손상하는지 분리한다.
- 호출 추가, V voting, resolver, evidence algorithm은 없다.
- 과거 EXP125/186/187의 V-only 및 반복 V-only는 recall 하락으로 기각됐다. EXP210은 그 구조를
  반복하는 후보가 아니라, corrected input + 관계 체크리스트에서 output contract 하나만 바꾸는
  마지막 최소 ablation이다.
- fast20에서 EXP205 `.325000`을 이기고 total TP/recall이 감소하지 않으며 parse error 0일 때만
  holdout으로 간다. 실패하면 V-only wording, 반복 호출, evidence algorithm으로 확대하지 않는다.

#### EXP210 pre-provider gate — 2026-09-14

- preflight는 EXP205 대비 `prompt.output_mode` 하나만 검출했다.
- exact fast20 admission은 24 messages, dev200 complete-fact audit은 374/374 documents,
  source omission 0, metadata/card/organizer-semantics omission 0, over-budget pack 0이다.
- short `PPS-DEV-062`, attachment `PPS-DEV-194`, overflow `PPS-DEV-169`의 실제 rendered
  messages를 `outputs/exp210-preflight/rendered_inputs/`에서 읽었다. 세 경우 모두 cards,
  human-readable metadata, organizer semantics, product facts, admitted original source와
  source 뒤 checklist를 유지한다. V-only에서는 checklist의 마지막 출력 지시도 V-only로
  바뀌어 V/E 계약과 충돌하지 않는다.
- 같은 세 record의 semantic-input contract audit은 각각 24/24를 통과했다.
- exact config mock은 fast20 20/20, 49-column/ID/schema validation을 통과했다. V-only의 blank
  evidence는 예상 limitation이며 이 진단은 label F1만 비교한다.
- full tests: 204 passed.

따라서 output-contract 하나를 검증하는 fast20 provider run만 승인한다.

#### EXP210 result

- EXP205 `.325000` -> EXP210 `.256944`, delta `-.068056`.
- TP/FP/FN `14/4/24` -> `12/2/26`. FP는 줄었지만 v1, v12, v23 TP를 잃어 macro와
  recall gate를 실패했다. v19 TP 회복과 v13/v19/v24 FP 제거는 전체 손실을 보상하지 못했다.
- 24 messages, 28.1 s, prompt/completion `373,170/4,416`, parse error 0. V-only는
  completion/runtime을 줄였지만 label quality를 높이지 못했다.
- paired artifact: `outputs/exp210-preflight/paired_exp205_exp210.json`.

결정: holdout/dev200을 실행하지 않는다. V-only wording, 반복 V-only, consensus/resolver,
Python evidence algorithm으로 확대하지 않는다.

### EXP211 — one-call structured decision protocol

EXP210 결과와 별개로, 오류 감사가 all-item prompt의 절차 누락을 지지할 때만 설계한다.
V/E output과 24개 카드 원문은 유지하고, 판정 직전 지시를 다음처럼 이해하기 쉬운 고정 절차로
구조화한다.

1. 적용대상인가.
2. 원문에 실제 의무·제한·부재·불일치가 있는가.
3. 동일 주체·semantic role·조항·AND/OR 범위인가.
4. 카드의 0 조건·예외와 양립하는가.
5. 1이면 정확한 source substring을 연결한 뒤 JSON을 출력한다.

이는 card 수정이나 chain-of-thought 출력 schema가 아니다. 모든 항목을 한 호출 안에서
qualification/product/absence/document/contract/schedule/metadata family로 인지시키되, final
output은 기존 v1-v24 V/E 하나다. 정확한 family 문구와 대상 항목은 오류 감사에서 broad하게
재현된 failure type만 사용한다.

EXP208 사후 감사 결과는 TP/FP/FN `51/78/102`다. FN 중 22개는 gold exact span이 실제
rendered input에 있었고, source에는 있으나 rendered input에서 빠진 FN은 0개다. 31개는
v10/v11/v16/v18/v20의 whole-notice absence FN이며 이 다섯 항목은 모두 TP 0이다. multi-pack
FN은 2개, parse-error record의 FN은 1개뿐이므로 overflow/parse가 주 병목이라는 설명은
기각한다. 49개 blank-gold-evidence FN은 이 감사만으로 source 위치나 법적 원인을 단정하지
않는다. 생성물은 `outputs/exp208-failure-modes/`에 있다.

#### EXP211 pre-provider gate — 2026-09-14

- base는 EXP205이고 allowed/effective change는 `prompt.mode` 하나다. V/E schema, cards,
  source admission, metadata/product facts, merge, postprocess, provider parameter는 같다.
- exact fast20 admission은 24 messages다. dev200은 181x1 + 16x2 + 3x3 = 222 messages,
  374/374 source documents, omission 0, over-budget pack 0이다. EXP208보다 고정 prompt가
  길어져 overflow boundary에서 3 messages 증가한다.
- rendered short/attachment/overflow를 `outputs/exp211-preflight/rendered_inputs/`에서 읽었다.
  기존 입력을 모두 유지하며 원문 뒤에만 독립 적용범위 -> 실제 사실 -> 관계 -> 0/예외 ->
  evidence 순서와 absence/product/relationship 확인을 둔다.
- 세 record semantic-input contract는 각각 24/24, exact mock은 20/20과 submission schema를
  통과했다. full tests는 205 passed다.

따라서 구조적 prompt 하나의 fast20 provider run만 승인한다.

#### EXP211 fast20 result와 holdout 조건부 승인

- EXP205 `.325000` -> EXP211 `.330556`, delta `+.005556`.
- TP/FP/FN `14/4/24` -> `16/5/22`. v4는 `0 -> .800`, v19는 `0 -> .667`로 TP를
  회복했고 v13/v24 FP가 줄었다. 반면 v12 TP가 사라지고 v15/v17/v23 FP가 늘었다.
- 핵심 absence family v10/v11/v16/v18/v20은 여전히 TP 0이다. 따라서 absence 강조가
  성공했다는 결과가 아니라, 독립 적용·관계 절차의 v4/v19 신호로만 해석한다.
- 24 messages, 60.4 s, prompt/completion `386,443/16,269`, parse error 0,
  evidence warning 4. paired artifact는
  `outputs/exp211-preflight/paired_exp205_exp211.json`이다.

Macro와 total TP/recall이 모두 개선됐지만 delta가 작고 corrected/regressed가 섞였다. 문구를
재조정하지 않고 policy-identical independent holdout EXP212를 한 번 실행한다. matched control은
EXP206이다. Holdout에서 macro 또는 TP/recall이 하락하면 dev200으로 확장하지 않는다.

#### EXP212 holdout result

- EXP206 `.208333` -> EXP212 `.208333`, delta `0`.
- TP/FP/FN `5/11/10` -> `5/10/10`. TP와 recall은 그대로이며 fast의 v4/v19 TP 회복은
  재현되지 않았다.
- v13/v17/v19 FP는 줄었지만, 동일한 PPS-DEV-110에서 v10/v11/v16/v18/v20이 모두 0->1
  FP로 움직였다. 전역 absence 강조가 적용대상 분리 없이 family 전체의 label을 함께 움직인
  명확한 부작용이다.
- 22 messages, 53.1 s, prompt/completion `362,880/14,090`, parse error 0.
  paired artifact는 `outputs/exp212-preflight/paired_exp206_exp212.json`이다.

결정: fast gain이 independent holdout macro/TP로 확인되지 않았으므로 dev200을 실행하지 않는다.
전역 실행 절차를 더 강하게 고치지 않는다. 다음 구조 후보는 한 항목의 적용대상과 실제 사실을
observable field로 분리해 final label owner인 Gemma가 스스로 대조하는 최소 schema여야 한다.

### EXP213 — v4 one-call fact-first review

v4를 가장 작은 대상으로 고른다. EXP208 dev200에서 v4는 TP/FP/FN `0/1/6`이고, FN 6개 중
5개 gold exact span이 실제 rendered prompt에 있었다. fast20에는 v4 positive 3개가 있고
EXP205는 모두 놓쳤다. EXP211의 전역 절차가 fast에서 2개를 회복했지만 holdout의 v4 positive는
회복하지 못했다. 이 관찰은 문서 누락보다 v4 내부 조건을 끝까지 대조하지 않는 문제가 있음을
시사하지만 인과로 단정하지 않는다.

- base: EXP205 fast20.
- allowed change: `prompt.mode` 하나. mode가 v4 observable review + 기존 final V/E schema를
  감싼 one-call response schema를 선택한다.
- response 순서: `v4검토` 후 `판정`. v4 검토는 `참가자격실적근거`, `금액구간`,
  `특정발주기관한정`, `특정실적종류한정`, `구체적필요사유`와 `카드대조`를 명시한다.
- 원문 근거는 Python이 substring 여부만 기록한다. Python은 검토값으로 v4 label을 계산하거나
  override하지 않는다. final 24 V/E는 Gemma가 소유한다.
- 카드, metadata/product facts, 모든 원문, relation checklist, merge, postprocess, provider는
  고정한다. 별도 호출이나 item group은 없다.
- fast20에서 v4 TP/F1이 개선되고 전체 macro/TP가 하락하지 않으며 malformed가 허용 수준일
  때만 independent holdout으로 간다. 실패하면 v4 field/enum wording을 dev에 맞춰 반복하지
  않고 종료한다.

#### EXP213 pre-provider gate — 2026-09-14

- preflight는 EXP205 대비 `prompt.mode`만 검출했다. mode가 observable schema를 선택하지만
  final V/E semantics와 label owner는 바뀌지 않는다.
- fast20 exact admission은 24 messages, dev200은 181x1 + 16x2 + 3x3 = 222 messages다.
  374/374 documents와 metadata/cards/product/organizer semantics omission 0, over-budget 0이다.
- rendered short/attachment/overflow를 `outputs/exp213-preflight/rendered_inputs/`에서 읽었다.
  각 source pack 뒤 기존 relation checklist 다음에 v4 review 지시가 있고 모든 fixed input이
  유지된다. semantic-input contract는 세 record 모두 24/24다.
- mock 20/20, custom schema/parser/source-substring audit, 49 columns, tests 207 passed.

따라서 v4 one-item structured review의 fast20 provider run만 승인한다.

#### EXP213 fast20 result

- EXP205 `.325000` -> EXP213 `.314087`, delta `-.010913`.
- TP/FP/FN `14/4/24` -> `16/9/22`. 전체 TP는 2개 늘었지만 FP가 5개 늘어 macro gate를
  실패했다.
- 목표 항목 v4는 `0/0/3` -> `2/2/1`, F1 `0 -> .571429`로 실제 회복했다. 두 TP의
  `참가자격실적근거`는 모두 원문 substring 검증을 통과했다. 세 번째 positive는 모델이
  금액구간을 0 조건으로 대조해 0을 유지했다.
- 그러나 v6 FP 1개, v17 FP 3개, v23 FP 2개가 새로 생기고 v12 TP 1개를 잃었다. v4를
  먼저 구조화한 것이 v4 관찰에는 도움을 주었지만, 같은 generation의 나머지 23개 판단을
  안정시키지 못했다.
- 24 messages, 90.0 s, prompt/completion `385,603/23,385`, parse error 0. paired artifact는
  `outputs/exp213-preflight/paired_exp205_exp213.json`이다.

결정: holdout/dev200으로 확장하지 않는다. v4 field/enum을 fast 결과에 맞춰 반복 수정하거나
같은 schema를 여러 v로 일반화하지 않는다. 다만 source-grounded observable fact가 target
항목 TP를 실제로 회복했다는 관찰은, 호출 수를 늘리지 않는 더 넓은 fact-first 구조의 설계
근거로만 보존한다.

### EXP214 — one-call seven-category fact inventory then judgment

#### 가설

EXP200은 모든 원문을 두 번 읽어 `.324798`까지 올랐지만 제출시간을 넘었고, EXP208은 한 번만
읽어 `.292959`였다. EXP213은 같은 응답에서 원문 사실을 먼저 쓰게 하자 목표 v4의 TP를 실제로
회복했으나 item-specific review가 나머지 판단을 교란했다. 따라서 이미 EXP171/200에서 검증한
중립적 7개 source category를 **같은 한 응답의 앞부분**에 짧게 작성하고, 이어서 24 V/E를
판정하게 한다. autoregressive output상 사실목록이 판정보다 먼저 생성되므로 두 번째 full-source
prefill 없이 source-first의 집중 효과를 일부 재현할 수 있는지 검증한다.

이 실험은 EXP152/154의 “모든 정보를 입력에 한꺼번에 추가”와 다르다. 추가 입력이나 법령은
없으며, 모델이 방금 읽은 원문에서 만든 observable source fact가 최종 판단 앞에 위치한다.
EXP153/157처럼 final에서 원문을 제거하지도 않는다. 모든 admitted 원문은 같은 메시지에 그대로
남는다.

#### base와 허용 변경

- base: EXP205 fast20.
- allowed change: `prompt.mode` 하나.
- response key 순서는 `사실목록`, `판정`이다. `사실목록`은 EXP171의 7개 범주 각각 최대 2개
  unchanged source substring이고, `판정`은 기존 24 V/E schema 그대로다.
- 최대 2개는 출력 길이 상한일 뿐 원문 입력을 자르지 않는다. 모델은 최종 판정에서 사실목록에
  없는 내용도 반드시 전체 원문에서 다시 확인한다. 빈 범주는 final 0을 뜻하지 않는다.
- Python은 excerpt substring 검증과 audit 저장만 한다. 사실목록으로 label을 만들거나 override,
  routing, merge하지 않는다.
- cards, human-readable metadata, product facts, organizer semantics, source scope/order, exact-token
  admission, relation checklist, merge/evidence, postprocess, provider parameters는 고정한다.
- 호출 topology는 EXP205와 같은 one-stage context count다. item grouping이나 verifier 호출은 없다.

#### 유료 전 및 성능 gate

1. preflight가 `prompt.mode` 외 effective change 0을 확인한다.
2. fast/dev200 exact admission과 374/374 source coverage를 재확인한다.
3. short/attachment/overflow exact rendered prompt에서 7개 범주 지시가 source 뒤에 있고, cards,
   metadata/product facts, 모든 admitted 원문, relation checklist가 남는지 읽는다.
4. 세 record의 24/24 semantic-input contract, exact mock, parser/malformed recovery, substring audit,
   49-column output을 확인한다.
5. fast20에서 EXP205 `.325000`을 넘고 TP가 감소하지 않으며 parse error가 허용 수준일 때만
   policy-identical holdout으로 간다. 실패하면 범주 수·후보 수·위치를 dev에 맞춰 반복하지 않는다.

#### EXP214 pre-provider gate — 2026-09-14

- preflight는 EXP205 대비 `prompt.mode` 하나만 검출했다. cards, product/metadata facts, source
  admission, relation checklist, merge, postprocess, provider parameters는 동일하다.
- dev200 exact admission은 181x1 + 16x2 + 3x3 = 222 messages, 374/374 source documents,
  source/metadata/card/organizer-semantics omission 0, over-budget pack 0이다.
- short `PPS-DEV-062`, attachment `PPS-DEV-194`, overflow `PPS-DEV-169`의 actual rendered
  messages를 `outputs/exp214-preflight/rendered_inputs/`에서 읽었다. 각 pass에서 원문 뒤 기존
  relation checklist 다음에 fact-first 지시가 있으며 fixed input은 모두 유지된다.
- 같은 세 record의 semantic-input contract는 각각 24/24를 통과했다.
- exact mock은 fast20 20/20, 24 context passes, parse error 0, category review 24개 저장,
  49 columns/unique ID를 통과했다. nested-schema mock regression도 수정했다.
- full tests: 208 passed.

가설에 필요한 구성요소가 모두 구현·선택됐으므로 EXP214 fast20 provider run만 승인한다.

#### EXP214 fast20 result

- EXP205 `.325000` -> EXP214 `.269444`, delta `-.055556`.
- changed cells는 corrected 5 / regressed 5였다. v19는 `0/2/1 -> 1/0/0`으로 완전히
  회복하고 v13·v24 FP도 줄었지만, v12와 v22의 유일한 TP를 잃었고 v17 FP 2개와 v23 FP
  1개가 생겼다. sparse fast panel에서 TP의 item 분포가 나빠져 macro가 크게 하락했다.
- 24 context passes, 85.7 s wall time, summed latency 312.2 s, prompt/completion
  `385,939/30,644`, parse error 0, finish reason 전부 stop이다.
- 선출력 사실은 205개였고 Python exact substring 검증을 통과한 것은 153개(74.6%)였다.
  schema는 정상이어도 25.4%가 원문 그대로라는 source-grounding 계약을 지키지 못했다.
- paired artifact: `outputs/exp214-preflight/paired_exp205_exp214.json`.

결정: macro gate와 source-grounding gate를 모두 실패했으므로 holdout/dev200을 실행하지 않는다.
범주 수, 최대 발췌 수, 지시 위치를 반복 조정하지 않는다. 한 generation 안에서 긴 사실목록을
먼저 출력하는 방식은 target별 주의를 재배분할 뿐, EXP200의 독립 source-reading pass를
대체하지 못했다.

### EXP215 — source-first/full-final plus proven relation checklist

#### 가설과 우선순위

현재 local quality ceiling은 EXP200 repaired `.324798`이고, one-stage EXP208의 relation
checklist는 matched EXP209 대비 dev200 `+.035502`를 냈다. 이 두 효과는 아직 결합해 본 적이
없다. source-first inventory가 사실 탐색과 FP 억제를 맡고, final 원문 뒤 checklist가 v8/v19 등
관계 조립을 보완하면 local ceiling을 높일 수 있는지 먼저 본다.

이는 runtime 후보가 아니라 **local quality upper-bound 실험**이다. public timeout topology를
그대로 가지므로, quality가 확인돼도 제출 승격 전에 별도 압축/실행 구조가 필요하다. 그러나
지금 단계에서는 어떤 판단 구조가 실제로 정확한지 먼저 확정한다.

#### base와 허용 변경

- base: `configs/config.exp196-corrected-input-source-first-fast-panel-c4.yaml`.
- allowed change: `prompt.mode: baseline -> relation_checklist_after_source_v1` 하나.
- stage 1의 7-category source-only inventory, final의 inventory + 모든 admitted source,
  corrected cards/metadata/product/organizer semantics, V/E schema, merge, retry, postprocess,
  provider parameters는 고정한다.
- relation checklist는 final user message의 모든 원문 뒤에만 붙으며, stage 1 schema/prompt는
  바꾸지 않는다. source-first와 v-item grouping은 결합하지 않는다.
- fast에서 base EXP196 `.213889`보다 macro/TP가 개선되고 parse가 안정적일 때만 같은 fixed
  holdout으로 간다. fast 절대치가 one-stage EXP205 `.325000`보다 낮으면 local ceiling 후보로는
  약하다고 명시한다.

#### EXP215 pre-provider gate — 2026-09-14

- preflight는 EXP196 대비 `prompt.mode` 하나만 검출했다.
- 최초 staged rendered review에서 기존 builder가 relation checklist 뒤에 inventory를 별도 user
  turn으로 붙여 checklist가 판정 직전이 아님을 발견했다. 유료 실행 전에 `append_fact_inventory`
  가 relation mode에서 checklist를 중복 없이 inventory 뒤로 이동하도록 수정하고 regression test를
  추가했다. 이것은 EXP215의 선언된 prompt-mode 구현이며 label/merge 변경이 아니다.
- corrected exact mock은 20/20, inventory/final 각각 24 calls, 양 단계 parse error 0,
  49-column/ID/evidence validation PASS다. staged rendered output에서 short `PPS-DEV-062`,
  attachment `PPS-DEV-194`, overflow `PPS-DEV-169`의 각 final pass가 `원문 -> inventory ->
  relation checklist` 순서이고 checklist는 pass당 정확히 한 번이다.
- dev200 exact source-first profile은 empty-navigation 기준 stage 1 219 + final 221 = 440 calls,
  양 단계 source omission 0이다. final direct admission은 374/374 documents, metadata/card/
  organizer-semantics omission 0, over-budget 0이며 실제 inventory 길이에 따라 final calls는 늘 수 있다.
- 세 review record의 semantic-input contract는 각각 24/24다. full tests: 209 passed.

가설의 실제 구성요소가 끝 위치까지 검증됐으므로 EXP215 fast20 provider run만 승인한다.

#### EXP215 fast20 result와 independent confirmation

- corrected source-first EXP196 `.213889` -> EXP215 `.269444`, delta `+.055556`.
  changed cells는 corrected 7 / regressed 2다.
- v8과 v22의 유일한 TP를 회복했고, v23 FP를 4->1로 줄이며 v9 FP도 제거했다. 반면 v12의
  유일한 TP를 잃고 v23 FP 하나를 새로 만들었다.
- one-stage relation EXP205 `.325000`보다는 `.055556` 낮다. 따라서 fast 최고 후보는 아니지만,
  source-first 내부에서 relation checklist의 순효과는 명확한 양의 방향이다.
- 48 context calls, 108.7 s, parse error 0. paired artifacts는
  `outputs/exp215-preflight/paired_exp196_exp215.json`과
  `outputs/exp215-preflight/paired_exp205_exp215.json`이다.

기존 source-first holdout EXP168은 구형 cards/product/metadata라 matched control이 아니다.
독립 holdout에서 corrected source-first EXP216과 동일 정책+relation EXP217을 둘 다 실행한다.
EXP217이 EXP216보다 macro와 TP/recall에서 개선되지 않으면 dev200으로 확장하지 않는다.

### EXP212 이후 — 최소 item grouping 또는 selective specialist

다음이 입증될 때만 고려한다.

- 같은 complete input의 all-item call에서 특정 family가 지속적으로 zero-TP이고,
- 그 truth condition은 현재 prompt에 완결되어 있으며,
- EXP211의 one-call 구조화로 회복되지 않고,
- 별도 작은 호출이 fast panel에서 해당 family TP를 회복하면서 다른 family를 손상하지 않는다.

과거 full v grouping, document x v-group multiplication, source-first x grouping, multiple V-only
consensus는 반복하지 않는다. 그룹화를 한다면 가장 작은 한 family만 specialist로 관찰하고,
Python OR/majority가 아니라 Gemma final owner 또는 기존에 정당화된 merge만 사용한다. 예상
test call count와 120분 위험을 quality 평가 전에 계산한다.

## 모든 유료 후보의 gate

1. config에 `experiment.base_config`와 정확한 `allowed_policy_changes`를 선언한다.
2. `scripts/preflight_experiment.py`가 undeclared difference 0을 확인한다.
3. exact tokenizer admission으로 source coverage/provenance와 call topology를 기록한다.
4. short complete, attachment, overflow의 실제 rendered system/user messages를 내보내 읽는다.
5. 24개 semantic-input contract가 final message에서 24/24인지 감사한다.
6. 동일 config의 mock, 49열·ID·parse recovery·evidence validation을 확인한다.
7. fast20은 `configs/dev_fast_panel_v1.json`만 사용한다.
8. fast gain은 matched independent holdout20 이후에만 dev200으로 확장한다.
9. metrics, per-item TP/FP/FN, parse/finish reason, evidence validity, calls, tokens, runtime,
   paired changed cells를 isolated output에 남긴다.
10. prompt structure, output schema, grouping, card, merge, provider parameter를 한 실험에서 섞지
    않는다.

## 중단 규칙

- headline macro 상승만으로 통과시키지 않는다. TP/recall 붕괴, zero-TP item 증가, source
  omission, malformed 증가가 있으면 중단한다.
- dev200 특정 ID나 문구를 prompt/card/rule로 넣지 않는다.
- fast/holdout 방향이 다르면 wording 반복으로 맞추지 않는다.
- EXP200보다 느리거나 evaluator 120분 위험이 같은 구조는 local score가 높아도 submission
  후보로 부르지 않는다.
