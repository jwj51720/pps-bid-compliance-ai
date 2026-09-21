# EXP275–277 — v20 SW 참여제한 하한 card와 V/E 대 V-only

작성: 2026-09-15, dev / mac

## Source-first 결함 감사

현재 local-quality incumbent에서 v20은 `TP 0 / FP 0 / FN 5`, F1 `0`이다. current v10 card는
`사업금액과 대기업 구간(20억·40억·80억)`을 확인하라고만 하며, 어떤 금액에서 어떤 제한이
필요한지와 사업금액 산식을 말하지 않는다. 참가할 업체의 매출구간이 공고에 없다는 이유로
`금액구간 불명` 0 조건에 빠질 수도 있다.

주최 측 법령 원문은 다음 truth condition을 직접 제공한다.

- 「소프트웨어 진흥법」 제48조제2항: 고시 하한 미만 SW 사업에서 대기업 SW사업자의 참여를
  제한한다. 장기 유지관리 사업금액은 계약기간의 연평균을 사용한다.
- 같은 조 제4항: 상호출자제한기업집단 회사는 법정 예외가 없으면 사업금액과 무관하게 제한한다.
- 참여지원 지침 제3조: 사업금액은 추정가격에 부가가치세를 포함하며, 분리·분담발주는 SW 부분
  금액을 사용한다. 하한제를 적용하면 공고문 또는 제안요청서에 적용 여부와 근거를 명시한다.
- 별표 1: 중소기업에서 중견기업이 된 지 5년 미만인 대기업은 20억원, 매출 8천억원 미만
  대기업은 40억원, 매출 8천억원 이상 대기업은 80억원 이상 사업부터 참여할 수 있다.
- 법 제48조제3항·제5항: 조달청 재발주, 국가안보, 민간투자, 지정 공공기관, 불가피 사유 등
  법정 비적용 사유를 별도로 확인한다.

따라서 사업금액별 최소 필요한 제한 범위는 다음처럼 읽을 수 있다.

- 20억원 미만: 세 대기업군 모두 참여제한.
- 20억원 이상 40억원 미만: 매출 8천억원 미만/이상 일반 대기업 참여제한.
- 40억원 이상 80억원 미만: 매출 8천억원 이상 대기업 참여제한.
- 80억원 이상: 하한제에 따른 일반 대기업 제한은 없지만 상호출자제한기업집단 제한은 계속 필요.

일반 `중소기업자만 참가` 문구가 결과적으로 대기업을 배제하더라도, 그것만으로 지침 제3조의
SW 대기업 참여제한 적용 여부·근거 명시를 충족했다고 자동 간주하지 않는다. 반대로 문서가
적용되는 SW 제한과 법적 근거를 명시했다면 표현이 완전히 같지 않아도 0일 수 있다. 최종 해석은
Gemma가 card, human-readable metadata와 모든 원문을 함께 보고 소유한다.

## Controlled arms

### EXP275 — existing-card V/E control

- base: `configs/config.exp205-relation-checklist-after-source-fast-panel-c4.yaml`.
- allowed changes: `prompt.active_items`, `prompt.profile`, `prompt.mode`.
- current v10 card로 v20/e20만 판단하는 `complete_fact_subset_v1`, plain baseline이다.

### EXP276 — corrected-card V/E

- base: EXP275.
- sole allowed change: `prompt.decision_cards_path`.
- 새 v19 artifact는 v10 대비 v20 text만 바꾼다.

### EXP277 — corrected-card V-only

- base: EXP276.
- sole allowed change: `prompt.output_mode: labels_and_evidence -> labels_only`.
- EXP276과 user input, card, metadata, product fact, 모든 source, admission, model parameters가 같다.
- e20은 대회 규칙상 항상 blank인 absence evidence field라서 V-only가 label을 유지하면 별도
  evidence 복원 없이도 출력 정보가 완결된다.

세 arm 모두 Python 금액 계산/법률/label override를 사용하지 않는다. Python은 tokenizer
admission, source/doc-id 연결, parsing과 merge만 담당한다.

## Paid-run gates

1. card artifact가 v10과 v20에서만 다르고 source 조건을 정확히 보존하는지 확인한다.
2. 선언된 base와 `allowed_policy_changes`로 preflight를 통과한다.
3. exact Gemma tokenizer로 dev200의 source coverage/provenance, fixed input, over-budget와 call
   topology를 기록한다.
4. short complete, attachment, overflow와 fast v20-positive의 실제 rendered system/user message를
   export하고 읽는다.
5. v20 적용성, 사업금액 산식·구간, 1/0 조건·예외, metadata와 모든 source type의 semantic-input
   contract를 별도 감사한다.
6. exact mock에서 49열, ID, parse, absence evidence와 output validation을 통과한다.

frozen fast20에는 v20 positive `PPS-DEV-131` 한 건이 있다. EXP276/277 중 하나가 EXP275보다
TP/F1을 개선하고 FP 폭증·parse/source failure가 없어야 frozen independent holdout20으로 간다.
V/E와 V-only의 label 성능을 우선하며 동점이면 completion과 evaluator runtime에 유리하고 e20
손실이 없는 V-only를 선택할 수 있다. holdout에서도 같은 방향일 때만 dev200으로 확장한다.

