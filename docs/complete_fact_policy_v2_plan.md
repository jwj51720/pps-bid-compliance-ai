# Complete-fact input policy v2 계획

작성일: 2026-09-09 (dev / mac)

## 문제 정의

공고의 판정 실패는 모델의 법률 지식 부족만으로 설명할 수 없다. 적용계약법, 금액,
계약·낙찰 방법, 제품 분류, 문서 사이의 실제 제한 문구처럼 **판정 전제인 사실**이
prompt 밖에 있으면, 어떤 모델도 올바른 0/1을 낼 수 없다. 특히 첨부문서에만 있는
제한·예외·필수문구를 ordered 4,000-character 앞부분이 누락할 수 있다.

그러므로 신규 후보는 4,000자를 문서 선택 휴리스틱으로 쓰지 않는다. 4k는 역사적
control/비교군으로만 남긴다.

## 완결 입력 계약

카드는 법령 원문 RAG가 아니라, organizer 제공 항목표·법령·고시를 offline 검토해 만든
item별 적용 전제·1 조건·중요 0 조건/예외의 압축본이다. actual fact는 다음 다섯 입력에서
빠짐없이 접근 가능해야 한다.

1. **판정 원칙과 V/E 출력 계약** — legal-compliance 역할, 불확실한 전제를 1로 단정하지
   않는 원칙, unchanged source evidence 규칙.
2. **활성 v의 decision card** — 카드 파일의 version/hash를 config에 고정한다.
3. **사람이 읽는 organizer metadata** — 적용계약법·업무구분·계약/낙찰방법·금액·지역·
   업종·공동계약·날짜·정보화 여부 등 item contract가 요구하는 field/value를 제공한다.
   raw JSON, 내부 status, code array는 노출하지 않는다.
4. **organizer CSV exact product fact** — v10–v18에는 `competition_products_v1` exact-code
   lookup을 친화적 한국어 applicability text로 제공한다. 이 fact는 applicability이며
   evidence는 아니다.
5. **actual notice source** — 공고문, 규격서, 과업지시서, 제안요청서, 예외공표서를
   organizer 순서대로 제공한다. source가 존재하면 조용히 버리지 않는다.

`docs/semantic_input_contract_v1.md`의 24개 row가 이 다섯 요소의 source/provenance와
rendered span을 검증하는 admission 기준이다. source scope는 좁은 근거가 생기기 전까지
모든 제공 문서다.

## 32k admission policy

대회 모델의 허용 길이는 32,768 tokens다. V/E output reserve 1,536을 뺀 prompt budget은
31,232 tokens다. 후보에서는 `max_document_chars: null`, `max_model_len: 32768`,
`overflow_split_enabled: true`를 함께 쓴다.

- 모든 다섯 source와 fixed prompt가 budget 안에 들면 한 번의 full-source call을 한다.
- 넘는 경우에만 exact Gemma chat-template tokenizer로 organizer 순서의 complete packs를
  만든다. 각 source document는 가능한 한 온전하게 유지하며, source 하나가 pack budget을
  넘을 때만 그 source의 연속 fragment를 만든다.
- non-absence item은 pack 중 어느 하나의 valid positive가 있으면 OR로 결합한다. absence
  v10/v11/v16/v18/v20은 모든 complete pack에서 필수 조건이 관찰되지 않았을 때만 1이 되는
  AND를 쓴다.

이는 full-split × item grouping이 아니다. 24-item final task는 한 full-source call 또는
overflow packs에 한 번씩만 실행된다. call 수는 exact admission 결과로 기록한다.

## EXP154: 먼저 검증할 최소 ablation

EXP154는 실패한 EXP152의 full-source complete-fact policy에서 **모델 context admission만
16k → 32k로 바꾼** diagnostic이다. card, metadata rendering, CSV fact, V/E schema,
merge, frozen v2/v3/v21 rule, decoder, model, temperature는 바꾸지 않는다. 따라서
EXP152보다 pack fragmentation이 얼마나 줄고, 그 변화가 quality/runtime에 미치는지만
검증한다.

유료 fast20 전 gate:

1. exact tokenizer로 dev-200 및 fast20 context/call distribution을 산출한다.
2. short complete, attachment, prior-overflow notice의 exact rendered input을 export하여
   사람이 읽고, card·metadata·CSV·모든 supplied source가 실제 span에 있는지 확인한다.
3. `audit_candidate_semantic_contract.py`, preflight, mock, parser/evidence regression을
   통과한다.
4. 32k admission이 EXP152보다 pack 수를 실질적으로 줄였는지 먼저 확인한다. 줄지 않으면
   paid run을 하지 않고 output reserve/prompt burden을 별도 진단한다.

## 알려진 위험과 해석 규칙

EXP152는 16k complete-source one-stage가 fast20 0.224306으로 EXP147 4k control
0.291071보다 낮았다. EXP153은 source inventory를 추가해 0.280556까지 회복했으나 gold
positive evidence coverage가 6/38(15.8%)여서 확장하지 않는다. 따라서 EXP154가
complete input의 품질을 자동으로 보장한다고 주장하지 않는다.

