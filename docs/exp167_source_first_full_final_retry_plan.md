# EXP167 — source-first/full-final clean retry plan

작성일: 2026-09-09 (dev / mac)

## 왜 이 branch인가

EXP154의 complete-source one-stage는 모든 사실을 보존했지만 24개 항목의 법률 판단과
근거 생성을 동시에 요구해 fast20 0.241667에 그쳤다. 단순 item partition EXP155/156도
각 group에 complete source를 반복 제공했지만 0.237500/0.213889로 낮았다. 반면
source-first/full-final은 모델에게 다음 두 역할을 명확히 분리한다.

1. **Stage 1 navigation:** 각 tokenizer-admitted source pack에서 원문에 있는 사실 후보만
   item별로 기록한다. 0/1, 법령 해석, final evidence를 내지 않는다. `없음`은 그 pack에서
   찾지 못했다는 뜻일 뿐 final 0이 아니다.
2. **Stage 2 final V/E:** Stage-1 navigation과 cards, friendly organizer metadata/CSV,
   그리고 **모든 원문을 다시** 받아 24개 V/E를 최종 판정한다. final stage는 navigation을
   보조 인덱스로만 사용하며 source 원문으로 항상 재확인한다.

따라서 EXP157처럼 final이 4k anchor에 의존하지 않고, EXP153처럼 inventory null을 0으로
조립하지 않는다. Python은 final JSON parse/evidence substring validation/ordered pack merge만
담당하며 navigation에서 위반을 판정하지 않는다.

## 기존 미완결 실행과의 관계

EXP160(c20), EXP161(c4), EXP162(c1)은 같은 logical policy의 원격 호출이지만 provider
in-flight-credit HTTP 402로 각각 18/20, 15/20, 13/20에서 멈췄다. partial predictions는
품질 계산에 쓰지 않았고 세 config는 invalidated다. 이번 EXP167은 사용자 확인의 credit
복구 후 새 ID·새 output에서 처음부터 실행한다. concurrency 4는 policy가 아니라 provider
reservation을 낮추는 scheduling setting이다.

## 비교 계약

Base는 EXP154 complete-source 32k one-stage V/E다. EXP167의 선언된 차이는 아래뿐이다.

- output reserve / generation upper: 1,536 → 2,500 (navigation과 final V/E의 schema 여유)
- staged mode: `fact_inventory_full_final_v1`
- concurrency: 20 → 4

Decision cards v6, exact friendly product fact, 21 human-readable metadata fields, all supplied
source documents, absence AND/non-absence merge, frozen EXP123 v2/v3/v21 postprocess, model,
temperature/seed/provider는 고정한다. Raw law/RAG, dev-label rule, source selection, final
label Python override는 추가하지 않는다.

## 유료 전 gate와 확대 기준

유료 fast20 전에는 preflight, full dev-200 exact final admission, dynamic semantic contract,
short/attachment/overflow의 actual Stage 1과 Stage 2 rendered-message review, mock parser/CSV,
and regression suite를 통과해야 한다. 특히 Stage 2 source coverage가 0 omission인지 확인한다.

quality는 20/20 response일 때만 기록한다. EXP154보다 fast macro positive-F1가 의미 있게
높고, 독립 holdout에서도 같은 방향이며 navigation·final parse/evidence 오류와 runtime
projection이 수용 가능할 때만 dev-200을 검토한다. fast-only gain 또는 partial response는
승격 근거가 아니다.

## EXP167 유료 전 검토 (2026-09-09)

- Preflight는 EXP154 대비 선언된 4개 차이만 확인했다: `output_reserve_tokens`와
  `llm.max_tokens` 1,536→2,500, `staged_run.mode` 추가, 그리고 concurrency 20→4.
- `outputs/exp167-source-first-full-final-feasibility-v4.json`은 exact Gemma chat-template
  profile이다. 모든 scenario에서 stage 1과 final stage의 source-document omission은
  **0**이다. no-navigation/full dev200은 stage1 216 + final 216 = 432 calls,
  saved 20-record navigation은 23 + 24 = 47 calls, schema-upper ledger에서는 448 calls다.
  즉 quality fast probe에는 가능하지만 submission runtime risk가 크며, 결과가 좋아도
  즉시 submission candidate로 올리지 않는다.
