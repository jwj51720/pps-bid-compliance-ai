# 입력·판정·실행 전수 감사와 일반화 결론

작성: 2026-09-18, dev / mac

## 목적

개별 v 문구를 한 건씩 고치는 방식이 아니라, 낮은 성능이 생길 수 있는 전체 경로를 다음 층으로
분해해 다시 검사했다.

1. organizer JSONL과 label의 grain, ID, schema, 결측, 중복, evidence 무결성.
2. 모든 제공 문서가 exact tokenizer admission 뒤 final prompt까지 도달하는지.
3. 24개 항목의 적용 전제, 1 조건, 핵심 0 조건/예외, metadata/제품 사실이 실제 rendered
   message에 존재하는지.
4. 카드가 organizer 항목표·법령·CSV와 일치하는지.
5. model raw V가 parse, evidence gate, merge, postprocess에서 손실되는지.
6. V/E, V-only, 반복 V-only, 카드 재배치가 독립 cohort에서 일반화하는지.
7. 루트 config, local runner, submission runner, admission profiler가 같은 실행 topology를
   의미하는지.

이 문서는 입력이 완전하다는 주장과 모델 성능이 좋다는 주장을 분리한다. PASS는 해당 층의
무결성만 의미한다.

## 최종 판정 요약

| 층 | 판정 | 근거와 남은 위험 |
| --- | --- | --- |
| raw record/label join | PASS | dev 200/200 unique ID, label 200행·49열, exact ID join, binary V 오류 0 |
| 제공 문서 본문 | PASS | dev 374문서, empty/NFC/doc-id 중복 0; exact duplicate 본문 0 |
| upstream 완전관측 | 제한 | dev 10건(5%)의 제안요청서 10개가 organizer 조립 전에 이미 미제공 |
| 문서 유형/순서 | 제한 | raw 순서 불일치 dev 10건은 pipeline이 canonical order로 정렬. PPS-DEV-178의 D0는 내용상 설계서인데 `공고문`으로 표기된 semantic type anomaly |
| final source admission | PASS | v30/v31 기준 200 notices, 374 supplied docs, 243 contexts, pipeline omission 0 |
| final 실제 값 delivery | PASS | 200/200 notices 및 243/243 contexts에서 card·필요 metadata actual value·condition-aware product fact 존재 |
| 24-item semantic contract | PASS(검사 fixture) | short/attachment/overflow 5 fixtures의 모든 실제 context에서 v1–v24 PASS |
| 카드 source concordance | 대부분 보수, 1개 충돌 | v30에서 7개 확정 결함과 2개 충돌을 보수; v4는 v31에서 해소, v3 등호 경계는 organizer source 충돌로 잔존 |
| 최신 완결 카드의 canonical 선택 | **FAIL** | v30/v31은 실험 artifact/config에서 검증됐지만 root/submission은 여전히 과거 v10 base + v11/v12 specialists를 선택 |
| raw V→final label 보존 | 주 병목 아님 | 비교 가능한 EXP208/209 응답에서 raw→model label 변화 0; clean record FP/FN이 압도적 |
| V-only 일반화 | 기각 | fast의 미세 우위가 holdout에서 반전; single V-only도 V/E보다 낮음 |
| 카드 recency | 기각 | exact card recap은 fast F1과 runtime 모두 악화 |
| canonical 실행 재현성 | **FAIL/차단** | root는 619-call specialist composition이지만 local runner는 specialist를 실행하지 않았음; 이제 base-only surrogate 실행을 fail-fast 처리 |
| evaluator runtime | FAIL | 619-call EXP231 및 이전 435-call EXP171 제출이 120분 초과. batch 128은 call 수를 줄이지 않음 |

## 1. 데이터 품질 전수 결과

`scripts/audit_input_data_quality.py`와 config-aware `scripts/profile_data.py`를 다시 실행했다.

| split | records / unique IDs | supplied docs | empty/NFC/doc-id duplicate | upstream missing notices | raw order mismatch |
| --- | ---: | ---: | ---: | ---: | ---: |
| dev | 200 / 200 | 374 | 0 / 0 / 0 | 10 (5.0%) | 10 |
| train_unlabeled | 20,000 / 20,000 | 38,862 | 0 / 0 / 0 | 853 (4.265%) | 671 |
| local test sample | 10 / 10 | 23 | 0 / 0 / 0 | 0 | 0 |