반대로 EXP154가 낮더라도, 그것은 “필요한 사실을 다시 빼자”는 결론이 아니다. full source
reading과 24개 동시 final judgment의 인지 부담을 분리할 후속 architecture가 필요하다는
증거다. 다음 architecture는 source coverage를 labels 없이 먼저 검증하고, 4k front-cut을
다시 기본값으로 되돌리지 않는다.

## EXP154 fast-20 결과

사전 gate를 통과한 뒤 EXP154을 실행했다. macro positive-F1은 `0.241667`으로 EXP152
16k `0.224306`보다 `+0.017361` 개선됐지만 EXP147 4k single `0.291071`보다
`-0.049405`다. 실제 fast20 call 수는 22회, runtime은 40.5초, parse error는 0이다.
자세한 admission과 per-v 오류는 `docs/exp154_complete_fact_32k_fast_result.md`에 있다.

따라서 32k admission은 확실히 채택할 만한 **source-completeness mechanism**이다. 그러나
EXP154 one-stage 24-item V/E는 quality gate를 통과하지 못했으므로 canonical submission
policy로 승격하지 않는다. 4k는 성능 비교 control로는 보존하되, 앞으로 모든 사실이
들어간다고 주장하는 candidate의 document-selection heuristic으로는 사용하지 않는다.

## complete-source item partition 탐색

EXP155는 EXP154의 source-complete 32k admission을 유지하고, 기존에 provenance로
고정된 `document_restrictions_two_way_v1` 19+5 partition만 적용했다. 모든 group은 같은
카드·friendly metadata·CSV fact·complete source·frozen v2/v3/v21 rule을 유지한다.
fast20은 42 calls, 599,696 tokens, F1 `0.237500`이었다. EXP154 `0.241667`보다 낮아
19+5 partition은 확대하지 않는다. v8/v12/v19 일부 FN은 회복했지만 v8/v17/v19/v23 FP가
늘었다. 이는 문서제한 5개를 따로 떼는 것만으로는 완결입력 one-stage의 판단 과부하를
풀지 못했다는 결과다.

다음 EXP156은 dev 오류 기반 재조정이 아니라, item truth-condition family에 따른 다른
두-way partition을 비교한다. G01은 qualification/document/procedure/consistency
(v1–v9, v19, v21–v24), G02는 exact-product 및 whole-notice absence (v10–v18, v20)다.
두 group 모두 32k complete-source admission을 독립적으로 수행하므로 runtime-risk
diagnostic이다. EXP155와 동일한 preflight, semantic contract group audit, exact rendered
input review, mock gate를 통과한 뒤 fast20만 실행한다.

### EXP156 결과와 분기 종료

EXP156은 모든 gate를 통과했지만 fast20 `0.213889`, 40 calls, 45.67초였다. EXP154
one-stage `0.241667`보다 `-0.027778`이다. EXP155 19+5도 `0.237500`으로 낮았으므로,
두 가지 independent two-way grouping hypothesis는 현재 종료한다. 결과·runtime·per-v
해석은 `docs/exp155_exp156_complete_source_group_results.md`에 남긴다.

## EXP157: source fact inventory → final

EXP153의 실패는 complete source 자체가 아니라 한 pack에서 `v1`–`v24` 각각에
excerpt/null을 요구한 output burden과 15.8% gold-evidence coverage였다. EXP157은
source admission을 32k로 유지하되 1차 output을 v가 아닌 일곱 factual category로 바꾼다.
각 category는 최대 세 개의 짧은 unchanged source excerpt만 갖고, 위반/무위반·법령
해석·예외 적용을 내리지 않는다. 2차는 card v6, readable metadata, exact product fact,
4k original orientation context, source-labelled factual inventory로 독립 V/E를 낸다.

2차의 4k는 source selection policy가 아니다. 모든 source는 1차 exact token pack에서
읽히며, 4k는 final reader가 공고의 서술 흐름을 파악하는 보조 anchor다. stage1 output
capacity 때문에 output reserve/max tokens를 2,500으로 함께 올린다. 유료 실행 전 stage별
exact rendered message, source-category parse/substring validation, semantic input audit,
mock, post-run source coverage를 각각 검증한다.

### EXP157/158 결과

EXP157 fast20은 `0.286111`로 complete-source branch 중 최고였고 post-run source coverage도
31.6%(12/38)로 EXP153의 15.8%보다 높았다. 그러나 policy를 바꾸지 않은 independent
holdout EXP158은 `0.187500`(70.9초)이었다. 따라서 source-category representation의 fast
결과는 일반화 근거가 아니며 dev-200/submission으로 확대하지 않는다. 앞으로 이 branch의
다음 후보는 fast score만 보고 category나 phrase를 추가하지 않고, holdout의 coverage/FP/FN
차이를 먼저 label-blind source composition과 output-capacity 관점에서 진단해야 한다.
