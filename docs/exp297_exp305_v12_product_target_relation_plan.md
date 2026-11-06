# EXP297–305 — v12 실제 구매대상·경쟁제품 조건·직생요구 관계와 V/E–V-only 비교

작성: 2026-09-15, dev / mac

## 가설과 최소 항목 근거

현재 최고 local composition의 v12는 `TP/FP/FN=1/1/5`, F1 `0.25`다. v12의 organizer
truth condition은 실제 조달대상이 경쟁제품이 아닌 일반제품이고, 그 계약의 실제 참가자격으로
직접생산확인을 요구하며, 별도 허용 근거가 없는 경우다.

현재 exact-code fact는 metadata 또는 공고 자료 어디에서든 organizer CSV code를 찾으면 `matched`로
보존한다. 이것은 source fact로는 맞지만, 그 code가 실제 조달대상과 같은지 또는 CSV `특이사항`
조건이 충족되는지까지 뜻하지 않는다. dev200 v12 양성 6건 중 다음 세 건이 이 차이를 직접 보인다.

- `PPS-DEV-053`: 실제 조달대상은 위탁연구인데 직접생산 요구 code는 행사기획 서비스다.
- `PPS-DEV-054`: 실제 조달대상과 축제대행 code는 대응하지만 CSV 행은 추정가격 3억원 미만에만
  적용되고 실제 입찰추정가격은 약 3.27억원이다.
- `PPS-DEV-056`: 인터넷지원개발서비스 code의 `소프트웨어 진흥법 제48조 적용` 조건을 실제
  조달대상과 별도로 확인해야 한다.

기존 7-category inventory와 all-item relation checklist는 제품·기업·직접생산 문구를 찾지만,
`실제 조달대상 ↔ 고시 후보 code ↔ 특이사항 충족 ↔ 참가자격 직생요구`의 관계를 별도 상태로
보존하지 않는다. 따라서 v10–v18 전체 schema나 Python rule을 만들지 않고 v12 하나에서만 시험한다.

## 불변 입력 계약

모든 arm은 다음을 유지한다.

1. incumbent decision cards의 나머지 23개 문구와 organizer 원본 항목표.
2. v12에 필요한 human-readable metadata와 condition-aware exact-code 제품 사실.
3. 공고문·규격서·과업지시서·제안요청서·예외공표서 중 실제 제공된 모든 문서.
4. exact Gemma tokenizer admission과 overflow source-pack coverage.
5. final 모델이 card, metadata, 제품 사실, 관계 관찰과 admitted 원문 전체를 직접 대조하는 구조.
6. Python은 source substring 검증·doc 연결·병합·직렬화만 하며 제품 적용이나 v12 label을 계산하지
   않는다.

raw metadata JSON, internal product status/code array, raw 법령, 법령 bundle, corpus/RAG는 넣지 않는다.

## 실험 arm

### EXP297 — existing-card V/E attention control

- base: `configs/config.exp205-relation-checklist-after-source-fast-panel-c4.yaml`
- allowed changes: `prompt.active_items`, `prompt.profile`, `prompt.mode`
- v12-only, `complete_fact_subset_v1`, plain `baseline`, V/E.

### EXP298 — source-correct v12 card, plain V/E

- base: EXP297.
- sole allowed change: `prompt.decision_cards_path`.
- 새 card는 actual purchase target과 exact-code row가 같은 대상이고 `특이사항`이 충족될 때만 그
  행이 v12의 경쟁제품 0조건이 된다고 명시한다. 다른 조달대상·불충족 조건의 code가 문서에
  있다는 이유만으로 실제 계약대상을 경쟁제품으로 바꾸지 않는다.
- 직접생산 문구는 실제 참가자격/필수요건일 때만 본다.

### EXP299 — relation review V/E