dev의 문서 유형은 공고문 201, 규격서 63, 과업지시서 53, 제안요청서 57이다. 200 notices보다
공고문이 하나 많은 이유는 PPS-DEV-178에 `공고문` 두 개가 있기 때문이다. D1은 실제 입찰공고이고,
D0는 본문 시작과 목차가 설계서/시방서인 문서다. 본문 자체는 전달되므로 source omission은
아니지만, model에게 표시하는 문서 유형은 잘못되었을 가능성이 높다. 이 한 건을 근거로 Python
문서 재분류 규칙을 만들지 않는다. public에도 같은 현상이 있는지 organizer 원본 provenance로
확인할 수 있을 때만 일반 정책을 정한다.

dev metadata의 높은 null rate는 `공동도급구성방식 79.5%`, `긴급공고여부 69%`,
`세부품명번호목록 61%`, `낙찰하한율 57%`, `제한지역코드목록 56.5%`다. 이들은 조건부 필드라서
null 자체를 데이터 오류로 보지 않는다. null을 자동 0/비적용으로 바꾸지 않고, 값이 있는 항목은
actual value를 final에 전달한다.

dev의 24개 positive count는 각 5–8개로 모두 존재한다. nonblank gold evidence 54개는 전부 한
source document의 exact substring이고 500자/NFC 위반은 0이다. non-absence positive 중 68개는
gold evidence가 비어 있으며 metadata 관계형 판정도 포함하므로 이를 input missing 또는 recall
상한으로 해석하지 않는다. absence positive 31개는 규칙대로 evidence가 비어 있다.

## 2. 입력 완결성과 감사 도구 자체의 결함

v30/v31 final 기준 exact tokenizer admission은 `168×1 + 21×2 + 11×3 = 243` contexts이며,
organizer가 실제 제공한 374개 문서의 omission은 0이다. actual-value audit도 200 notices와
243 contexts 전부 통과했다. 따라서 **pipeline이 받은 문서를 버리거나 카드/실제 metadata/제품
사실을 final에서 빠뜨리는 결함은 현재 검사 범위에서 발견되지 않았다.**

다만 이 결론에 도달하는 과정에서 감사 도구 두 개의 결함을 찾았다.

- `audit_candidate_semantic_contract.py`가 exact tokenizer를 연결하지 않아 overflow notice도
  한 개의 무제한 message처럼 검사했다. audit v2는 실제 context를 모두 렌더링하며 overflow
  PPS-DEV-143의 3개 context를 다시 검사해 PASS했다.
- 문서화된 `profile_data.py --config ...` 명령이 실제로는 `--config`를 받지 않았다. config의
  data root/input/labels/item-table을 따라가도록 고치고 configured path를 결과에 남긴다.

이 정정 전의 단순 “render PASS”는 overflow 경계를 입증한 증거로 사용하지 않는다.

## 3. 카드 source-concordance

동일한 일곱 축으로 v1–v24를 전수 검토했다. v30은 v5/v6/v7의 계약유형·금액 selector,
v9 예외 범위, v12 적용 계약, v14 예외의 잘못된 전용, v15 고시금액 등 7개 확정 결함을 보수했다.
v4는 v30에서 항목명의 `고시금액 이상`을 hard gate로 다시 넣은 회귀가 발견됐다. organizer
법령의 금액 비의존 금지조항과 dev 양성 6건의 금액/evidence를 교차검증해 v31에서 gate를 제거했다.

남은 확정 불해소 항목은 v3의 정확히 1배 경계다. 항목명은 `1배수 이상`으로 등호를 위반에
포함하지만 법령은 `1배 이내`를 허용한다. source가 충돌하므로 dev-fit으로 한쪽을 발명하지 않는다.

