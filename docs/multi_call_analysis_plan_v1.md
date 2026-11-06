# EXP123 이후 다중 호출 분석 계획 v1

작성일: 2026-09-09 (dev / mac)

## 목적

현재 최고 공개 관측은 `pps_20260906_233304.zip`의 EXP123이다.

| 정책 | Local dev-200 | Public | Runtime |
| --- | ---: | ---: | ---: |
| EXP120 | 0.248932 | 0.244317 | 기록 참조 |
| **EXP123** | **0.317797** | **0.260446** | **37분 14초** |
| EXP135 two-way v partition | 0.246940 | 0.220069 | 93분 28초 |

EXP123은 EXP120의 **card v6 + ordered 4,000-character single V/E Gemma
call**을 유지하고, 정상 pipeline finalization 뒤 v2/v3/v21만 organizer
metadata와 전체 notice source substring으로 정한 deterministic predicate로
교체한다. 다른 21개 v/e는 EXP120의 Gemma 결과를 보존한다.

이 계획의 목적은 EXP123을 버리고 organizer minimum baseline을 재시도하는 것이
아니다. EXP123을 incumbent로 고정한 상태에서, 하나의 24-item 판단을 여러
semantic operation으로 나누는 방식이 public quality와 2시간 runtime 안에서 성립할
수 있는지 폭넓게 분석하고 검증하는 것이다.

## 비목표와 고정 조건

- raw law/article RAG, generic case RAG, dev error를 본 새 item-level numeric/
  keyword rule 누적은 대상이 아니다.
- EXP123의 v2/v3/v21 rule source, predicate, evidence contract는 변경하거나
  제거하지 않는다.
- evidence는 unchanged source-document substring, 500자 이하를 유지한다.
- 각 notice에는 실제 notice를 포함한 Gemma 호출이 최소 한 번 존재해야 한다.
- `full_split_merge × v grouping`처럼 source-document pass와 item-group pass를
  곱하는 topology는 이미 runtime 실패했으므로 재시도하지 않는다.
- exact vLLM tokenizer/throughput은 이 mac 환경에서 측정할 수 없다. OpenRouter
  token 값은 비교용 관측치일 뿐 submission admission 증거가 아니다.

## 두 종류의 대조군

1. **Organizer control**: item name/note, metadata, ordered 4,000-character
   context만 가진 official baseline. 이는 무엇이 모델에 전혀 들어가지 않는지
   진단하는 하위 control이다.
2. **EXP123 incumbent**: card v6와 v2/v3/v21 frozen full-source rule을 포함한
   최고 public policy. 모든 새 후보의 성능·runtime·evidence 비교 기준이다.

`docs/semantic_input_contract_v1.md`의 matrix는 다음 단계에서 두 policy를
나란히 보인다. “organizer control에서 빠졌다”는 사실만으로 EXP123에서 새 정보를
더 넣어야 한다는 결론을 내리지 않는다.

## 분석 산출물 순서

### A0. EXP123 policy-delta semantic matrix (offline)

v1–v24 각각에 대해 아래를 organizer control과 EXP123에서 비교한다.

- 실제 system/user prompt에 있는 card condition과 metadata/CSV 사실
- 4,000자 context에 들어가는 문서 범위
- full-source Python predicate가 있는지와 해당 item
- final label/evidence의 소유자(Gemma 또는 frozen rule)
- source-provenance 및 unresolved input gap

이 matrix는 labels를 읽지 않는다. v2/v3/v21이 이미 Python 전체원문으로
보정됐다는 사실을 이후 prompt 후보에서 빠뜨리지 않기 위한 admission gate다.

### A1. Notice-level operation and runtime topology audit (offline)

dev-200을 사용하되 labels 없이 다음을 계산한다.

- 공고당 document type/length/4k omission pattern
- 각 architecture별 `calls per notice`, `items per call`, fallback path,
  worst-case call count
- exact rendered prompt의 request count, schema size, character count,
  OpenRouter historical token observation(있는 경우) 및 submission runtime
  미확정 표시