- base: EXP298.
- sole allowed change: `prompt.mode: baseline -> v12_product_target_review_v1`.
- 같은 응답에서 최종 판정보다 먼저 다음 source-grounded 관찰을 낸다.
  - 실제구매대상원문
  - 고시후보세부품명
  - 고시후보출처: metadata / 공고자료 / 둘다 / 없음 / 불명
  - 구매대상관계: 동일대상 / 다른대상 / 불명
  - 적용조건상태: 충족 / 불충족 / 조건없음 / 불명
  - 경쟁제품적용: 적용 / 비적용 / 불명
  - 직접생산요구원문
  - 직접생산요구역할: 참가자격 / 계약이행일반 / 서류안내 / 없음 / 불명
  - 허용사유: 있음 / 없음 / 불명
  - 카드대조: 1조건충족 / 0조건충족 / 판단불가
- 두 원문 field는 500자 이하 unchanged substring으로 Python이 검증한다. 관찰에서 label을
  계산하거나 override하지 않는다.

### EXP300 — relation review V-only

- base: EXP299.
- sole allowed change: `prompt.output_mode`.
- system/user 입력의 의미·순서·관계 관찰은 같고 final serialization만 v12 0/1로 줄인다.
- V-only가 label 성능을 실제로 개선하거나 유지하면서 completion/runtime를 줄일 때만, 검증된
  `직접생산요구원문`을 e12로 회수하는 후속을 허용한다. label gain 없이 evidence 복구를 먼저
  구현하지 않는다.

### EXP301–303 — conditional independent holdout

- EXP301: EXP298 plain V/E holdout.
- EXP302: EXP299 relation V/E holdout.
- EXP303: EXP300 relation V-only holdout.
- fixed `configs/dev_prompt_holdout_v1.json`만 사용한다. 이 cohort에는 v12 positive 1건이 있다.

### EXP304–305 — conditional confirmation and bounded multi-call

- fast와 holdout에서 이긴 단일-call arm 하나만 EXP304 dev200으로 확장한다.
- V-only가 V/E보다 우수할 때만 EXP305를 설계한다. EXP305는 동일 prompt majority 반복이 아니라,
  source-only v12 관계 추출을 모든 admitted pack에서 수행해 validated excerpts를 concat한 뒤,
  final V-only가 그 관찰과 모든 admitted 원문을 다시 보는 2-stage 구조다.
- EXP305의 final v12가 개선된 경우에만 positive의 검증된 직접생산 참가자격 substring을 e12로
  연결한다. 발췌 존재를 label rule로 쓰지 않는다.

## paid-run 전 필수 gate

1. 각 config에 `experiment.base_config`와 `allowed_policy_changes`를 선언하고 preflight가 선언 밖
   변경 0을 보여야 한다.
2. organizer archive 원본과 현재 `항목표.json`, dev input, labels, 경쟁제품 CSV/index hash를
   대조한다.
3. exact Gemma tokenizer로 dev200의 document type별 source coverage/provenance, omission,
   overflow와 call topology를 기록한다.
4. short complete `PPS-DEV-062`, attachment `PPS-DEV-194`, overflow `PPS-DEV-169`, 그리고 v12
   관계 양성 `PPS-DEV-053`의 actual rendered system/user message를 export해 사람이 읽는다.
5. v12 적용 전제, 1조건, 핵심 0조건/예외, 모든 source type, metadata/product fact가 final
   rendered prompt의 exact span에 있는지 semantic-input audit한다.
6. exact mock에서 ID/49열/parse recovery/evidence substring/isolated output을 검증한다.
7. 유료 직전 구현된 schema, selected mode/card/output mode가 가설과 일치하는지 재확인한다.

## 승격·중단 기준

- fast20은 `configs/dev_fast_panel_v1.json`만 사용한다.
- EXP298/299/300 중 하나가 EXP297보다 v12 F1을 높이고 TP를 잃지 않으며 FP를 늘리지 않아야
  holdout에 진입한다. 같은 F1이면 completion token과 runtime가 낮은 arm을 선호한다.
- V/E와 V-only의 label이 같으면 V-only를 runtime 후보로 보되, 실제 evaluator runtime이
  검증됐다고 표현하지 않는다.
- holdout의 v12 positive를 유지하고 FP가 control보다 늘지 않은 arm만 dev200으로 확장한다.
- relation 관찰이 맞는데 label이 틀리면 enum/card를 fast label에 맞춰 반복 수정하지 않는다.
- full product catalog, unknown→일반제품 Python 변환, code substring label rule, 같은 prompt
  consensus/majority, 다른 v로 schema 확대는 금지한다.

