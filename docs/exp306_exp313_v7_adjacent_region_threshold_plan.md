# EXP306–313 — v7 고시금액·인접지역 적용성과 V/E–V-only 비교

작성: 2026-09-15, dev / mac

## 가설

EXP208 dev200의 v7은 `TP/FP/FN=0/0/7`이다. effective v10 card는 실제 참가자격,
기준지역↔추가지역의 인접 관계, 지방 2인 이상 견적 수의계약 허용을 이미 말하지만,
항목표의 적용 전제인 `고시금액 미만`을 판정할 실제 숫자와 기관 분기를 주지 않는다.

v7 양성 7건은 모두 원문에 둘 이상의 지역을 실제 본점·주된 영업소 참가자격으로 요구하는
substring이 있고 입찰추정가격도 2억 3천만원 미만이다. fixed fast20에는 양성
`PPS-DEV-039`, `PPS-DEV-072`, independent holdout20에는 `PPS-DEV-050`이 있어 recall과
specificity를 순서대로 검증할 수 있다.

가장 작은 가설은 다음과 같다.

1. v7만 떼어 읽게 하면 all-item attention 경쟁 때문에 사라진 양성을 회복할 수 있다.
2. organizer 제공 2026 고시금액과 human-readable metadata operand를 card에 명시하면
   `고시금액 미만` 적용 전제를 안정적으로 확인할 수 있다.
3. 같은 입력에서 V-only가 V/E보다 label 성능을 높일 때만, 서로 다른 역할의 독립 V-only
   검토를 후속으로 고려한다. 같은 prompt 반복·majority는 이미 기각됐으므로 재시도하지 않는다.

## source 감사

- 주최 측 항목표 v7: `고시금액 미만 지역제한 인접 확대`.
- 국가 시행규칙 제25조는 원칙적으로 현장·납품지가 있는 시·도만 허용하며, 현장이 인접
  시·도에 걸치거나 해당 지역의 유자격자가 10인 미만인 경우에만 인접 시·도를 포함할 수 있다.
- 지방 시행규칙 제25조도 현장·납품지 기준 시·도가 원칙이고, 현장 걸침·인접 납품지/시설
  유지관리·유자격자 10인 미만 등을 허용한다.
- 지방 수의계약 운영요령은 금액기준 2인 이상 견적 절차에서 시·군과 인접 시·군 또는
  시·도와 인접 시·도를 포함할 수 있도록 별도로 허용한다.
- 주최 측 2026 고시금액 자료는 일반 국가 물품·용역 2억 3천만원, 공기업·준정부기관
  물품·용역 7억 1천만원을 제공한다. 지방 기관·용역별 별도 기준은 organizer metadata로
  확정되는 경우에만 적용하며 기관명에서 추정하지 않는다.

법령 원문은 prompt에 넣지 않는다. 위 사실은 versioned v7 card의 압축 판단 기준으로만 쓴다.

## 불변 입력 계약

모든 arm은 incumbent v10의 v7 외 23개 card, v7에 필요한 human-readable metadata,
condition-aware 제품 사실, 실제 제공된 공고문·규격서·과업지시서·제안요청서·예외공표서,
exact Gemma tokenizer admission과 원문 substring evidence 검증을 유지한다. raw metadata JSON,
법령/RAG, Python 금액·지역·label rule은 사용하지 않는다.

## 실험 arm

### EXP306 — existing-card V/E attention control

- base: `configs/config.exp205-relation-checklist-after-source-fast-panel-c4.yaml`
- allowed changes: `prompt.active_items`, `prompt.profile`, `prompt.mode`
- v7-only plain V/E. 현재 v10 card를 그대로 쓴다.

### EXP307 — numeric-applicability card V/E

- base: EXP306.
- sole allowed change: `prompt.decision_cards_path`.
- v7만 바꾼 card는 적용계약법·소관구분·업무구분으로 고시금액을 선택하고
  `입찰추정가격 < 적용 고시금액`인지 확인한 뒤, 실제 복수지역 참가제한과 인접 관계 및
  명시 허용사유를 대조한다.

