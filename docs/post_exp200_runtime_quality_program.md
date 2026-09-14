# Post-EXP200 runtime and judgment-quality program

작성: 2026-09-14, dev / mac

## 결정

EXP200 corrected-input source-first/full-final은 dev200 repaired macro positive-F1
`.324798`을 기록했지만 public evaluator에서 batch 128로도 120분을 초과했다. EXP171의
batch 64 timeout과 함께 보면 batch 크기가 아니라 모든 공고 원문을 두 번 읽는 계산량이
제출 불가능 원인이다. EXP200은 입력·품질 진단 incumbent로 보존하되 그대로 재제출하지 않는다.

다음 프로그램은 입력 완결성을 유지하면서 요청 topology를 한 번의 full-source read로 줄이고,
이미 찾은 사실을 final이 잘못 조립하는 병목을 한 호출 내부의 observable fact-first output으로
검증한다. 카드, prompt calibration, output reasoning schema를 한 실험에 섞지 않는다.

## 근거

- EXP200 intended topology: stage 1 217 + final 221 = 438 calls.
- EXP200 recorded prompt/completion: 5,957,180 / 295,667 tokens.
- matched direct EXP172: 216 calls, 3,198,825 / 143,368 tokens.
- remote time EXP171/172: 1,501.6 / 686.5 seconds, 2.19x.
- EXP200 evidence-bearing positives 54개 중 navigation gold-span hit 49개, 그중 final FN 22개.
- EXP172에서 93% notice가 one pack이고 merge policy 효과는 macro -0.001788에 불과하다.
- EXP200 zero-TP items: v6, v7, v10, v11, v13, v14, v16, v17, v18, v20.
- v23은 33 predicted positives 중 FP 31개로 반대 방향의 관계 오류가 있다.

따라서 다음 병목은 broad source retrieval이나 OR/AND merge가 아니라 applicability, 관계,
예외와 최종 0/1의 조립이다.

## 입력 완결성의 정확한 범위

현재 organizer-provided input transport는 강하게 검증됐다.

- dev 200 records / 374 supplied documents, exact admission omission 0.
- 21 metadata fields 모두 존재하며 human-readable renderer로 전달된다.
- corrected cards, condition-aware competition-product facts, anonymization semantics가 final에 있다.
- organizer test sample 10건 모두 `anon_applied=true`이며 익명화 legend가 실제로 렌더된다.

그러나 semantic correctness까지 완결됐다고 부르지 않는다.

- organizer assembly 이전에 빠진 dev 제안요청서 10건은 복구할 수 없다.
- v10–v18 gold-positive 58 cells 중 exact product applicability unknown이 30개다.
- document code가 실제 구매대상인지 참가등록/기존장비인지 role relation은 아직 완전히 감사되지 않았다.
- v6/v7에서 card scope 오류가 발견됐으므로 나머지 card도 독립 source audit 대상이다.
- 일부 dev gold와 visible source/official meaning의 충돌은 별도 concordance로 관리한다.

## Phase A — EXP202 corrected direct full-source control

### 가설

EXP200에서 fact-inventory stage만 제거하면 corrected cards/metadata/product/semantics와 모든
admitted source를 유지하면서 호출과 prompt-token workload를 약 절반으로 줄일 수 있다. 이
control은 corrected input의 one-stage quality와 runtime-safe floor를 확정한다.

### base와 허용 변경

- base: `configs/config.exp197-human-readable-metadata-fast-panel-c4.yaml`
- candidate: `configs/config.exp202-corrected-input-direct-fast-panel-c4.yaml`
- allowed policy change: serialized `staged_run` mapping과 그 `mode` 제거. 둘은 같은
  execution-topology 변경을 preflight가 표현하는 두 diff key다.
- 고정: cards, metadata, product facts, source scope/order, tokenizer admission, V/E schema,
  merge/evidence, frozen historical postprocess, model/provider/seed/temperature/concurrency.
- frozen rule 전 model-owned 결과와 rule 후 제출 결과를 모두 보고한다.

### 유료 전 gate

1. preflight에서 declared difference 하나만 존재.
2. exact-token admission에서 supplied source omission 0, over-budget 0, call count 기록.
3. short complete, attachment, overflow의 exact rendered messages를 export하고 사람이 읽는다.
4. 24/24 semantic-input contract를 final rendered prompt에서 audit한다.
5. exact config mock이 20 rows / 49 columns / ID/evidence validation을 통과한다.
6. isolated output path와 API key 환경만 사용한다.

### 성능 gate

- `configs/dev_fast_panel_v1.json` fast20만 먼저 실행한다.
- parse/recovery 오류 0, source omission 0이어야 한다.
- corrected source-first EXP196 fast `.213889`와 policy-identical direct comparison은 아니므로,
  EXP202의 주 대조는 같은 corrected input의 다음 fact-first treatment다.
