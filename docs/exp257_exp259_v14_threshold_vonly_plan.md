# EXP257–259 — v14 missing threshold operand and V/E versus V-only

작성: 2026-09-15, dev / mac

## Audited defect and hypothesis

현재 최고 EXP231 composition의 v14는 dev200 `TP 0 / FP 0 / FN 8`, F1 `0`이다.
현재 v10 card는 `고시금액 이상`을 필수 전제로 요구하지만 실제 숫자 operand를 제공하지 않는다.
`docs/exp218_v4_independent_scope_plan.md`의 rendered semantic audit에서도 이 누락이 이미 별도
문제로 기록됐다.

organizer 제공 법령 원문은 이 관계를 완결한다.

- 「중소기업제품 구매촉진 및 판로지원에 관한 법률 시행령」 제2조의2제1항제2호는
  우선조달 구간의 상한을 「국가계약법」 제4조제1항에 따라 장관이 고시하는 금액으로 직접
  연결한다.
- organizer의 2026년 고시금액 문서는 그 WTO 물품·용역 금액을 `2억 3천만원`으로 명시한다.
  같은 문서의 공기업·준정부기관 계약사무규칙상 `7억 1천만원`은 다른 법적 selector이며,
  제2조의2제1항제2호가 가리키는 국가계약법 제4조제1항 금액으로 바꾸어 쓰지 않는다.
- 제2조의2는 `물품 또는 용역`을 대상으로 하므로 v14의 organizer 표시명 `일반물품`을
  goods-only gate로 좁히지 않는다.
- 제2조의3의 유찰, 비영리 참여 필요, 다른 법령상 우선구매·수의/지명계약, 특정 성능·기술·
  품질 등 명시 예외는 계속 0 조건이다.

dev labels는 위 source audit 뒤 결과 대조에만 사용했다. v14 positive 8건의 입찰추정가격은
237,781,818원부터 727,272,727원으로 모두 2억 3천만원 이상이다. exact-code product fact는
unknown 4, known non-match 3, conditional match 1이다. conditional match 1건은 organizer CSV의
`추정가격 3억원 미만` 조건에 대해 실제 가격이 327,272,727원이므로 해당 경쟁제품 조건을
충족하지 않는다. 공고 원문에는 중소기업 확인서가 실제 참가자격인 사례가 확인된다.

가설은 v14 하나에 정확한 2억 3천만원 operand, 물품·용역 범위, condition-aware product 대조와
제2조의3 예외를 압축한 card를 주면 Gemma가 현재의 보수적 all-zero를 벗어나며, item-only
attention control보다 TP/F1이 개선된다는 것이다.

## Controlled arms

### EXP257 — existing-card V/E control

- base: `configs/config.exp205-relation-checklist-after-source-fast-panel-c4.yaml`.
- allowed changes: `prompt.active_items`, `prompt.profile`, `prompt.mode`.
- exactly v14/e14만 판단하는 `complete_fact_subset_v1`, plain `baseline` specialist다.
- current v10 card, conditional exact-code product facts, human-readable metadata, organizer
  semantics, 모든 admitted original source, tokenizer admission, evidence validator, merge,
  postprocess와 provider parameters는 고정한다.

### EXP258 — corrected-card V/E treatment

- base: EXP257.
- sole allowed change: `prompt.decision_cards_path`.
- 새 card artifact는 v10 대비 v14 text만 변경한다.
- final v14/e14는 Gemma가 소유한다. Python은 가격·제품·예외로 label을 계산하지 않는다.

### EXP259 — corrected-card V-only treatment

- base: EXP258.
- sole allowed change: `prompt.output_mode: labels_and_evidence -> labels_only`.
- user input, card, documents, metadata/product facts, source admission과 model parameters는
  EXP258과 동일하다. system/output schema에서 evidence contract만 제거한다.
- label 성능을 우선 비교한다. V-only가 V/E보다 의미 있게 좋을 때만 source-grounded evidence
  복원을 별도 가설로 설계한다. 임의 키워드/법률 Python rule로 e14를 만들지 않는다.

## Gates

1. card structural diff, declared preflight, exact tokenizer dev200 coverage/provenance,
   short/attachment/overflow actual rendered review, active-v14 semantic contract, exact mock,
   49-column validation과 tests를 provider call 전에 완료한다.