## 2026-09-15 paid-run 전 gate 결과

- organizer 배포본 `open (1).zip`과 현재 입력을 hash로 다시 대조했다. `항목표.json`, dev input,
  labels, 경쟁제품 CSV가 배포본과 일치하며, 24개 card artifact의
  `source_item_table_sha256`도 복구한 항목표 hash
  `368cb41f376d8ad7edbbdf181542e6e959de356f7f70d86e72943325ecad61d9`와 일치한다.
- EXP297~300 config preflight는 모두 통과했다. EXP297은 active item/profile/mode만,
  EXP298은 card path만, EXP299는 relation-review mode만, EXP300은 output mode만 바뀐다.
- exact Gemma tokenizer로 dev200 전체를 admission한 결과 source document는 374개이고 누락은
  네 arm 모두 0개다. EXP297/298은 200건 모두 1 pass다. EXP299/300은 가장 긴
  `PPS-DEV-11`, `PPS-DEV-197`만 각각 2 pass여서 총 202 calls다.
- 실제 rendered message를 short complete `PPS-DEV-062`, attachment `PPS-DEV-194`, long
  `PPS-DEV-169`, 관계 양성 `PPS-DEV-053`에서 export해 읽었다. card와 human-readable
  metadata 뒤 condition-aware 경쟁제품 사실, 모든 admitted 원문, after-source 관계 검토가
  순서대로 존재한다. raw metadata JSON, internal product status/code array, 법령/RAG 문맥은 없다.
  `PPS-DEV-053`에서는 위탁연구라는 실제 계약대상과 행사대행 code가 직접생산 참가조건에
  등장하는 사실을 모두 보존해, 두 역할을 모델이 대조할 수 있다.
- 네 arm의 v12 semantic-input contract가 `PPS-DEV-053`에서 통과했다. 적용 전제, 1조건,
  핵심 0조건, metadata span, organizer CSV provenance, 실제 공고문 span이 모두 추적된다.
- exact mock은 네 arm 모두 fixed fast20 20 IDs, 49열, validation error/warning 0으로
  완료했다. mock score는 품질 지표가 아니다.
- 전체 회귀검사는 `258 passed`다.

따라서 EXP297~300의 fast20 provider 비교를 실행할 수 있다. 이 gate는 카드가 정답이라는
결론이 아니라, 비교하려는 카드·관계 구조가 입력 누락이나 숨은 정책 변경 없이 정확히
렌더링된다는 결론이다.

## fast20 결과와 결정

| EXP | 형식 | v12 TP/FP/FN | v12 F1 | completion tokens | runtime |
| --- | --- | --- | --- | ---: | ---: |
| 297 | existing-card V/E | `1/1/0` | `.6667` | 644 | 20.685s |
| 298 | source-correct card V/E | `0/2/1` | `0` | 1,280 | 21.605s |
| 299 | relation review V/E | `0/3/1` | `0` | 5,093 | 25.245s |
| 300 | relation review V-only | `0/7/1` | `0` | 4,437 | 24.984s |

모두 fixed `configs/dev_fast_panel_v1.json`의 같은 20건이며 parse error는 0이다. EXP298은
기존의 유일한 positive `PPS-DEV-049`를 잃고 negative `PPS-DEV-191`, `PPS-DEV-194`를 1로
냈다. EXP299/300에서는 source-grounded relation field가 있어도 Gemma가 다음과 같은 내부 모순을
냈다.

- `경쟁제품적용=적용`인데 `카드대조=1조건충족` 또는 최종 v12=1.
- `직접생산요구역할=없음`인데 `카드대조=1조건충족` 또는 최종 v12=1.
- V-only는 V/E보다 completion을 656 tokens 줄였지만 FP를 3개에서 7개로 늘렸다.

따라서 source-correct condition을 장문 card 또는 same-response checklist로 넣는 방식은 성능을
개선하지 못했다. EXP298~300은 fast 승격 조건을 모두 실패했으므로 EXP301~305 holdout,
dev200, evidence recovery는 실행하지 않는다. review field를 Python 논리식으로 바꾸거나 동일
prompt를 반복하는 후속도 하지 않는다.