- runtime-safe control은 낮더라도 보존한다. 후보 승격은 holdout20, dev200 순서로만 한다.

## Phase B — one-call fact-first judgment

### 구조 가설

별도 navigation call을 없애고 한 structured generation에서 source-grounded observation을 먼저
출력한 뒤 V/E를 출력하면, 원문 prefill은 한 번만 수행하면서 source-first의 판단 집중 효과를
일부 보존할 수 있다. 이것은 hidden chain-of-thought가 아니라 검증 가능한 짧은 사실 field다.

첫 항목은 v24 하나다. 현재 input에는 비교 metadata와 source가 있지만 EXP200은 8 positive 중
1개만 잡았다. v24 output 앞에 다음의 compact review를 둔다.

- 비교 field 또는 `없음`
- 원문 대응값의 unchanged excerpt 또는 null
- metadata 대응값의 human-readable value 또는 null
- 같은 의미 field인지
- 두 값이 양립 가능한지

Gemma가 같은 response 뒤에서 모든 v1–v24/e1–e24를 최종 판정한다. Python은 schema parsing,
source substring 검증, evidence resolution, pass merge만 하고 review field를 label로 변환하지 않는다.

### 최소성 및 확장 gate

- base: EXP202.
- 첫 treatment에서 허용하는 변화는 output/reasoning schema와 그 명시 instruction뿐이다.
- v24 외 item card, source, metadata, merge, model parameters는 고정한다.
- 먼저 schema upper-bound token, mock, rendered inputs, malformed recovery를 검증한다.
- fast20에서 v24 TP/FP와 전체 recall이 악화되지 않고 macro가 개선될 때만 holdout20으로 간다.
- holdout에서도 같은 방향일 때만 dev200 및 두 번째 relation family로 확장한다.
- 24-item ledger, 다중 draft, 별도 verifier, item grouping으로 즉시 확대하지 않는다.

## Phase C — card and calibration audit

모델 호출과 독립적으로 24개 card를 organizer item table과 제공 법령 provenance에 역추적한다.
우선순위는 v24, v20, v6/v7, v10–v18, v23이다. 각 card에서 applicability, 1-condition,
material 0-condition/exception, missing-information treatment를 분리한다.

현재 system과 cards에 반복되는 `판단이 어려우면 0`, `하나라도 불명이면 0`이 실제 0 조건과
정보 부족을 혼합하는지 감사한다. 이를 바꾸는 실험은 fact-first schema와 섞지 않고 별도
one-variable prompt-calibration ablation으로 둔다. `불명=1` 규칙이나 Python override는 만들지 않는다.

## Runtime gate

- public 후보는 dev200 exact-admission 기준 약 230 calls 이하를 목표로 한다.
- 한 notice의 source를 두 번 읽는 구조, v grouping, document×group multiplication은 제출하지 않는다.
- batch 증가는 총 계산량 감소로 세지 않는다.
- full-source one-pass도 32k prompt 때문에 2시간 통과가 자동 보장되지 않으므로 call count,
  prompt/completion tokens, p50/p95/max prompt, finish reason을 남긴다.
- exact paragraph dedup의 label-blind 절감은 dev 2.78%, sample test 4.67%뿐이므로 핵심 runtime
  전략으로 채택하지 않는다.

## 외부 기준선

동료 near-vanilla public `.32734` / 약 32분의 original zip/config를 받을 수 있으면 최우선으로
chat template, schema, context, model options, evidence, postprocess를 exact diff한다. 확보되지 않아도
EXP202와 fact-first program은 진행하며 이를 blocker로 삼지 않는다.

## 종료 조건

- EXP202와 첫 v24 fact-first treatment의 fast 결과가 모두 확보되고 artifacts가 완전해야 한다.
- treatment가 gate를 통과하면 holdout, 그 뒤 dev200까지 진행한다.
- gate를 통과하지 못하면 wording 반복 없이 결과와 원인을 기록하고 Phase C의 다음 근거 기반
  item을 선택한다.
- public 후보는 quality뿐 아니라 120분 workload gate를 동시에 통과해야 한다.

## 2026-09-14 실행 상태

- EXP202 fast20: `.239683`, 24 calls, 59.1 s. dev200 exact admission은 217 calls,
  374/374 supplied documents, omission 0이다.
- EXP203 v24 fact-first: `.255556`, 24 calls, 76.8 s. 그러나 v24가
  `0 TP / 0 FP / 3 FN`에서 `0 TP / 3 FP / 3 FN`으로 악화되어 target gate를 실패했다.
- 사전 규칙대로 holdout/dev200은 중단했다. 상세 결과는
  `docs/exp202_exp203_runtime_quality_result.md`에 기록했다.
- 다음 단계는 v24 positive-8 concordance와 v20 또는 v6/v7 card/calibration audit이다.