fast 실패 시 threshold 문구, 예시 또는 enum을 해당 ID에 맞춰 반복 조정하지 않는다. 그 경우
v20은 card 누락을 교정해도 관계를 실행하지 못한 것으로 기록하고 v8/v19 source-role 감사로
이동한다.

## Pre-provider gate

- 새 `decision_cards_v19_v20_threshold.json`은 incumbent v10 artifact와 비교해 v20 text만
  다르다. item name, absence flag와 나머지 23개 card는 같다.
- preflight는 EXP275에서 선언한 active-items/subset-profile/baseline-mode, EXP276에서 card
  path, EXP277에서 output mode만 각각 검출했다.
- exact Gemma tokenizer dev200 audit는 세 arm 모두 200 records × one pass, 374/374 source
  documents, source omission 0, overflow 0이다. 가장 긴 prompt는 EXP275 29,568,
  EXP276 29,930, EXP277 29,854 tokens로 30,268-token budget 안에 있다.
- short `PPS-DEV-062`, attachment `PPS-DEV-194`, 이전 all-item overflow 대표
  `PPS-DEV-169`, fast v20-positive `PPS-DEV-131`의 actual rendered messages를 세 arm에서
  export하고 읽었다. 이 item-only policy에서는 네 건을 포함해 dev200 전체가 single-pass라
  실제 overflow fixture는 존재하지 않는다. 169도 공고문과 제안요청서가 한 pass에 온전히 있다.
- 네 fixture 모두 v20 card, 업무구분·입찰추정가격·정보화사업여부·긴급공고여부 metadata와
  존재하는 공고문·규격서·제안요청서 원문을 보존한다. raw metadata JSON, internal product
  status/code array, raw law text는 없다.
- EXP276/277의 네 user messages는 각각 byte-identical하다. system/output schema에서 evidence
  contract만 다르다.
- active-v20 semantic-input contract는 세 arm·네 fixture에서 모두 PASS했다. 별도의 source-to-card
  감사는 사업금액 산식, 20/40/80억원 ladder, 상호출자제한기업집단, 법정 예외와 적용 여부·근거
  명시를 새 card에서 직접 확인했다.
- exact mock은 각 arm 20 rows, 49 ordered columns, unique IDs, parse error 0, e20 blank,
  validation error 0이다.
- full tests: `242 passed`.

세 fast20 provider arm만 승인한다.

## Fast20 result and holdout promotion

| arm | v20 TP/FP/FN | precision / recall / F1 | completion | runtime |
| --- | ---: | ---: | ---: | ---: |
| EXP275 existing V/E | `0/1/1` | `0 / 0 / 0` | 529 | 20.611s |
| EXP276 corrected V/E | `1/10/0` | `.0909 / 1.0 / .1667` | 528 | 20.539s |
| EXP277 corrected V-only | `1/6/0` | `.1429 / 1.0 / .2500` | 180 | 20.560s |

- 세 arm 모두 20 calls, parse error 0, validation PASS다.
- corrected card는 유일한 positive `PPS-DEV-131`을 회복했지만 V/E에서는 FP 10건을 만들었다.
- 같은 user input의 V-only는 TP를 유지하면서 V/E보다 FP를 4건 줄였다. completion은 65.9%
  감소했지만 wall time은 같아 remote runtime 개선 근거로 쓰지 않는다.
- V-only가 V/E보다 label 성능이 실제로 높은 첫 item-local 결과지만 fast precision은 낮다.

frozen independent holdout20에는 v20 positive `PPS-DEV-132` 한 건이 있다. 따라서 기존 V/E
EXP278, corrected V/E EXP279, corrected V-only EXP280을 policy-identical하게 모두 실행해 card
효과와 serialization 효과의 sensitivity/specificity를 다시 분리한다. holdout에서 corrected arm이
positive를 회복하고, V-only가 V/E보다 F1/precision을 유지하거나 개선해야 dev200 후보가 된다.

## Holdout20 pre-provider gate

- EXP278/279/280은 각각 fast arm을 그대로 상속하며 cohort와 output directory만 바꾼다.
  preflight effective differences는 세 arm 모두 `{}`다.
- exact Gemma tokenizer admission은 각 arm 20 records, 20 calls, 41/41 source documents,
  source omission 0, overflow 0이다. 최장 `PPS-DEV-27`도 EXP278 28,248, EXP279 28,610,
  EXP280 28,534 tokens로 30,268-token budget 안에 있다.
- actual rendered messages는 short `PPS-DEV-094`, attachment 및 유일한 v20 positive
  `PPS-DEV-132`, longest `PPS-DEV-27`에서 세 arm 모두 export하고 읽었다. v20-only
  topology에서는 holdout 전체가 one-pass이므로 별도 overflow fixture는 존재하지 않는다.
