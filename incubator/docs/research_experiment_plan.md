# 독립 연구 실험계획서 v1

## 목적

목표는 dev-200의 단발성 Macro F1이 아니라, 제공 Gemma와 공식 자료만 사용해 test 1,853건을 두 시간 안에 재현 가능하게 처리할 항목별 법적 적용성 판단 정책을 찾는 것이다.

- 한 실험은 한 개의 인과 가설만 바꾼다. prompt, context, retrieval, merge, correction을 동시에 바꾸지 않는다.
- 작은 cohort는 진단용이고 dev-200은 확증용이다. 작은 cohort 승자는 제출 정책이 아니다.
- 규칙은 fact extraction과 call scheduling으로 시작한다. 모든 final notice에는 actual-notice Gemma call이 한 번 이상 있어야 한다.
- source evidence와 비용·token·runtime은 F1과 동등한 release gate다.

| 결과 | 정의 | 다음 행동 |
|---|---|---|
| 성공 | 사전 등록 safety gate와 효과 크기 gate를 통과하고 hard negative 퇴행이 없다. | frozen policy로 dev-200 confirmation. |
| 부분성공 | coverage·근거·비용은 좋지만 F1 이득이 부족하거나 P/R trade-off가 불명확하다. | 원인 하나만 바꾼 repair pilot 1회. |
| 실패 | target positive 누락, FP 증가, schema/runtime/cost failure, 불공정 비교다. | policy 폐기; error ledger를 남기고 다른 branch로 이동. |

## 출발 기준과 질문

재현 가능한 역사적 기준은 EXP-001 공동 24항목 4,000자 prompt의 dev Macro F1 `0.220416`이다. 기록상 full context는 `0.213825`, 큰 v1 법령 bundle은 `0.167873`, strict split/card v1은 `0.17417`, card v2/product context는 `0.22802`였다. 마지막 두 full-dev artifact는 이 WSL에 없으므로 historical reference이지 재현 비교군이 아니다.

```text
Q1 24개 법률 문제를 한 번의 공동 출력에 넣는 것이 주된 오류 원인인가?
Q2 exact product/price/metadata fact + active-item prompt가 v10--v18을 개선하는가?
Q3 typed document-to-metadata reconciliation이 v24를 개선하는가?
Q4 document-local window와 item-aware merge가 local/absence 항목 FP를 줄이는가?
Q5 lexical retrieval을 BGE-M3 hybrid으로 확장할 실증적 가치가 있는가?
Q6 적용성 계층이 안정된 뒤 self-labeled case retrieval이 일반화에 기여하는가?
```

## 공통 실험 계약

- 입력은 `../data/raw/open/`만 읽는다. 모든 run은 source-file hash, record-ID hash, code revision을 기록한다.
- judgment는 `google/gemma-4-26b-a4b-it`, temperature 0, fixed seed, fixed JSON schema로 시작한다.
- paired comparison은 같은 notice/document order, output schema, evidence validator를 사용한다.
- final message SHA-256, exact token count, model/route/settings, raw response, provider usage를 저장한다.
- raw prompt/response는 untracked `runs/`에만 저장한다. tracked 문서는 raw notice, notice ID, API key를 포함하지 않는다.

| 축 | 필수 기록 |
|---|---|
| 판단 | item별 TP/FP/FN, P/R/F1, prediction-positive count, macro positive-F1 |
| 근거 | non-absence substring validity, span overlap, doc type, source offset |
| retrieval | gold fact/evidence coverage, chunks/windows 수, selected token count |
| 실행 | request success, parse failure, retry, input/output tokens, cost, wall time |
| 안정성 | changed-cell ledger, notice bootstrap 10,000회, fixed cohort hash |

dev-200 bootstrap은 test 분포를 보장하지 않는다. 한두 notice의 우연한 변화가 정책 선택을 지배하지 않게 하는 보조 지표다.