2. fast20은 frozen `configs/dev_fast_panel_v1.json`만 쓴다. 여기에는 v14 positive 2건이 있다.
3. EXP258/259 중 하나가 EXP257보다 v14 TP/F1을 개선해야 한다. V/E와 V-only는 label
   TP/FP/FN을 우선하고 completion/call/runtime을 보조 지표로 기록한다.
4. frozen independent holdout20은 v14 positive가 0건임을 미리 확인했다. fast winner와 control을
   모두 실행하여 FP 비열화를 검사하고, sensitivity를 검증하지 못한다는 한계를 명시한다.
5. fast sensitivity 개선과 independent specificity 비열화를 함께 만족할 때만 dev200으로
   확장한다. 실패하면 v14 wording/schema를 dev 사례에 맞춰 반복 조정하지 않는다.

## Pre-provider gate

- `decision_cards_v16_v14_threshold.json`은 v10과 비교해 v14 하나만 다르며, 2억 3천만원,
  국가계약법 제4조제1항 selector, 물품·용역 범위, 별도 7억 1천만원 비적용, condition-aware
  product fact와 제2조의3 예외를 모두 포함한다.
- preflight는 EXP257에서 선언한 active-items/profile/mode 세 차이, EXP258에서 card path 하나,
  EXP259에서 output mode 하나만 검출했다.
- exact Gemma tokenizer dev200 complete-input audit는 세 arm 모두 200 records, 374/374 source
  documents, source/metadata/card/organizer-semantics omission 0, over-budget 0, 200 single-pass다.
  즉 item-only이므로 all-item base의 overflow가 사라지지만 문서는 줄이지 않는다.
- frozen fast20 admission은 세 arm 모두 20 single-pass calls다. 최대 prompt는 EXP257 29,253,
  EXP258 29,539, EXP259 29,465 tokens로 budget 30,268 이하다.
- short `PPS-DEV-062`, attachment `PPS-DEV-194`, longest `PPS-DEV-169`, 두 fast positive
  `PPS-DEV-049/051` actual rendered messages를 세 arm 모두 export하여 읽었다. 공고문과 존재하는
  규격서·과업지시서·제안요청서, v14 card, 입찰추정가격, 세부품명번호, friendly conditional
  product fact가 보존된다. raw metadata JSON/internal status/code array나 raw law text는 없다.
- EXP258과 EXP259의 다섯 user messages는 각각 byte-identical하다. system 차이는 V/E evidence
  지시와 JSON shape 제거뿐이다.
- active-v14 semantic-input contract는 세 arm·다섯 fixture에서 card, price metadata, CSV fact,
  actual source type을 모두 추적하여 PASS했다.
- exact mock은 각 arm 20 rows, 49 columns, unique IDs, parse error 0, validation PASS다.
- full tests: `227 passed`.

세 fast20 provider arm만 승인한다.

## Fast20 results and holdout choice

| arm | v14 TP/FP/FN | precision / recall / F1 | completion | runtime | EXP205 merged macro |
| --- | --- | --- | ---: | ---: | ---: |
| EXP257 existing-card V/E | `2/9/0` | `.1818 / 1.0 / .307692` | 1,521 | 22.1s | `.337821` |
| EXP258 corrected V/E | `2/0/0` | `1.0 / 1.0 / 1.0` | 779 | 20.7s | `.366667` |
| EXP259 corrected V-only | `2/0/0` | `1.0 / 1.0 / 1.0` | 180 | 20.6s | `.366667` |

- 세 arm 모두 parse error 0이다.
- 수정 card는 control의 TP 두 건을 모두 유지하면서 FP 9건을 전부 제거했다. 이는 단순
  item-only attention이 아니라 누락된 threshold/legal selector를 보완한 효과다.
- EXP258과 EXP259의 20개 v14 labels는 완전히 동일하다. V-only는 completion을 76.9%
  줄였지만 label gain은 없고 e14를 모두 잃었다. 따라서 quality 우선 동점 규칙으로 evidence를
  보존하는 EXP258 V/E를 holdout winner로 선택한다.
- EXP258 evidence validity `0.5`는 두 gold-positive의 organizer e14가 원래 공란이고 한
  prediction evidence만 exact substring으로 검증된 결과다. label 성능과 별개로 dev200에서
  evidence validity를 다시 측정해야 한다.