- Mock fast20은 20/20, JSON parser/CSV validation error 0이었다. 
  `outputs/exp-167-source-first-full-final-fast-panel-c4-mock/staged_input_examples.md`에서
  PPS-DEV-062(짧은 one-pass)와 PPS-DEV-169(제안요청서 첨부 + overflow)의 Stage 1/Stage 2
  실제 메시지를 읽었다. Stage 1은 source-only fact copy schema를, Stage 2는 모든 card,
  readable metadata/CSV, notice source와 navigation section을 가진 V/E schema를 사용한다.
  Navigation의 빈 배열은 final 0으로 조립되지 않는다.
- 이 검토 중 staged markdown exporter가 fact-inventory mode의 nested message packs를
  빈 Locator로 표시하던 **관측성 전용** bug를 발견해 수정했고 mock을 새로 생성했다.
  pipeline prediction/merge 의미는 변경하지 않았다. Regression suite는 144 passed,
  `git diff --check`도 통과했다.

따라서 새 EXP167 remote fast20은 source-first/full-final architecture의 첫 valid quality
probe다. 20/20 완료를 끝까지 확인하고, provider partial row는 이전 EXP160–162처럼
invalidated로만 남긴다.

## EXP167 fast-20 결과

EXP167은 20/20 complete, JSON parser/CSV validation failure 0, final recovery 0으로
완료됐다. macro positive-F1은 **0.286111**로 EXP154의 0.241667보다 +0.044444였다.
주요 변화는 v8 FN 1건의 TP 전환, v12 FN 1건의 TP 전환(+FP 1), v19 TP 1건의 FN 전환,
v23 FP 1건 감소다. 따라서 headline 상승은 두 개의 희소 positive item에 크게 의존하며,
fast-only 승격 근거가 아니다.

| policy | macro F1 | calls | runtime | prompt / completion tokens | evidence validity |
| --- | ---: | ---: | ---: | ---: | ---: |
| EXP154 complete one-stage | 0.241667 | 22 | 40.5 s | 336,480 / 14,370 | 0.8261 |
| EXP167 source-first/full-final | **0.286111** | 47 | 165.0 s | 628,587 / 30,620 | 0.7000 |

navigation은 notice별 8–21 excerpt(중앙 12)를 남겼다. 모든 final label은 여전히 stage 2의
source-complete V/E이고 navigation null은 final 0이 아니다. 단, remote usage는
PPS-DEV-169 completion을 3,655로 보고해 configured 2,500을 넘었다. 이는 EXP165/166에서
확인한 OpenRouter usage-cap non-parity와 같은 경고이므로 source-first의 submission runtime을
이 remote wall time으로 확정하지 않는다.

다음은 `config.exp168-source-first-full-final-holdout-c4.yaml`의 frozen independent holdout
20건이다. config는 EXP167과 policy-identical이고 evaluation cohort/output만 다르다. holdout
전용 preflight, mock, staged rendered-message review를 다시 통과한 뒤에만 실행한다.

## EXP168 유료 전 검토

- Preflight: EXP167 대비 effective policy difference 0.
- Mock: 20/20, parser/CSV validation error 0.
- Semantic contract: `outputs/exp168-semantic-contract-audit-v1/` PASS.
- Staged exact-message review:
  `outputs/exp-168-source-first-full-final-holdout-c4-mock/staged_input_examples.md`의
  PPS-DEV-094(짧은 공고문), PPS-DEV-046(규격서 첨부), PPS-DEV-082(제안요청서·규격서 첨부와
  overflow)를 읽었다. 각 stage 1은 raw source facts만, final은 navigation + cards + friendly
  metadata/CSV + source packs로 구성되며, 2차 source omission은 EXP167 dev200 exact profile의
  0-omission invariant 아래에서 admission된다.

이제 EXP168 remote run은 fast 결과를 본 뒤 policy를 바꾸지 않은 valid independent holdout
test다.

## Capacity-matched controls와 dev-200 gate

