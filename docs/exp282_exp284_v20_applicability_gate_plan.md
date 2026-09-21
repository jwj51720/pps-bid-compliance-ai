# EXP282–284 — v20 적용성 gate-first card

작성: 2026-09-15, dev / mac

## 진단

EXP281 corrected-card V-only는 dev200 v20의 양성 5건을 모두 회복했지만 `FP 66`, precision
`.0704`였다. 예측 양성 71건을 label과 무관한 source 특징으로 다시 감사하면 50건은 공고 전체에
`소프트웨어`, `SW사업`, `정보시스템`, `시스템 구축·운영`, `유지관리` 중 어느 넓은 표현도 없다.
실제 표본에는 식품 구매(DEV15), 행사·광고대행(DEV39/75/169/191), 학술연구
(DEV10/73/85/136/137/140/161/165), 폐기물 처리(DEV91/151/185/189) 등이 포함된다.

v19 card는 이미 `실제 SW 사업이 불명확하면 0`이라고 쓰지만, 적용성 판정·사업금액 산식·
20/40/80억원 ladder·예외·부재 판정을 한 긴 단락에 둔다. V-only에서 모델은 비-SW 공고의
SW 제한 문구 부재를 먼저 보고 1로 뒤집은 것으로 보인다. 이는 threshold 사실 누락이 아니라
absence 판정 전에 applicability gate를 실행하지 못한 관계 오류다.

## 가설과 최소 변경

v20 card만 gate-first 형식으로 바꾼다.

1. `GATE A`: 제목·사업목적·실제 납품/과업에서 SW 개발·구축·운영·유지관리, 소프트웨어
   설치·라이선스·자체 조달 등 실질 SW 대상이 명시되어야 한다. 전자입찰시스템 문구,
   정보보안 boilerplate, 전산 제출 안내, SW사업자 업종 등록만으로는 통과하지 않는다.
2. `GATE B`: 적용 사업금액과 법정 비적용 사유를 확인할 수 있어야 한다.
3. 어느 gate든 실패·불명이면 그 즉시 `v20=0`; 제한 문구의 부재 검사를 수행하지 않는다.
4. 두 gate를 통과한 뒤에만 기존과 같은 20/40/80억원 제한 ladder와 공고/RFP의 적용
   여부·근거 부재를 검사한다.

DEV132처럼 실제 과업에 업무용 소프트웨어 설치가 있는 공고는 업종 등록만이 아니라 실질 SW
구성요소가 있으므로 gate 검토 대상이다. Python은 위 표현을 검색하거나 label을 바꾸지 않는다.
모든 판단은 card, readable metadata와 모든 원문을 받은 Gemma가 한다.

## Controlled sequence

- EXP282 fast20: base EXP277 corrected-card V-only. 유일한 allowed policy change는
  `prompt.decision_cards_path`다.
- EXP283 holdout20: EXP282가 fast의 TP를 유지하면서 FP를 줄일 때만 policy-identical하게 실행한다.
- EXP284 dev200: EXP283도 유일한 positive를 유지하고 기존 EXP280보다 precision/F1을 개선할
  때만 실행한다.

기존 EXP277/280/281 결과를 frozen controls로 사용하며 재호출하지 않는다. 각 승격 단계에서
preflight, exact tokenizer admission, short/attachment/longest actual rendered review,
active-v20 semantic contract, exact mock과 output validation을 다시 기록한다. 결과는 v20
TP/FP/FN, tokens/runtime 및 EXP262 composition에 v20만 overlay한 macro로 판단한다.

## EXP282 pre-provider gate

- generated v20 artifact는 v19 artifact와 비교해 `v20.prompt_text`만 다르고 나머지 23개 card,
  item name과 absence flag는 같다. focused test와 full suite `243 passed`다.
- preflight는 선언한 `prompt.decision_cards_path` 한 차이만 검출했다.
- exact tokenizer dev200 audit는 200 records, 200 one-pass calls, 374/374 documents,
  omission 0, overflow 0이다. 최대 prompt는 DEV11 29,921/30,268 tokens다.