### EXP308 — numeric-applicability card V-only

- base: EXP307.
- sole allowed change: `prompt.output_mode`.
- input/card/source admission은 동일하고 final serialization만 v7 0/1이다.

### EXP309–311 — conditional independent holdout

- EXP309: EXP306 existing-card V/E holdout.
- EXP310: EXP307 corrected-card V/E holdout.
- EXP311: EXP308 corrected-card V-only holdout.
- fixed `configs/dev_prompt_holdout_v1.json`만 사용한다.

### EXP312–313 — conditional dev200와 다중 V-only

- fast와 holdout에서 이긴 single-call arm 하나만 EXP312 dev200으로 확장한다.
- V-only가 V/E보다 label 성능에서 이긴 경우에만 EXP313을 새로 설계한다. 후속은 동일 prompt
  반복 투표가 아니라, 첫 V-only가 적용금액·실제 참가제한·두 지역 역할·허용사유만 source-only로
  검토하고 두 번째 V-only가 card·metadata·검토·모든 원문을 다시 보는 final-owner 구조여야 한다.
- V-only label gain이 먼저 확인되지 않으면 evidence recovery와 다중 호출을 만들지 않는다.

## paid-run 전 gate

1. `base_config`와 `allowed_policy_changes` preflight 통과.
2. exact tokenizer source coverage/provenance와 omission/call topology 기록.
3. short `PPS-DEV-062`, attachment `PPS-DEV-194`, long `PPS-DEV-169`, v7 positive
   `PPS-DEV-039`/`PPS-DEV-050` rendered message 직접 검토.
4. v7 적용 전제·1조건·0조건/예외, required metadata와 모든 실제 source의 semantic-input audit.
5. exact mock 20 IDs, 49열, parse/evidence/output validation과 전체 pytest 통과.

## 승격·중단 기준

- EXP307/308은 EXP306보다 fast v7 TP/F1을 개선하고 FP를 늘리지 않아야 holdout에 진입한다.
- corrected V/E와 V-only가 동률이면 evidence를 보존하는 V/E를 품질 기본값으로 두고 V-only는
  serialization/runtime 관찰값으로만 남긴다.
- holdout `PPS-DEV-050`을 회복하고 control 대비 FP가 늘지 않은 arm만 dev200으로 간다.
- fast 실패 시 숫자·지역 예시·enum을 같은 ID에 맞춰 반복 수정하지 않는다.
- Python 비교/지역 인접/OR/majority label rule, full v-grouping, raw-law 입력은 금지한다.

## 2026-09-15 fast paid-run 전 gate 결과

- EXP306~311 config preflight가 모두 통과했다. fast arm의 유일한 단계별 차이는 v7-only
  attention, v7 card path, V/E↔V-only output contract이며 holdout arm의 controlled policy
  difference는 0이다.
- exact Gemma tokenizer로 dev200을 admission한 결과 세 fast arm 모두 200건이 1 pass에
  들어갔다. source documents는 374/374, omission 0, 예정 call count는 각각 200이다.
  최대 prompt는 EXP306 29,613, EXP307 29,858, EXP308 29,784 tokens로 budget 30,268 이하다.
- short `PPS-DEV-062`, attachment `PPS-DEV-194`, long `PPS-DEV-169`, fast positive
  `PPS-DEV-039`, holdout positive `PPS-DEV-050`의 actual rendered messages를 export해 읽었다.
  card 뒤 human-readable metadata와 모든 admitted 원문이 존재한다. 두 positive에서
  입찰추정가격과 복수지역 본점/주된 영업소 참가자격 substring이 함께 보인다.
- EXP307/308의 `PPS-DEV-039` user message SHA256은 일치한다. 즉 V/E와 V-only의 user
  semantic input은 byte-identical하고 system output contract만 다르다.
- EXP306~308의 v7 semantic-input contract는 `PPS-DEV-039`, `PPS-DEV-050` 모두 통과했다.
- exact mock은 각 20 IDs, 49 columns, validation errors/warnings 0으로 통과했다.
- 전체 회귀검사는 `259 passed`다.