| 단계 | requests 상한 | OpenRouter 상한 | 즉시 중단 |
|---|---:|---:|---|
| offline/mock | 0 | $0 | schema, token admission, coverage failure |
| paired pilot | 64 | $0.50 | request/cost ceiling 또는 parse failure >5% |
| repair pilot | 32 | $0.25 | 동일 |
| dev-200 confirmation | profiling 후 승인 | $1.50 | failure >2%, runtime/cost projection 초과 |
| BGE-M3 ranking ablation | 200 embeddings | $0.25 | lexical 대비 recall 이득 없음 |

## 의사결정 트리

```text
F0--F3 no-API foundation
  ├─ 실패 → foundation만 고친 뒤 재검증
  └─ 통과 → E1 product/price paired pilot (v10--v18)
               ├─ 성공 → E2 dev-200 confirmation → E9 scheduler 후보
               ├─ 부분성공 → E1R 단일원인 repair → 성공이면 E2, 그 외는 branch 동결
               └─ 실패 → judgment policy 폐기, fact layer만 보존

독립 branch: E3 v24 → E4 v1--v9 → E5 v19--v23
검증된 branch가 하나 이상 생긴 뒤: E6 lexical/BM25 → E7 BGE-M3 → E8 case RAG
검증된 branch 조합: E9 full-system confirmation → parent integration proposal
```

final merge, candidate suppression, legal bundle를 바꾸는 정책은 dev-200 confirmation 전에는 다른 branch의 comparator 또는 제출 후보가 될 수 없다.

## F0--F3: API 호출 전 기반 실험

### F0. Source, schema, historical-artifact audit

**가설:** 동일 입력과 출력 계약을 재현하지 못하면 이후 비교는 무의미하다.

- 원본 JSONL, labels, item table, official law package의 SHA manifest를 작성한다.
- historical config/output/prompt hash 존재 여부를 조사한다. local artifact 없는 EXP-013/014는 재현 불가로 표시한다.
- official 10-notice fixture에서 mock input/output, 49-column, evidence validation을 검사한다.

| 성공 | 부분성공 | 실패 |
|---|---|---|
| source/schema/validator/provenance가 모두 명확 | historical output 일부 누락; 누락 run은 comparator 금지 | raw source 또는 schema 불명확; API 실행 중지 후 path/manifest 수정 |

### F1. Dev error atlas와 cohort compiler

**가설:** gold evidence와 metadata strata를 명시하면 random first-20보다 적은 표본으로도 가설을 반증할 수 있다.

- 각 positive를 `item × evidence-doc-type × contract-law × product-state × price-bucket × completeness`로 분류한다.
- 각 target item에 같은 cue/fact의 hard negative와 no-cue negative를 붙인다.
- cohort는 ID 나열이 아닌 versioned selection rule, seed, resulting-ID SHA로 고정한다.

| 성공 | 부분성공 | 실패 |
|---|---|---|
| item별 positive/hard-negative cohort spec 존재 | 희귀 item의 matched negative 부족; diagnostic 표시 | evidence/fact extractor가 positive를 놓침; LLM 없이 수정 |

### F2. Deterministic fact와 source-window audit

**가설:** code, amount, date, ratio, restriction, provenance를 먼저 정규화하면 prompt가 작아지고 법적 적용성의 모호성이 줄어든다.

- 모든 fact는 raw text span, `doc_id`, normalization rule, deterministic parsing state를 가진다.
- product code는 official CSV exact match만 사용하며 `matched`, `not_matched`, `unknown`을 합치지 않는다.
- window는 full document offset을 보존하고 final evidence는 항상 원문 전체에서 재검증한다.

| 성공 | 부분성공 | 실패 |
|---|---|---|
| target cohort gold fact/evidence coverage 100%, attribution error 0 | coverage 100%이나 windows 과다; ranking만 개선 | coverage <100% 또는 offset 오류; prompt pilot 금지 |

### F3. Official-law manifest와 token admission

**가설:** 작은 완결 조문 bundle은 broad law context의 혼선을 피하고 필요한 예외까지 제공한다.