- EXP123 37분 14초와 EXP135 93분 28초를 기준으로 한 optimistic/guarded runtime
  projection

다중 호출 후보는 항상 single 4k notice context를 재사용한다. 이 단계에서
document splitting은 도입하지 않는다.

### A2. Four architecture contracts (offline prompt/mock review)

#### A. Disjoint v semantic groups

예비 source-domain group은 다음 세 개다. 이는 dev label이 아니라 항목의
source/operation 형태로 정한다.

- `qualification`: v1–v8, v21
- `product_and_absence`: v10–v18
- `document_procedure_consistency`: v9, v19, v20, v22–v24

각 호출은 자기 item만 최종 V/E를 낸다. item ownership이 겹치지 않으므로 merge는
OR/majority가 아니라 **ordered concatenation**이다. EXP123 frozen rule은 마지막에
동일하게 v2/v3/v21을 덮어쓴다.

이 3-call form은 가능성 탐색용 upper bound다. runtime audit에서 guarded 2시간
projection을 넘으면 실행하지 않는다. 2-group compression은 이 3-group prompt의
오류/길이 분석 후에만 정의하며, EXP135 G01/G02 membership을 재튜닝하지 않는다.

#### B. Candidate triage → strict final adjudication

1차 호출은 final 0/1이 아니라 각 item의 다음 상태를 낸다.

- `명시근거`: 원문에 실제 제한/요구/불일치 문구가 있음
- `부재검토`: 부재 항목 또는 whole-notice condition을 검토해야 함
- `불명확`: 관련 문구/전제가 있어 final 판단이 필요함
- `해당없음`: 관련 사실을 확인하지 못함

2차 호출은 `명시근거`, `부재검토`, `불명확` item만 strict V/E로 판정한다.
1차 `해당없음`을 final 0으로 사용하는 것은 **positive-coverage analysis가
확인한 뒤에만** 허용한다. 부재탐지 item은 원칙적으로 `부재검토`로 보내며,
1차가 absence를 확정하지 않는다.

fallback은 malformed triage 또는 item 누락 시 해당 notice의 full 24-item EXP123
single call이다. fallback까지 포함한 worst-case call count를 runtime report에 쓴다.

#### C. Evidence/location retrieval → final adjudication

1차 호출은 label을 내리지 않고 active item별로 원문 unchanged substring 또는
`찾지못함`만 반환한다. 2차 호출은 original notice context, 1차가 찾은 source
substring/주변 문맥, 필요한 metadata와 card를 받아 final V/E를 낸다.

이 구조는 explicit source text의 의미 해석과 evidence copying을 분리한다. 그러나
v10/v11/v16/v18/v20의 whole-notice absence는 locator-only로 판단할 수 없으므로
이 items는 2차 full review로 직접 보내거나 별도의 `부재검토` 상태를 사용한다.

1차 locator가 source text를 못 찾은 non-absence item을 final 0으로 쓰려면,
dev labels는 설계 뒤의 **coverage evaluation**에만 사용한다. coverage가 약하면
이 architecture는 종료하며 locator prompt를 v별로 tweak하지 않는다.

#### D. Draft judgment → independent legal review

이 구조는 1차가 전 v의 잠정 V/E를 내고, 2차가 **동일한 실제 공고 자료와 카드**를
다시 읽으면서 1차 판단을 유지하거나 정정하는 방식이다. 1차 V/E는 정답·규칙·증거가
아니며, 2차가 모든 24개 final V/E를 단독 소유한다.

- 1차의 0은 2차의 0을 확정하지 않는다. triage B v1처럼 positive를 조기 종료하지
  않는다.
- 1차의 evidence는 navigation/검토 후보일 뿐이고, final evidence는 2차가 원문에서
  다시 검증한 unchanged substring이어야 한다.
- 2차에는 “초안이 틀릴 수 있다. 초안에 따르지 말고 원문·metadata·card로 독립 판단”을
  명시한다. 따라서 이것은 self-consistency vote나 Python majority merge가 아니다.