EXP169/170은 EXP167/168에서 stage navigation만 제거하고 같은 2,500 output reserve,
same 32k source admission, decoder, postprocess, concurrency를 유지한 one-stage controls다.

| cohort | one-stage 2,500 | source-first/full-final | delta |
| --- | ---: | ---: | ---: |
| frozen fast-20 | 0.262500 | 0.286111 | +0.023611 |
| independent holdout-20 | 0.211111 | 0.229167 | +0.018056 |

두 cohort 모두 source-first가 v4 recall을 하나 잃었지만, fast에서는 v8, holdout에서는
v22 TP를 얻고 v23 FP를 하나 줄였다. 항목은 작아 불확실성이 크지만, 두 방향이 같고
capacity-only control보다 높으므로 `config.exp171-source-first-full-final-dev200-c4.yaml`로
dev-200을 확인한다. 이 config는 EXP167과 policy-identical이며 cohort/output만 다르다.
dev-200이 control 수준을 유지하거나 넘고 parser/evidence/runtime gate를 통과할 때만
submission feasibility를 별도 검토한다; 그렇지 않으면 source-first를 reject한다.

## EXP171 dev-200 결과 (2026-09-09)

EXP171은 200/200 complete로 끝났다. parser error와 final recovery는 모두 0이었고,
CSV validation은 `passed: true`였다. macro positive-F1은 **0.307962**다. 이는 이 정책의
첫 complete dev-200 측정치이며, fast/independent holdout에서 보였던 source-first의 상승
방향과 모순되지 않는다. 다만 이 dev-200에는 아직 동일 decoder/output-cap의 one-stage
control이 없으므로, 기존 EXP120/123 같은 이질 historical run과의 차이를 source-first의
인과 효과라고 해석하지 않는다.

| cohort / policy | macro F1 | runtime | calls | total tokens | reported cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| EXP167 fast20, source-first | 0.286111 | 165.0 s | 47 | 659,207 | $0.0717 |
| EXP168 independent holdout20, source-first | 0.229167 | 129.3 s | 47 | 631,653 | $0.0694 |
| **EXP171 dev200, source-first** | **0.307962** | **1,501.6 s** | **435** | **6,083,261** | **$0.6562** |

EXP171은 inventory 216회와 final 219회다. notice당 각각 1/1회가 중앙값이고 최대 3/3회,
navigation excerpt는 notice당 중앙 14개(최대 28개)였다. 따라서 source-first의 효과를
더 검증할 가치는 생겼지만, full evaluation에는 대략 4천 호출 규모가 예상되므로 이
architecture는 아직 runtime-risk ablation이다. offline vLLM에서의 batch/throughput 검증과
one-stage dev200 capacity-matched control 없이는 submission default로 승격하지 않는다.

항목별 F1은 v2/v3/v21=1.000, v1=.769, v19=.667, v22=.667, v9=.556, v5=.500,
v8=.462, v12/v15=.286, v23=.200이고 나머지 다수 항목은 0이었다. 특히 v4, v6–v7,
v10–v11, v14, v16–v18, v20, v24의 FN 편향과 v13/v23의 FP가 병목이다. 즉 이 결과는
문서 사실 탐색이 일부 항목을 돕는 신호이지, 카드/항목별 판단 정책이 전반적으로
해결됐다는 증거는 아니다.

Evidence validation에는 11건의 warning이 있었다(e8/e9/e13/e15/e23/e24 positive 중
유효 원문 substring이 없는 경우). label/CSV 형식은 통과했지만 submission candidate에는
허용할 수 없는 evidence 품질이므로, 후속 비교에서는 이 warning을 별도 gate로 추적한다.
또한 OpenRouter가 12개 응답에서 configured 2,500보다 큰 completion usage(최대 4,211)를
보고했다. raw JSON은 모두 정상 `stop`으로 파싱됐지만 remote usage는 local vLLM cap/runtime
proxy가 아니다.

다음 최소 실험은 **동일한 32k admission, cards v6, metadata/product facts, 2,500 cap,
concurrency 4에서 stage 1만 제거한 one-stage dev200 control**이다. 이 control이 있어야
EXP171의 +/−를 source-first라는 단일 policy change로 판정할 수 있다. 그 전에는 prompt,
card, grouping 또는 evidence 규칙을 더 바꾸지 않는다.