- article/section/appendix/table마다 source SHA, heading boundary, chunk SHA, linked items, token count를 남긴다.
- 불명확 selector, 긴 예규 heading, 표 header/각주는 원문 해결 전 retrieval 후보가 아니다.
- active-item prompt + metadata + window + legal chunk의 final chat token으로 admission한다.

| 성공 | 부분성공 | 실패 |
|---|---|---|
| 모든 target input이 budget 내, 조건/예외가 완결 | 일부 group overflow; window 축소, legal chunk 임의 split 금지 | fixed context 자체 overflow; law 없이 pilot 또는 selector 재설계 |

## E1: 첫 유료 실험 — v10--v18 product/price active-item pilot

**우선순위:** 이 group은 baseline 오류가 집중되고 exact code·금액·계약법·presence라는 강한 organizer-data fact가 있다.

**가설:** 9개 항목만 출력하게 하고 product exact-match state, price bucket, relevant official-law chunk, source-local window를 주면 joint 24-item prompt보다 FP를 줄이고 target recall을 유지한다.

**고정 cohort:** F1 selection rule로 만든 24--32 notices. 가능한 모든 target positives와 `matched/not_matched/unknown` 및 price bucket별 hard negative를 포함한다. incomplete notice도 absence-item 검증용으로 포함한다.

**동시 비교:** 같은 cohort와 settings에서 notice당 두 호출을 실행한다.

- `C1`: active v10--v18만 출력. product/price fact·legal chunk 없는 concise control이다.
- `T1`: C1 skeleton에 F2 facts, F3 legal chunk, source window, absence coverage contract만 추가한다.

32 notices면 최대 64 requests다. 출력 dimension을 C1/T1에서 맞추므로 T1 이득을 “9개만 출력했기 때문”이라고 오인하지 않는다.

| E1 gate | 성공 기준 |
|---|---|
| transport | C1/T1 parse success >=95%, budget ceiling 이내 |
| evidence | non-absence positive validity 100% |
| effect | T1 target macro F1이 C1보다 +0.05 이상, target recall non-decrease |
| error balance | changed cells net correct >= +3, 같은 fact-stratum hard negative 새 FP <=1 |
| absence safety | incomplete notice를 미관측만으로 positive 처리하지 않음 |

- **성공:** T1 implementation/selector/prompt를 freeze하고 E2로 간다.
- **부분성공:** coverage·evidence는 통과했으나 effect gate 미달일 때만 E1R을 한다. error ledger에서 `legal exception`, `presence definition`, `window ranking`, `prompt interpretation` 중 하나만 주원인으로 선택한다.
- **실패:** recall 감소, strata-independent FP 증가, source fact 오류, overflow면 T1 judgment policy를 폐기한다. facts는 E3/E4에 재사용 가능하나 동일 policy는 재시도하지 않는다.

### E1R. Repair는 한 번만

E1 부분성공일 때 legal chunk, absence contract, window selector, instruction 중 하나만 바꾼다. cohort/model은 같고 treatment는 32 requests 이하이다.

- 성공: E1의 모든 gate 충족 → E2.
- 부분성공 또는 실패: 추가 prompt fishing 금지. product branch는 best safe control로 동결하고 E3/E4로 이동.

### E2. Product/price dev-200 confirmation

E1 개선이 chosen cohort overfit인지 검증한다. C1/T1을 frozen code/settings로 dev-200에 적용한다. overall Macro F1 +0.015 이상 또는 v10--v18 macro F1 +0.05 이상이어야 하며, isolated branch이므로 v1--v9/v19--v24를 바꾸지 않는다. 10,000 notice bootstrap delta의 90% lower bound >=0 및 evidence/schema/runtime guardrail 통과가 필요하다.

| 결과 | 조치 |
|---|---|
| 성공 | validated candidate로 고정하고 E9 scheduler 후보로 승격 |
| 부분성공 | target gain은 있으나 overall 불확실; optional branch로 보관하고 default를 바꾸지 않음 |
| 실패 | recall collapse 또는 gate 미달; policy 폐기, fact extractor만 보존 |