- malformed 1차는 빈 초안으로 처리해 2차 full review를 계속하며, malformed 2차만
  ordinary all-item call로 recovery한다.

이 후보는 역할 분리 자체가 Gemma의 24-item 동시 판정 오류를 줄이는지를 검증한다.
raw law/RAG, 새 수치 규칙, document splitting을 추가하지 않는다.

#### E. Absence-item focused partition

v10/v11/v16/v18/v20은 한 문구의 위반 탐지가 아니라 필요한 조건이 **전체 공고에
없는지**를 확인하는 항목이다. 이 group을 나머지 explicit-item group과 분리하는
two-call candidate를 별도로 둔다. 각 call은 자기 item만 final V/E를 내며 merge는
ordered concatenation이다.

다만 complete notice scope가 실제로 제공되지 않는 4k context에서는 absence 1을
강하게 주장할 수 없다. 이 후보는 source-coverage audit가 all-document requirement를
만족하는 record subset 또는 complete-document admission strategy를 증명할 때만
유료로 실행한다. 단순 4k prompt를 두 번 읽히는 것을 complete absence review로
부르지 않는다.

#### F. Complete-source fact inventory → final adjudication

EXP152는 complete source를 **한 long final V/E task**에 넣는 방식이 fast20에서
실패했다. EXP144–146의 label-draft adjudication도 이미 실패했으므로, F는 두
실패를 반복하지 않는다.

1차는 exact-token ordered packs로 all supplied documents를 읽되, label을 내지
않는다. 각 active v에 대해 다음 중 하나만 낸다.

- actual source의 짧은 unchanged candidate excerpt (document type/id 포함)
- absence item의 `필수문구_발견` 또는 `이 pack에서_미발견`
- relevant fact를 찾지 못했을 때 `후보없음`

이것은 위반/무위반·법령 해석·evidence 확정이 아니다. `후보없음`은 final 0도 아니며,
absence item의 pack-level state는 Python이 **AND로 결합할 수 있는 관찰**일 뿐이다.
2차는 4k organizer context와 1차의 source-labelled excerpts를 함께 받고, 모든 24 V/E를
원문/metadata/card로 독립 판단한다. excerpt가 없는 항목도 0으로 닫지 않는다.

이 구조의 목적은 full source 전체를 final prompt에 반복하지 않으면서도 attachment의
사실을 source-preserving compact signal로 전달하는 것이다. source excerpt는 prompt의
새 법령/요약/RAG가 아니며, current notice의 unchanged substring만 허용한다.

F는 구현 전에 다음 offline gate가 필요하다.

1. exact tokenizer로 stage-1 packs + final 4k의 call-count/token projection을 낸다.
2. short/attachment/overflow fixture에서 stage-1 prompt는 all supplied docs, stage-2는
   only source-labelled inventory plus normal final context임을 export/read한다.
3. mock에서 malformed inventory, candidate 없는 positive, absence pack AND, final parse
   recovery, evidence substring validation을 검증한다.
4. fast20에서는 stage-1 candidate coverage를 gold evidence가 있는 positive에 대해
   **평가 후** 보고한다. coverage가 낮아도 v별 phrase tuning을 하지 않고 F를 종료한다.

F의 total calls는 `complete-source pack count + one final`이다. EXP152 fast20의 observed
distribution으로는 2–7 calls/notice가 가능하므로, fast observed latency로 2-hour
projection을 다시 계산하기 전에는 submission candidate가 아니다.

### EXP153 F fast-20 outcome

EXP153은 fast20에서 `0.280556`이었다. EXP152 one-stage `0.224306`보다 크게
회복했으나 EXP147 4k single `0.291071`보다 `-0.010516`이다. inventory parse error는
0, unchanged candidate excerpt는 98개였고 runtime은 75.664초/682,723 tokens였다.
따라서 F의 information-preserving separation은 단순 label-draft review와 다르지만,
current broad inventory form을 holdout/dev200/submission으로 확대할 근거는 없다.
상세는 `docs/exp153_inventory_final_fast_result.md`에 기록한다.