v31의 v4 수정은 의미적으로 옳지만 all-24 성능은 안정적이지 않았다. fast에서는 v4가
`0/0/3 → 2/0/1`로 회복하면서도 무관한 v2/v3/v22가 변해 macro가 `.142361 → .122917`로
하락했다. holdout macro는 `.125000 → .166667`로 올랐지만 v4는 회복되지 않았고 gain은 무관한
v2에서만 나왔다. 이는 card 입력 누락보다 all-item attention/provider 변동을 지지한다.

## 4. 판정·parse·merge 누수

저장된 EXP208/209 raw 응답과 final을 분해한 결과, 비교 가능한 179/185 records에서 raw model
label이 parser/normalizer 때문에 바뀐 사례는 0이다. parse-error record가 전체 FN을 설명하지도
않는다. frozen postprocess의 v2/v3/v21 변경은 저장 dev에서 개선 방향이지만, 다른 21개 item의
낮은 recall은 merge나 evidence 후처리가 아니라 model이 처음부터 0을 출력한 결과다.

따라서 E-only 알고리즘, JSON repair, OR merge 변경을 주된 V 성능 해법으로 삼을 근거가 없다.
특히 source pack OR은 non-absence item의 서로 다른 문서에서 나온 positive를 보존하는 용도이지,
한 context 안에서 놓친 truth condition을 복구하지 못한다. absence item은 이미 per-pass AND를
사용한다.

## 5. 출력 형식과 반복 호출의 일반화 검사

source-concordant v30에서 다시 비교한 결과는 다음과 같다.

| 구조 | fast20 | holdout20 | 결론 |
| --- | ---: | ---: | --- |
| one-stage V/E | `.142361` | `.125000` | control |
| one-stage V-only | `.088889` | 미확장 | 열위 |
| V-only draft → V/E | `.123611` | 미확장 | 열위 |
| V-only×2 → V-only resolver | `.144444` | `.111111` | fast 미세 gain이 holdout에서 반전 |

반복 V-only는 prompt token을 약 3배 사용하고 독립 holdout에서 V/E보다 낮았다. 따라서 V-only
label을 여러 번 뽑고 evidence를 알고리즘으로 복구하는 방향은 label-quality 선행조건을 충족하지
못했다.

원문 뒤 exact 24-card recap도 fast `.083333`, 387.4초, 39 contexts로 실패했다. 단순 card
recency나 output serialization은 주 병목이 아니다.

## 6. 실행·설정·제출 재현성 결함

현재 root와 submission은 `decision_cards_v10_v6_v7_scope.json`을 base로 쓰고 v4에는 v11,
v5에는 v12 specialist를 사용한다. 따라서 v30/v31에서 보수한 v3/v6/v7/v9/v12/v14/v15 및
v4 최종 정의가 **현재 canonical all-item policy에 통합되어 있지 않다**. v30/v31의 admission과
semantic-contract PASS를 root EXP231 제출의 카드 완결성 PASS로 전용하면 안 된다. 최신 카드를
root에 바로 올리지 않은 이유는 all-item fast/holdout 성능이 안정적이지 않고 dev200·evaluator
runtime 승격 gate를 통과하지 못했기 때문이다. 결과적으로 현재는 “최신 source-concordant 연구
artifact”와 “과거 local-best이지만 runtime 불가인 submission policy”가 분리돼 있으며, 유효한
canonical submission candidate는 없다.

이번 감사에서 추가 도구/설정 결함도 확인했다.

1. root `config.yaml`의 `staged_run: {mode: "off"}`를 shared config loader가 실제 stage로
   해석해 즉시 `unsupported` 오류를 냈다. 명시적 off를 `None`으로 정규화하고 회귀테스트를
   추가했다.
2. root는 EXP208 base 뒤 v4/v5 specialist replacement를 선언하지만 local
   `scripts/run_experiment.py`에는 이 실행 경로가 없다. 제출 스크립트만 specialist를 실행한다.
   따라서 같은 config가 local 219-call base와 submission 619-call composition이라는 서로 다른
   정책이 되는 심각한 재현성 결함이다.
3. 기존 admission profiler의 `call_count=219`도 specialist 400 calls를 빼고 보고했다. profiler가
   base 219 + v4 200 + v5 200 = **declared execution 619 calls**를 표시하도록 고쳤다. 각 specialist도
   374 supplied documents, omission 0, 200×1 context다.