- DEV094는 공고문, DEV132는 공고문+과업지시서, DEV27은 공고문+과업지시서+제안요청서의
  원문 경계와 전체 텍스트를 보존한다. 세 fixture 모두 readable 업무구분·입찰추정가격·
  정보화사업여부·긴급공고여부와 v20 card를 포함한다. DEV132에는 SW사업자 업종과 실제
  소프트웨어 설치 과업 문구가 함께 보이므로 업종명만으로 적용성을 확정할 필요가 없다.
- EXP279/280의 세 user messages는 fixture별 SHA-256이 byte-identical하다. 차이는 system의
  V/E 대 V-only output contract뿐이다.
- active-v20 semantic-input contract는 세 arm·세 fixture에서 모두 PASS했다.
- exact mock은 각 arm 20/20 rows, 49 ordered columns, unique IDs, parse error 0, e20 blank,
  validation error 0이다. full tests는 `242 passed`다.

따라서 policy-identical holdout provider 세 arm을 승인한다.

## Holdout20 result and dev200 promotion

| arm | v20 TP/FP/FN | precision / recall / F1 | completion | runtime |
| --- | ---: | ---: | ---: | ---: |
| EXP278 existing V/E | `1/6/0` | `.1429 / 1.0 / .2500` | 491 | 21.125s |
| EXP279 corrected V/E | `0/9/1` | `0 / 0 / 0` | 535 | 21.068s |
| EXP280 corrected V-only | `1/5/0` | `.1667 / 1.0 / .2857` | 180 | 20.977s |

- 세 arm 모두 20 calls, parse error 0, validation PASS다.
- corrected V/E는 유일한 positive DEV132까지 놓쳐 fast 개선이 일반화되지 않았다. 카드 문구만의
  개선으로 보아서는 안 된다.
- corrected V-only는 DEV132를 회복하고 기존 V/E보다 FP를 하나 줄였다. 같은 corrected-card
  V/E 대비 TP `0→1`, FP `9→5`, F1 `0→.2857`이다.
- V-only의 V/E 대비 label 우위가 fast와 independent holdout에서 같은 방향으로 재현됐다.
  completion은 V/E 대비 66.4% 적지만 remote wall time은 사실상 같으므로 evaluator runtime
  개선으로 주장하지 않는다.

따라서 EXP280을 정책 변경 없이 EXP281 dev200으로 확장한다. EXP279는 holdout에서 명백히
실패했으므로 별도의 200-call V/E 반복에 비용을 쓰지 않는다. dev200에서 v20 자체 F1과
EXP262 incumbent에 v20/e20만 exact-ID overlay한 macro positive-F1을 함께 평가한다.

## EXP281 dev200 pre-provider gate

- EXP280 상속 후 cohort를 dev200으로 되돌린 것 외 effective policy difference는 `{}`다.
- exact tokenizer admission은 200 records × one pass = 200 calls, 374/374 source documents,
  omission 0, overflow 0이다. 최대는 `PPS-DEV-11`의 29,854/30,268 tokens다.
- holdout에서 이미 읽은 short/attachment/longest message와 동일한 policy이며, dev200 exact mock
  200/200 rows, 49 columns, unique IDs, parse error 0, e20 blank, validation PASS다.
- DEV132 active-item semantic contract를 dev200 config에서도 다시 실행해 PASS했다.

EXP281 provider run을 승인한다.

## EXP281 dev200 result

- exact topology: 200 records × one pass = 200 calls, 374/374 source documents.
- v20: `TP 5 / FP 66 / FN 0`, precision `.070423`, recall `1.0`, F1 `.131579`.
- parse error 0, output validation PASS. v20은 absence item이므로 e20은 전부 blank다.
- prompt/completion: `2,428,996 / 1,800` tokens; OpenRouter wall time 200.911초.
- EXP262 local-quality incumbent에 v20/e20만 exact-ID field replacement하면 Macro positive-F1은
  **`.353775 -> .359257`**이다. 71개 v20 cell만 바뀌었고 non-v20 cell 변경은 0이다.

따라서 corrected-card V-only는 fast `.2500`, holdout `.2857`, dev200 `.1316`으로 세 cohort에서
일관되게 양성 recall을 회복했고, 현재 최고 local composition도 `.005482` 올렸다. 이것은 지금까지
같은 입력의 V/E를 이긴 첫 재현 가능한 V-only item-local 결과다.

그러나 FP 66과 precision `.0704`는 매우 낮다. 새 card가 하한 기준은 완결했지만 실제 SW 사업
적용성 또는 문서에 이미 존재하는 적법한 제한/비적용 사유의 판독이 충분히 정밀하지 않다는 뜻이다.
이를 그대로 canonical card나 submission topology로 승격하지 않는다. 현재 composition에 추가하면
base+v4+v5+v14+v20 약 1,019 calls라 evaluator 120분 제한에도 부적합하다. 다음 단계는 66 FP를
source-grounded하게 유형화하여 card의 적용성 결함인지, 입력 organizer fact 결함인지, 모델의
absence 판독 실패인지 분리하는 것이다. 개별 문구를 Python rule로 고치거나 label-aware router를
만들지 않는다.