### G. 32k complete-source control

EXP154는 EXP152 complete-source one-stage policy의 `max_model_len`만 16k에서 대회 허용
32k로 바꾼 diagnostic이다. exact tokenizer admission은 dev-200 193 one-pass/7 overflow,
208 calls였고 EXP152의 123/77/384보다 fragmentation을 줄였다. semantic contract 24/24,
short/attachment/overflow rendered input, mock, regression을 모두 통과했다.

fast20 F1은 0.241667로 EXP152 0.224306보다 올랐지만 EXP147 4k control 0.291071보다
낮았다. 이는 4k omission이 유일한 병목이 아님을 보여준다. 이후 complete-input 후보는
32k exact admission과 all-supplied-source contract를 기본으로 하되, 4k front-cut을
“완결 입력”으로 부르지 않는다. 상세: `docs/exp154_complete_fact_32k_fast_result.md`.

### H. Complete-source two-way final partition

EXP155는 existing `document_restrictions_two_way_v1` 19+5 item partition을 32k
complete-source context에 적용했다. semantic contract group audit 24/24, mock,
preflight를 통과했지만 fast20 F1은 0.237500(42 calls)으로 EXP154 0.241667보다 낮았다.
따라서 19+5 split은 종료한다.

EXP156은 별도 source-domain two-way probe다. G01은 qualification/document/procedure/
consistency, G02는 product/absence라는 서로 다른 truth-condition family를 맡는다.
이는 EXP155 error row나 dev label을 보고 만든 rule이 아니며, 어떤 group도 source를
생략하지 않는다. 두 group의 quality와 runtime을 fast20에서 함께 측정한다.

EXP156은 fast20 0.213889, 40 calls, wall 45.67초로 EXP154 one-stage 0.241667보다 낮았다.
그러므로 H 아래의 simple disjoint item partition branch는 종료한다. source-complete
admission을 포기하지 않되, 다음 candidate는 group membership 재배치가 아니라 source fact의
representation과 final legal judgment의 역할 분리를 검증해야 한다. 상세:
`docs/exp155_exp156_complete_source_group_results.md`.

### A2.5. Input-truthful card control (required before B/C paid calls)

A0 rendered-input review found a prerequisite defect in EXP123 card v6:
v10–v13 say “provided competition-product lookup”, but EXP123 supplies no
friendly exact CSV lookup; v10/v11/v16/v18/v20 instruct a whole-document
absence check while the 4k single context explicitly omits attachments on
some notices. A multi-call run that copies those cards would change both
operation topology and this factual input contradiction.

Create a versioned **input-truthful card control** that changes only these
claims:

- no exact organizer CSV fact supplied → do not claim that a provided lookup
  established competition/general-product status;
- an omitted-document marker exists → do not claim absence across all notice
  documents; route/return uncertainty instead;
- do not add CSV text, full documents, law text, new numeric thresholds, or
  new Python overrides.

Run this as an EXP123-compatible single-call control before B/C. Its result
does not test product facts or document expansion; it isolates whether an
instruction that mentions unavailable information harms the incumbent card
policy.

### A2.6 Candidate semantic-input admission gate (required for every paid arm)

기존 A0 matrix는 organizer control의 결손을 보여주는 진단이었다. 새 후보에는
`semantic_input_contract_v1.md`를 읽고 아래를 **candidate config와 exact staged
messages 기준으로** 검증하는 generic audit을 실행한다.

1. active v마다 versioned card의 applicability/1-condition/material 0-condition이
   final stage system message에 exact span으로 존재하는가.
2. active v의 required metadata/organizer CSV fact가 실제 user message에
   human-readable span으로 존재하는가. 값이 주어지지 않으면 card가 그 값을 받았다고
   주장하지 않는가.
3. record별 required document type이 존재하는데 final stage context에서 omitted 된
   경우가 있는가. contract가 `qualification attachments`처럼 정확한 source type을
   말하지 못하면 **unresolved**로 fail한다.