따라서 EXP306~308 fixed fast20 provider 비교를 실행할 수 있다. 이 gate는 corrected card가
성능을 높인다는 결론이 아니라 입력 누락·token omission·숨은 merge/label rule 없이 가설이
정확히 구현됐다는 결론이다.

## 결과

### Fast20

| EXP | 정책 | v7 TP/FP/FN | v7 F1 | completion | runtime |
| --- | --- | --- | --- | ---: | ---: |
| 306 | existing-card V/E | `1/0/1` | `.666667` | 712 | 20.584s |
| 307 | threshold-card V/E | `1/0/1` | `.666667` | 929 | 20.819s |
| 308 | threshold-card V-only | `1/0/1` | `.666667` | 160 | 20.616s |

세 arm의 v7 labels는 20/20 동일했다. 숫자 card는 label을 바꾸지 않았고 V-only도 label gain이
없었다. V-only는 completion을 줄였지만 e7을 잃었으므로 EXP307/308은 종료한다. 회복된 양성은
세 arm 모두 `PPS-DEV-072`이고 exact source evidence가 유효했다.

### Historical exact-repeat 발견과 holdout 변동

실행 뒤 과거 문서를 다시 대조해 EXP306이 이미 끝난 EXP223 v7-only specialist와 같은 정책임을
확인했다. 과거 EXP223 fast도 `1/0/1`, F1 `.666667`이었고, 과거 EXP224 holdout은
`0/0/1`, F1 `0`으로 중단됐다. 특히 과거 EXP224와 새 EXP309의 `PPS-DEV-050.request.json`은
SHA256 `ca2cb9a2385ad230aaf509d282464372d2f8cbbf34aed0c76e5947ec36416a3c`로 byte-identical하다.

그럼에도 새 EXP309 holdout은 `PPS-DEV-050`을 1로 회복해 `TP/FP/FN=1/0/0`, F1 `1.0`이었다.
temperature 0의 같은 OpenRouter input에서도 과거 raw response 0과 새 raw response 1이 달랐다.
따라서 EXP309는 새로운 독립 일반화 증거가 아니라 **정책 동일 재실행에서 발생한 provider/model
변동성 증거**다. 동일 prompt 반복을 성능 전략으로 승격하거나 좋은 repeat만 선택하지 않는다.

### EXP312 dev200

EXP309의 repeat limitation을 명시한 상태에서 정책의 dev200 단일-run 상한을 측정했다.

- 200 calls, 203.115초, prompt/completion `2,380,796 / 7,296`, parse error 0.
- v7 `TP/FP/FN=3/2/4`, precision `.6`, recall `.428571`, F1 `.5`.
- TP: `PPS-DEV-10`, `PPS-DEV-050`, `PPS-DEV-072`.
- FP: `PPS-DEV-048`의 단일 경북 소재지, `PPS-DEV-122`의 작업 현장 납품지를 복수지역
  참가제한으로 오독했다.
- EXP262 composition에 v7/e7만 교체하면 Macro positive-F1
  `.3537749417 -> .3746082750`.
- runtime-부적합 EXP281 v20 연구 상한까지 합치면 `.3800907311`이지만, 이것은 제출 후보가 아니다.

## 결정

v7 item isolation은 한 dev200 run에서 유효한 local-quality gain을 보였지만, 동일 prompt의
holdout 결과가 과거 0과 현재 1로 뒤집혀 안정성이 증명되지 않았다. 또한 200 calls를 추가하므로
EXP231이 이미 120분을 초과한 제출 topology에는 그대로 더할 수 없다.

- EXP312 결과와 `.3746082750` composition은 연구 상한으로 보존한다.
- threshold card와 V-only는 label gain이 없으므로 canonical로 승격하지 않는다.
- EXP313 다중 V-only/evidence recovery는 실행하지 않는다.
- 같은 v7 prompt repeat, majority, best-of-run 선택은 하지 않는다.
- 다음 구조 후보는 specialist 호출을 더 쌓는 것이 아니라, 검증된 item-isolation 이득을 한 번의
  bounded final 안에서 유지할 수 있는 출력 attention 구조여야 한다.