## EXP172 one-stage dev-200 control: 유료 전 검토

`config.exp172-complete-source-2500-dev200-c4.yaml`은 EXP171을 base로 하며,
`staged_run.mode`만 `fact_inventory_full_final_v1`에서 unset으로 바꾼 대조군이다.
preflight는 바로 그 한 차이만 보고했다. exact final admission audit은 dev200의 source
374/374, required metadata 21/21, active card 24/24, over-budget 0을 확인했고, pack 수는
1회 186건·2회 12건·3회 2건으로 EXP171 final stage와 동일하다. semantic-input contract은
24/24 PASS였다.

사람 검토는 `outputs/exp172-prompt-review/pps-dev-01.messages.md`(짧은 공고),
`pps-dev-062.messages.md`(첨부), `pps-dev-169.messages.md`(첨부+overflow)에서 했다.
각 메시지에 human-readable metadata, 필요한 경쟁제품 설명, cards v6 및 해당 원문 packs가
있고 law/RAG 또는 internal status key는 없다. mock은 200/200 parser/CSV completion,
regression suite는 144 passed였다. 따라서 이 remote run은 EXP171의 유효한 one-variable
dev200 control이다.

## EXP172 dev-200 control 결과

EXP172는 200/200 complete, parser error 0, final recovery 0, CSV validation PASS로
완료했다. macro positive-F1은 **0.259281**이었다. EXP171 source-first/full-final의
0.307962보다 **-0.048681**이다. 두 run의 full-source packs는 거의 동일하다
(EXP171 final 219 calls, EXP172 216 calls). 따라서 이 차이는 4k/첨부 누락, card,
metadata, product fact, decoder, frozen rule 또는 concurrency가 아니라 stage-1
source-fact navigation 유무의 비교 결과다.

| policy | macro F1 | runtime | final calls | all calls | total tokens | validation warnings |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| EXP171 source-first/full-final | **0.307962** | 1,501.6 s | 219 | 435 | 6,083,261 | 11 |
| EXP172 one-stage control | 0.259281 | 686.5 s | 216 | 216 | 3,342,193 | 16 |

개선은 한 항목에만 모이지 않았다. source-first는 v1(+.154), v5(+.029), v8(+.176),
v9(+.056), v12(+.086), v15(+.286), v19(+.042), v22(+.205), v23(+.136)를 올렸고,
v4/v6/v7/v10/v11/v14/v16/v18/v20/v21은 동일했다. control보다 FP는 v4 4→1,
v5 6→2, v9 9→7, v12 3→0, v13 8→4, v17 4→0, v19 5→2, v22 5→1,
v23 25→13, v24 6→2로 넓게 줄었다. 반대로 v5/v19의 TP는 각 1개 줄고, v8은
TP 1→3과 FP 0→4라는 tradeoff가 있다. 즉 0.0487 상승은 희소 item 하나의 우연한
반전만으로 설명되지는 않지만, OpenRouter remote variance를 제거한 반복 측정도 아직 없다.

Evidence span F1은 EXP171 .4193, EXP172 .4209로 비슷하고, source-first의 evidence
warning은 11건으로 control의 16건보다 적지만 여전히 submission gate에는 부족하다.
EXP172의 completion usage는 모두 2,500 이하(최대 2,163)였고 EXP171은 12건이 상한을
넘어 최대 4,211로 보고됐다. 이는 raw JSON/validation과 별개인 remote provider cap
non-parity다.

결론: source-first/full-final은 complete-source branch의 현 incumbent로 승격한다.
다만 약 2.19배의 remote runtime/1.82배 tokens와 evidence warning을 감안해 submission
default는 아니다. 다음 후보는 source-first의 **source-complete final, non-final-only
stage 1, Python final-label 비개입**을 지키면서 fact navigation의 coverage/표현을 바꾸는
단일 ablation이어야 한다. 이미 실패한 full-split×group, raw-law RAG, dev-label item
postprocess, final source를 4k로 줄이는 방식은 다시 열지 않는다.