4. short complete / overflow / attachment fixture의 stage-별 final messages를 export해
   사람이 읽고 review verdict를 남겼는가.

이 gate는 dev labels와 prior predictions을 읽지 않는다. `pass`는 quality evidence가
아니라 해당 architecture가 주장하는 입력을 실제로 받는다는 최소 증거다. `fail`이면
그 run은 API 호출 금지이며, complete-document strategy 또는 item scope를 먼저
정확히 해야 한다.

### A3. Paid exploration order

Paid run 전 모든 architecture는 다음을 갖춰야 한다.

1. `base_config`, `allowed_policy_changes`, `grouped_run` 또는 operation config
2. short complete / 4k truncation / attachment notice exact rendered messages
3. no-network mock, parse/error recovery, evidence substring validation
4. A0 matrix and A1 runtime manifest
5. isolated output directory and preflight success

그 뒤 **세 architecture를 모두 가능 후보로 남기되**, small fixed panels에서 먼저
다음 순서로 실행한다.

1. B triage→strict: early-0 route contract는 EXP150에서 반증되어 종료. 그 결과를
   참고하되 v별 route tuning은 하지 않는다.
2. C strict locator→final: EXP151에서 탐색 coverage가 낮아 종료. `찾지못함 → 0`은
   앞으로도 사용하지 않는다.
3. C2 broad-candidate locator→final: 항목별로 final label이 아닌 관련 원문 후보를
   넓게 제시하고, final이 원문을 독립 판단한다. A2.6 audit 통과 전에는 실행하지
   않는다.
4. D draft→independent review: 정보 손실 없이 2차가 all-item final을 소유하는
   신규 후보다. A2.6 audit·mock·runtime manifest 후 fast panel로 간다.
5. A two-group / E absence-focused partition: no more than two whole-notice calls;
   item ownership, complete notice scope, runtime guard를 모두 통과할 때만 fast panel로
   간다. 3-group은 runtime analysis-only upper bound로 유지한다.

각 arm은 EXP123-compatible single-call control과 같은 provider/model/seed/
temperature/4k context/evidence policy를 유지한다. input-truthful card를 쓰는 arm은
EXP147을 direct control로 쓰며, historical card v6 EXP123과 단일변경 대조라고
주장하지 않는다. 구조가 본질적으로 다르므로 “schema-only ablation”으로 부르지
않는다.

The input-truthful card control is evaluated before these three arms and
becomes their fixed card basis only if it passes its own isolated checks.

## 2026-09-09 사전 control 관측 (EXP147, fast panel만)

EXP123-compatible fast control은 macro positive-F1 `0.282738`이었고,
입력에 실제로 없는 경쟁제품 조회와 보지 못한 첨부문서 전체 부재판정 주장을
card에서만 제거한 EXP147은 `0.291071`이었다. 변경은 480개 v cell 중 7개였다.

- v2/v3/v21에는 변화가 없었다. 세 item의 full-source frozen override가 두 run에
  같은 순서로 적용됐음을 확인했다.
- v12는 gold positive 하나를 회복했으나 새로운 FP 세 개가 생겼다
  (F1 `0.000 → 0.400`). v1은 TP 하나를 잃었다
  (F1 `1.000 → 0.800`).
- 따라서 이 결과는 card의 factual contradiction이 무해하지 않다는 신호일 뿐,
  card 정책 또는 다중 호출의 승격 근거가 아니다. 독립 holdout과 dev-200을
  통과하기 전에는 EXP123 public incumbent를 교체하지 않는다.

## B fast-20 결론 (EXP150)

EXP150은 input-truthful card를 사용한 B implementation을 fast-20에 실행했다.
strict item은 평균 9.2개로 줄었지만, gold positive 19개가 triage `해당없음`으로
종료됐다. F1도 같은 single-call card control EXP147 대비 `0.291071 → 0.277020`으로
하락했다. 자세한 contract, stage input, route coverage, per-item 변화는
`docs/exp150_triage_strict_fast_result.md`에 있다.