local runner에는 아직 specialist composition을 구현하지 않았다. 대신 선언된 specialist를
조용히 무시한 base-only surrogate를 실행하지 못하도록 fail-fast 처리했다. 그러므로 현재 root
config는 submission policy 설명에는 사용되지만 canonical local experiment command로 재현 가능한
상태는 아니다. 또한 619-call 제출은 이미 120분을 초과했으므로 제출 후보가 아니다.

## 7. 일반화 결론과 다음 gate

현재 증거가 지지하는 결론은 다음과 같다.

1. 주된 문제는 더 이상 “제공받은 문서나 실제 metadata/product fact가 final prompt에서
   빠진다”가 아니다. supplied-input delivery는 강하게 검증됐다.
2. 카드에는 실제 결함이 있었고 보수했지만, source-correct card가 all-item score를 자동으로
   높이지 않는다. 의미 정확성과 Gemma 실행 성공은 별도 축이다.
3. V-only, 반복 V-only, exact card recap, generic checklist/proof 확대는 일반 개선책이 아니다.
4. item-local specialist는 attention 병목을 입증하지만 200 calls씩 추가하는 방식은 runtime을
   통과하지 못하고, 저장된 item별 best를 oracle 조합해도 dev200 상한은 `.420269`다. specialist
   누적만으로 `.7`에 갈 수 없다.
5. 다음 유료 실험 전에는 먼저 **zero/low-recall item 한 개의 실패 사례에서 기존 7-category
   navigation으로 표현할 수 없는 source 관계를 입증**해야 한다. 그 뒤 그 관계만 source-only로
   구조화하고, final owner가 카드·모든 원문·metadata와 다시 대조하는 bounded architecture를
   설계한다. broad multi-item schema나 24-way grouping으로 바로 확대하지 않는다.
6. 동시에 runtime-feasible canonical base를 다시 정해야 한다. 619-call root composition과
   435-call EXP171은 제출 불가가 관측됐으므로, 새 구조는 품질 이전에 예상 call topology와
   evaluator 120분 gate를 통과해야 한다.
7. root policy를 바꿀 때는 최신 v31 카드를 무조건 승격하지도, 과거 EXP231을 canonical이라고
   계속 부르지도 않는다. 한 번의 변경에서 `(a) source-concordant card 선택`, `(b) 실행 가능한
   topology`, `(c) local runner와 submission runner 동형성`을 함께 충족하고 dev200/runtime을
   다시 검증해야 한다.

현재 가장 작은 다음 분석 대상은 제품/기업범위 absence family 중 하나다. 다만 v10 full catalog가
dev200에서 `TP4/FP66/FN3`으로 무너졌으므로, full catalog나 unknown→applicable 변환을 반복하지
않는다. v11 또는 v13의 gold-positive/false-negative 사례를 label-blind source 관계로 먼저 감사해
`실제 구매대상 ↔ exact-code 후보/특이사항 ↔ 참가자격 기업범위 ↔ 명시 예외` 중 기존 입력에
없는 관계가 무엇인지 증명한 뒤에만 최소 schema를 만든다.

## 재현 산출물

- raw audit: `outputs/data-quality-audit-20260918/dev-integrity.json`,
  `train-integrity.json`, `test-sample-integrity.json`.
- profile: `outputs/data-quality-audit-20260918/profile.json`.
- canonical exact topology: `outputs/data-quality-audit-20260918/canonical-admission.json`.
- v30 admission/value/semantic audit:
  `outputs/card-input-completeness-v30-20260918/`.
- V-only staged quality: `outputs/v30-vonly-staged-quality-audit-20260918/report.json`.
- detailed card audit: `docs/decision_card_source_concordance_audit_20260918.md`.
- V-only comparison: `docs/exp333_exp336_v30_output_strategy_requalification.md`.
- v4 resolution: `docs/v31_v4_organizer_definition_resolution_plan.md`.
- exact recap result: `docs/exp341_exact_card_recap_after_source_plan.md`.