## E3--E5: 독립 task-shape branch

### E3. v24 typed reconciliation

**가설:** 금액·계약방법·지역·업종을 typed pair로 렌더하고 source window를 Gemma에 주면 실제 불일치를 joint prompt보다 잘 구분한다.

v24 positives 전체와 같은 field type negatives로 최대 24-notice paired cohort를 만든다. money field는 `예산`, `추정가격`, `기초금액`, `부가세` identity를 보존하며 교차 비교하지 않는다.

- 성공: v24 F1 +0.10, new FP <=1, evidence validity 100% → dev-200.
- 부분성공: candidate recall 100%이나 normalization이 모호 → pair renderer 하나만 repair 1회.
- 실패: VAT/rounding/field ambiguity 지배 → automatic positive rule 금지, triage candidate로만 보존.

### E4. v1--v9 document-local groups

**가설:** qualification/performance/region/model cue window와 active items만 출력하면 24-item confusion이 줄어든다.

`v1,v4`, `v2,v3`, `v5--v9` subgroup을 차례로 20--30 notice paired pilot한다. document-local positive에는 target-document evidence를 의무화한다.

- 성공: subgroup target macro +0.05, recall non-decrease, new hard-negative FP <=1 → subgroup dev-200.
- 부분성공: evidence는 향상, F1 동일 → selector만 1회 repair.
- 실패: recall loss → full-notice triage context 단일 ablation; 재실패하면 group-call 접근 폐기.

### E5. v19--v23 procedure items

확약서 제출 시점, 공동계약 지분율, SW 금액 구간, 협상/지방계약 적용성, 날짜 간 기간을 facts로 만들고 item별 small call 또는 동일 legal mechanism pair만 묶는다.

- 성공: item별 positive/hard-negative cohort에서 F1 개선 → item별 dev-200.
- 부분성공: date/ratio parser만 검증 → extractor 보존, judgment 보류.
- 실패: sparse dev wording만으로 final rule을 만들지 않고 E8 이전까지 보류.

## E6--E8: retrieval과 case RAG

### E6. Lexical/BM25 retrieval

E1/E3/E4 중 하나가 legal/window context의 가치를 보인 뒤 시작한다. exact item selector와 metadata filter를 baseline으로 두고 BM25가 추가 선택한 chunk/window의 gold fact/evidence coverage를 API 없이 평가한다.

- 성공: frozen dev query set retrieval recall +5pp, token budget 준수 → small Gemma paired pilot.
- 부분성공: recall 동일, token 감소 → scheduler optimization 후보로 보관.
- 실패: exact selector보다 나쁨 → BGE로 이동하지 않고 query/chunk design 수정.

### E7. BGE-M3 hybrid retrieval

E6 성공 뒤에만 OpenRouter `baai/bge-m3`를 development ranking ablation에 쓴다. final design은 `PPS_EMBED_DIR` offline BGE-M3로 재현되어야 한다. rank fusion은 exact code/number/legal-citation filter 뒤에서만 작동한다.

- 성공: E6 대비 gold recall +5pp 또는 같은 recall에서 median selected token -20%, exact fact gate 무침범 → Gemma pilot 결합.
- 부분성공: semantic variant는 찾지만 exact legal chunk를 밀어냄 → BGE를 supplemental window source로 제한.
- 실패: recall/token/runtime 이득 없음 → BGE를 final 시스템에서 제외.

### E8. Stratified self-label과 case RAG

E1--E7 중 최소 두 branch가 validated candidate가 된 뒤에만 한다. train 20,000 전체가 아니라 likely positive, matched hard negative, ambiguous, rare-layout strata만 sample한다. record마다 source ID/hash, selected facts/chunks, prompt hash, model/settings, raw output, validation, timestamp를 남긴다. dev gold는 validation에만 사용하며 train label prompt answer로 넣지 않는다.