따라서 `해당없음 → final 0` B v1은 종료한다. v별 route 문구를 dev 사례에 맞춰
보완하거나 holdout/dev-200을 실행하지 않는다. C locator는 `찾지못함 → 0`을 쓰지
않는 별도 architecture로만 진행한다.

### A4. Evaluation and promotion

각 paid fast run 후, frozen fast panel과 independent holdout panel에서 아래를
같이 보고한다.

- 24 positive-F1 mean, per-v precision/recall/F1, TP/FP/FN
- stage-1 positive coverage and routing rate (B/C)
- parse/malformed/fallback rate
- valid evidence rate and evidence source type
- calls per notice distribution, worst-case calls, observed remote latency/tokens

둘 다 directional gain이고 parse/evidence/runtime gate를 통과한 arm만 dev-200으로
간다. dev-200의 gain만으로 public submission policy를 바꾸지 않으며, EXP123 public
`0.260446`보다 나은 public observation이 있어야 incumbent를 교체한다.

## Runtime guard

EXP123의 37분 14초는 optimistic single-call anchor이고 EXP135의 93분 28초는
multi-call warning anchor다. 따라서 exact vLLM benchmark 전에는:

- unconditional two whole-notice calls: 분석/fast probe 가능, submission은
  guarded projection과 staged runtime proof가 있어야 함
- unconditional three whole-notice calls: analysis-only upper bound
- conditional third call: fallback/routing rate를 포함한 worst-case와 projected
  percentile runtime을 모두 기록
- batch size는 request count를 줄이지 않으며 별도 scheduling parameter

## 2026-09-09 candidate admission audit: EXP151 C1

`scripts/audit_candidate_semantic_contract.py`를 EXP151의 exact final staged input에
offline 실행했다. review fixture는 short notice `PPS-DEV-01`, attachment notice
`PPS-DEV-03`, long/overflow notice `PPS-DEV-062`이며 labels, predictions, provider는
읽거나 호출하지 않았다. 결과는 ignored
`outputs/exp151-semantic-contract-audit-v1/semantic_contract_audit.md`에 남는다.

결과는 **FAIL — broad locator C2를 실행하지 않는다**이다.

- decision-card text와 organizer metadata key는 24개 모두 final message에 있었다.
- 그러나 `metadata_style: full_json`은 사람이 읽는 필요한 사실만 주입한다는 canonical
  input policy를 위반한다.
- v10–v18은 contract가 요구하는 friendly exact competition-product CSV fact가 없는데
  EXP151은 product index를 주입하지 않는다.
- v9/v19는 reviewed attachment fixture에서 필요한 규격서·과업지시서·RFP source가
  4k final context 밖이었다.
- v1–v3, v5–v8, v10–v18, v20–v21, v24의 current contract scope는
  `qualification attachments`/`all supplied documents`처럼 exact organizer document
  type set이 아니므로 audit가 추측하지 않고 unresolved로 fail했다.

이는 EXP151 fast score가 무효라는 선언이 아니라, C1은 이미 종료된 diagnostic이고
그 위에 C2를 성능 후보라고 쌓을 수 없다는 뜻이다. 다음 유료 arm 전에는 source ledger와
item table을 다시 검토해 contract의 document scope를 exact source type으로 보완하거나,
complete-document admission을 먼저 구현·검증해야 한다. CSV는 단순 status/code dump가
아닌 friendly exact applicability text로만 넣을 수 있다.

## 2026-09-09 complete-fact admission measurement: EXP152 candidate

사용자 요구인 “법령은 카드로 압축하되 사실관계·정형 metadata·제품 고시 사실·제공
문서를 누락하지 않는다”를 하나의 coherent policy로 검증할 후보를
`configs/config.exp152-full-source-card-v6-product-fast-panel.yaml`에 만들었다.
이는 4k control의 one-field ablation이 아니라 input-completeness candidate임을
명시한다.