EXP260은 EXP257 existing-card V/E holdout control, EXP261은 EXP258 corrected-card V/E
holdout treatment다. frozen holdout에 v14 positive가 없으므로 `FP261 <= FP260`, parse/source
failure 0을 gate로 쓴다. 통과하면 V/E만 dev200으로 확대하며, V-only dev200은 fast label gain이
없으므로 실행하지 않는다.

### Holdout pre-provider gate

- EXP260/261 preflight controlled differences는 모두 `{}`다.
- 두 arm 모두 dev200 전수 complete-input audit에서 374/374 documents, omission/over-budget 0,
  200/200 single-pass다. holdout20 역시 20/20 single-pass다.
- short `PPS-DEV-068`, attachment `PPS-DEV-27`, longest attachment `PPS-DEV-082` actual
  rendered messages를 읽었다. 존재하는 공고문·규격서·과업지시서·제안요청서가 모두 있고,
  EXP261에는 2억 3천만원 operand와 같은 metadata/product facts가 유지된다.
- active-v14 semantic contract는 두 arm 모두 세 fixture에서 PASS했다.
- exact mock은 두 arm 모두 20 rows/49 columns/unique IDs, parse error 0, validation PASS다.

EXP260/261 holdout provider run만 승인한다.

## Holdout20 result and dev200 promotion

- EXP260 existing-card control: `TP 0 / FP 12 / FN 0`, evidence validity `.833333`,
  parse error 0, completion 1,768 tokens, runtime 22.0초.
- EXP261 corrected-card treatment: `TP 0 / FP 0 / FN 0`, parse error 0,
  completion 762 tokens, runtime 21.1초.
- 양쪽 모두 exact output validation을 통과했다.

따라서 수정 card는 fast에서 TP 2를 모두 유지하며 FP 9를 제거했고, independent negative-only
holdout에서도 FP를 `12 -> 0`으로 줄였다. 사전 gate를 통과했으므로 policy-identical EXP262
dev200 confirmation을 승인한다. 이 승격은 holdout sensitivity 증거가 아니라 fast sensitivity와
holdout specificity의 결합임을 유지한다.

EXP262는 EXP261을 base로 하고 `allowed_policy_changes: []`이며, dev200 전체를 선택하는 data
cohort/output path 외 prompt·schema·card·source·model·merge policy 차이는 없다. 완료 후 v14 raw
TP/FP/FN, evidence validity, parse errors, calls/tokens/runtime를 기록하고, EXP208+EXP221+EXP231
현재 최고 composition에 v14/e14만 field replacement하여 전체 macro를 계산한다.

## EXP262 dev200 result

- exact topology: 200 records × one pass = 200 calls, 374/374 documents.
- v14: `TP 5 / FP 4 / FN 3`, precision `.555556`, recall `.625`, F1 `.588235`.
- evidence validity `.888889`; `PPS-DEV-051` 한 positive는 생성 evidence가 source substring
  검증을 통과하지 않아 blank 처리됐다. parse error 0, output validation PASS.
- prompt/completion tokens: `2,448,875 / 7,490`; OpenRouter wall time 201.3초.
- 현재 최고 EXP208 + EXP221(v4) + EXP231(v5) composition에 v14/e14만 field replacement한
  macro는 **`.329265 -> .353775`**다. non-v14 field는 변경하지 않았다.

fast F1 1.0보다는 낮지만 independent specificity와 dev200 양성 recall이 모두 확인되어 v14
specialist는 local-quality incumbent에 포함한다. 이는 submission runtime 승격과 별개다. 현재
구조를 그대로 제출하면 base 219 + v4 200 + v5 200 + v14 200 = 약 819 calls이므로 evaluator
제한에는 부적합하다.

dev200 error는 TP 5, FN 3(`DEV17/47/54`), FP 4(`DEV05/07/150/182`)다. FP 중 DEV07은 최종
evidence가 신용정보업 허가 문구여서 중소기업 참가제한이라는 truth condition과 맞지 않는다.
따라서 남은 오류를 Python phrase rule로 고치지 않고, 다음 실험은 수정 v14 card를 all-item
relation generation에 넣었을 때 target recovery가 유지되는지만 별도로 본다.