- 성공: frozen dev-200에서 no-case policy보다 target F1 +0.03, runtime budget 통과.
- 부분성공: hard-negative discrimination만 개선 → same-regime filter 강화 repair 1회.
- 실패: superficial cue copying, label noise, token explosion → corpus를 final inference에서 제거.

## 별도 출력·근거 아키텍처 branch

분류 F1과 근거 생성은 같은 어려움이 아니다. INC-001처럼 joint output에서 근거 validity가
낮거나 completion이 커지면, 아래 방향을 **동일한 judgment policy와 cohort에서 하나씩**
비교한다. 근거가 1차 리더보드 점수에 직접 들어가지 않더라도 2차 평가와 audit를 위해
substring validity는 release gate로 유지한다.

| 실험 | 바꾸는 한 가지 | 성공 신호 | 실패 시 해석 |
|---|---|---|---|
| O1 judgment-only | Gemma가 v만 출력하고 Python이 evidence를 만들지 않는다. | v F1/parse/cost의 순수 기준선 확보 | evidence 결합이 아니라 판단 자체가 문제 |
| O2 v→e selective | v=1인 non-absence item에만 두 번째 evidence call을 한다. | v 유지, evidence validity 상승, 제한된 call 증가 | second call이 source attribution을 해결 못함 |
| O3 e→v candidate | 먼저 item별 source window/evidence 후보를 찾고, 그 후보가 있을 때만 violation adjudication한다. | FP 감소와 source-local evidence 향상 | evidence 부재가 violation 부재가 아님; recall 위험 |
| O4 dual independent | judgment call과 evidence retrieval/call을 독립 실행하고 merge한다. | disagreement taxonomy가 명확해짐 | 단일 prompt보다 비용만 증가 |
| O5 mechanical evidence | 문장/표 행/문단을 원문 offset으로 분절하고, LLM 후보를 exact match·whitespace match·lexical/BGE similarity로 원문 span에 정렬한다. | validity 100%, span overlap 상승 | 모델 판단 오류는 해결하지 못함 |
| O6 evidence-constrained | active-item prompt에서 먼저 exact source quote를 선택하게 하고 그 quote에 근거해 v를 결정한다. | document-local FP 감소 | absence/v24/cross-document item에는 부적합 |

O3/O6는 v10, v11, v16, v18, v20의 absence items와 v24에 그대로 적용하지 않는다. 해당
항목들은 quote가 없는 것이 정상일 수 있으므로, full document coverage와 typed facts를 별도
입력으로 가진 judgment contract가 필요하다.

## E9: 전체 시스템과 integration gate

E9는 새 성능 탐색이 아니라 validated branch 조합의 시스템 시험이다. baseline triage → product → v24 → document/procedure → retrieval/cases 순으로 하나씩만 추가한다.

- notice당 Gemma calls 평균/p95/worst-case, 1,853건 총 calls/tokens, 64-way vLLM batch projection을 기록한다.
- every-notice actual-content Gemma call, missing docs, malformed retry/all-negative fallback을 검사한다.
- exact tokenizer admission, two-hour projection, source evidence, 49 columns, UTF-8/NFC validation을 통과해야 한다.

| 결과 | 조치 |
|---|---|
| 성공 | frozen dev-200 comparator보다 낫고 runtime/asset 제약 통과 → parent shared-pipeline integration proposal |
| 부분성공 | 성능은 좋으나 worst-case runtime 초과 → scheduler/early-stop만 별도 ablate |
| 실패 | 조합 해체, 최고 validated subset으로 복귀; incubator에서 직접 제출 금지 |

## 매 run의 decision record

`decision.md`는 다음에 답한다: 바꾼 단 하나의 policy와 comparator, cohort가 가설을 반증할 수 있었는지, target/non-target TP·FP·FN 변화, source/fact/retrieval/prompt/merge 중 주원인, 비용·token·runtime 외삽 가능성, 성공/부분성공/실패와 다음에 허용되는 단 하나의 행동.

이 기록이 없으면 그 run은 아이디어 탐색일 뿐 연구 증거나 병합 근거가 아니다.