- actual rendered fast messages를 short DEV062, attachment DEV194, longest-class DEV169,
  positive DEV131에서 export하고 읽었다. 각 system에는 GATE A/B, 즉시 0 조건, 기존 threshold
  ladder와 예외가 있고, user에는 readable metadata와 존재하는 공고문·규격서·제안요청서
  원문 경계가 보존된다. raw metadata/internal code/raw law는 없다.
- active-v20 semantic-input contract는 네 fixture 모두 PASS다.
- exact fast mock은 20/20 rows, 49 columns, unique IDs, parse error 0, e20 blank,
  validation PASS다.

EXP282 fast provider run을 승인한다.

## EXP282 fast20 result

- v20: `TP 1 / FP 1 / FN 0`, precision `.5`, recall `1.0`, F1 `.666667`.
- frozen EXP277 control `1/6/0`, F1 `.2500` 대비 TP를 유지하면서 FP 5개를 제거했다.
- positive는 DEV131, 남은 FP는 DEV30이다. parse error 0, validation PASS.
- prompt/completion `256,695 / 180`; runtime 20.550초. 기존 V-only와 output 크기는 같다.

사전 승격 조건을 충족했으므로 policy-identical EXP283 holdout20을 승인한다.

## EXP283 holdout pre-provider gate

- preflight effective policy difference `{}`; same v20 gate-first V-only policy다.
- exact tokenizer full-dev audit는 EXP282와 동일하게 200/200 one-pass, 374/374 documents,
  omission/overflow 0, 최대 29,921/30,268 tokens다.
- holdout exact mock은 20/20 rows, 49 columns, unique IDs, parse error 0, e20 blank,
  validation PASS다.
- short DEV094, attachment/positive DEV132, longest DEV27의 rendered system/user message를
  읽었고 gate card, readable metadata와 모든 원문이 보존된다. active-v20 semantic contract는
  세 fixture 모두 PASS다. 이 policy에는 실제 overflow record가 없다.

EXP283 holdout provider run을 승인한다.

## EXP283 holdout result — rejected

- v20: `TP 0 / FP 0 / FN 1`, precision/recall/F1 `0/0/0`.
- frozen EXP280 control은 `1/5/0`, F1 `.285714`였다.
- gate-first card는 모든 FP를 제거했지만 유일한 positive DEV132도 0으로 만들었다. DEV132는
  전산기기 임차가 주 제목이고 업무용 소프트웨어 설치가 실제 과업 일부인 복합 조달이다.
  따라서 source-grounded applicability를 단순히 더 엄격하게 서술하면 이런 경계 사례의 recall을
  잃는다.
- prompt/completion `252,439 / 180`; runtime 21.023초. parse error 0, validation PASS.

fast에서의 precision 개선이 independent sensitivity로 일반화되지 않았으므로 EXP284 dev200은
실행하지 않는다. v20 gate-first v20 artifact는 rejected diagnostic이며 canonical로 승격하지 않는다.
현재 v20 최고 증거는 EXP281 corrected-card V-only의 dev200 F1 `.131579` 및 composition macro
`.359257`이지만, FP 66과 추가 200 calls 때문에 submission policy로도 아직 승격하지 않는다.

## 방법론 결론

1. v20에서는 동일 입력의 V-only가 V/E보다 fast와 holdout 모두 좋았고 dev200 양성 5건을 전부
   회복했다. V-only가 실제 판정 성능을 개선할 수 있다는 가설은 처음으로 재현됐다.
2. 그러나 강한 applicability 문구는 fast specificity와 holdout sensitivity를 맞바꿨다. 카드가
   법률상 맞는 문장을 포함하는 것과 복합 조달의 적용성을 안정적으로 분류하는 것은 다르다.
3. 같은 card를 반복 호출하거나 더 강한 문구로 조이는 대신, 다음에는 v8/v19처럼 실제 source
   역할 관계가 분명하고 evidence-bearing인 항목을 감사한다. v20을 다시 다룬다면 단일 최종
   label 앞에 source-only `주 조달대상/실질 SW 구성요소/boilerplate` 사실을 분리하는 작은
   relational pass가 필요하다. 이는 새 schema를 여러 v로 일반화하지 않고 v20 한 항목에서만
   검증해야 한다.