- 4,000-character cap을 제거한다.
- shared pipeline은 exact Gemma chat-template tokenizer로 complete notice가 들어가면
  한 call에 넣고, 넘는 notice만 ordered token-budgeted packs로 나눈다. 문서를
  조용히 버리지 않는다.
- card v6의 “제공된 경쟁제품 조회” 전제를 충족하도록 organizer CSV exact lookup의
  friendly Korean fact를 넣는다. v10–v18 모두 이 classification fact를 보도록
  renderer coverage를 수정했다. raw code/status key는 prompt에 넣지 않는다.
- raw metadata JSON 대신 organizer field/value의 human-readable line rendering을
  사용한다.
- non-absence는 OR, absence v10/v11/v16/v18/v20은 complete packs 전체가 1일 때만
  1인 AND로 결합한다.

Exact Gemma tokenizer profile (`outputs/exp152-token-admission-dev200-v1.json`)의
dev-200 관측은 complete policy의 실제 비용을 보여준다: one-pass 123, overflow 77,
총 384 calls (1.92 calls/notice), 최대 6 packs다. 따라서 이 arm은 4k single과
동일 runtime이라고 주장하지 않으며, fast20 observed latency와 test/sample tokenizer
call distribution을 기록한 뒤에만 submission candidate 여부를 판단한다.

`outputs/exp152-semantic-contract-audit-v1/semantic_contract_audit.md`는 short,
attachment, long fixture에서 24/24 card·metadata·friendly CSV·all-document coverage가
actual final message에 있는 것을 확인했다. 이 admission pass는 품질 보장이 아니라
EXP152가 실제로 complete-fact hypothesis를 시험할 자격이 있다는 뜻이다.

### EXP152 fast-20 outcome

EXP152은 mock/admission 뒤 실제 OpenRouter Gemma fast20을 실행했다. 결과는 macro
positive-F1 `0.224306`으로 EXP147 4k single `0.291071`보다 `-0.066766`이었다.
runtime은 80.614초, prompt/completion tokens는 498,451/28,665였고 parse error는 0이었다.
12 notice가 one pass, 나머지 8 notice가 2–6 pack이었다. 상세 per-v 변화와 evidence
warning은 `docs/exp152_complete_fact_fast_result.md`에 있다.

따라서 complete-fact **one-stage** policy는 fast gate를 통과하지 못하며 holdout/dev200/
submission으로 확대하지 않는다. 결론은 facts를 다시 빼자는 것이 아니라, full source
reading과 24-item final judgment를 같은 long call에 모두 과적재하는 것이 Gemma에 불리할
수 있다는 것이다. 이후 multi-call arm은 complete-fact admission을 유지하면서 final
decision burden을 분리하는지 검증해야 한다.

## Decision record

이 문서는 가능성을 미리 닫지 않는다. 다만 각 architecture가 무엇을 읽고, 누가
final label을 소유하며, 언제 0/1을 확정하고, 어떤 조건에서 fallback하는지를 코드
전에 명시한다. 이 계약을 충족하지 못하는 partial run은 diagnostic probe로만
기록하고 complete strategy의 성능으로 보고하지 않는다.

## EXP153 종료 뒤 coverage 판정

EXP153의 inventory excerpt와 평가가 끝난 뒤에만 gold positive evidence를 대조한 결과,
38개 중 6개(15.8%)만 겹쳤다. v2는 2/3, v3은 3/3, v22는 1/1이었고 나머지 positive
항목은 0이었다. 따라서 `inventory_then_final_v1`의 현재 “pack마다 24개 항목의
excerpt/null” 형태는 complete-source strategy의 충분한 사실 보존을 입증하지 못했다.
이 형식은 holdout/dev200/submission으로 확장하지 않으며, v별 키워드 조정으로 보정하지
않는다. 다음 architecture는 label이 아닌 source coverage를 먼저 측정할 수 있도록 사실
수집 단위를 줄이고 final judgment와 분리해야 한다.
