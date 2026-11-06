# EXP253/254 — v13 product applicability and bidder-scope specialist

작성: 2026-09-15, dev / mac

## Source audit and smallest-item justification

현재 최고 EXP231 composition에서 v13은 `TP 0 / FP 4 / FN 6`, F1 0이다. organizer 항목표,
법령 ledger와 공개 운영 해석의 공통 truth condition은 다음 관계다.

1. 실제 구매대상이 organizer CSV의 중소기업자간 경쟁제품이며 행의 `특이사항` 조건을 충족한다.
2. 실제 참가자격이 소기업·소상공인 등을 중심으로 제한되어 일반 중기업을 배제한다.
3. 소액수의 또는 별도 명시적 허용 사유가 없다.

dev200 gold positive 6건의 organizer-only product fact를 다시 계산하면 exact document-code
matched 4건, unknown 2건이다. matched 사례는 통학운송서비스, 조건부 기타행사기획및대행서비스,
조건부 축제기획및대행서비스, 디자인서비스이고 source doc-id/type provenance가 보존된다.
원문에는 제품 코드/직접생산 요건과 기업규모 참가제한이 서로 인접하거나 다른 문서에 존재한다.

기존 7-category inventory는 제품/기업/직접생산을 한 범주에 문자열로 모으고, relation checklist는
일반적으로 제품 적용조건과 참가자격 역할을 재확인할 뿐 `제품 행 조건 → 일반 중기업 참가 가능성
→ 예외`의 상태를 별도 관찰하지 않는다. EXP208은 네 FP에서 소기업 문구를 찾았지만 제품
`not_matched` 3건까지 v13으로 판정했고, six positives는 모두 놓쳤다. 따라서 v13 하나에서만
관계형 observable schema를 시험할 근거가 있다.

## EXP253 matched specialist baseline

구조화 schema의 효과와 item attention/full catalog 효과를 섞지 않기 위해 먼저 v13-only V/E
baseline을 만든다.

- base: `configs/config.exp205-relation-checklist-after-source-fast-panel-c4.yaml`.
- allowed changes: `prompt.active_items`, `prompt.profile`, `prompt.mode`,
  `prompt.competition_product_context_mode`.
- active item은 v13 하나, profile은 `complete_fact_subset_v1`, mode는 plain `baseline`, product
  context는 `full_catalog_v1`이다.
- v13/e13만 model-owned field replacement로 EXP205와 비교한다. Python label rule/OR/majority는
  없다.
- cards, metadata, organizer semantics, 모든 admitted source, provider parameters,
  evidence substring validation과 postprocess는 고정한다.

EXP253은 treatment control을 만드는 진단이다. v13 F1이 0이어도 EXP254의 matched base로 쓴다.

## EXP254 structured V/E treatment

- base: EXP253.
- sole allowed change: `prompt.mode: baseline -> v13_product_scope_review_v1`.
- 같은 응답에서 판정보다 먼저 다음 observable fields를 출력한다.
  - 실제구매대상
  - 고시후보세부품명
  - 적용조건상태
  - 경쟁제품적용
  - 기업제한원문: 실제 참가자격 제한을 보여 주는 500자 이하 unchanged source substring
  - 기업제한역할: 참가자격/평가우대/서류안내/없음/불명
  - 일반중기업참가: 가능/불가/불명
  - 허용사유: 소액수의/기타명시/없음/불명
  - 카드대조: 1조건충족/0조건충족/판단불가
- final v13/e13은 review로 Python 계산하지 않고 Gemma가 card, metadata, catalog와 모든 원문을
  다시 대조해 소유한다. e13은 기존 exact substring validator를 그대로 적용한다.

## Paid-run 전 gate

각 arm에 대해 다음을 완료한다.

1. base config와 allowed changes의 preflight.
2. exact Gemma tokenizer dev200 source coverage/provenance, fixed inputs, over-budget와 call topology.
3. short complete, attachment, overflow/long notice의 actual rendered system/user messages human review.
4. active-v13 applicability, 1/0 condition, 모든 source type, metadata/product CSV fact semantic contract.
5. exact mock, structured parser/malformed recovery, review source substring validation,
   49 columns/unique IDs/evidence validation.

## 승격과 중단

- fast20은 `configs/dev_fast_panel_v1.json`만 사용한다.
- EXP254가 EXP253보다 v13 TP/F1을 개선하고 parse/source failure가 없어야 policy-identical
  independent holdout으로 간다. EXP205 merge macro도 함께 기록한다.
- FP만 줄이고 TP 0이면 관계형 truth condition 실행 성공으로 보지 않는다.
- holdout에서도 TP/F1 방향이 유지된 뒤에만 dev200으로 확장한다.
- 실패 시 enum/문구를 fast label에 맞춰 반복 조정하거나 다른 v10–v18로 일반화하지 않는다.
- full catalog가 runtime을 키우므로 local quality와 submission 승격은 별도 판단한다.

## Pre-provider gate — 2026-09-15

- source audit는 gold v13 positives 6건 중 organizer exact document-code matched 4건,
  unknown 2건을 재확인했다. 감사 중 JSON payload 전체를 product mapping으로 잘못 넘겨 일시적으로
  6 unknown이 나온 분석 오류가 있었으나, 실제 pipeline의 `load_competition_product_index()`와
  동일한 mapping으로 재실행해 바로잡았다. runtime lookup 결함은 아니다.
- preflight:
  - EXP253은 선언된 active_items/profile/mode/product-context 네 변경만 검출했다.
  - EXP254는 EXP253 대비 `prompt.mode` 하나만 검출했다.
- exact Gemma tokenizer dev200 admission:
  - EXP253: 168×1 + 16×2 + 16×3 = 248 calls.
  - EXP254: 164×1 + 19×2 + 17×3 = 253 calls.
  - 두 arm 모두 374/374 source documents, metadata/card/product/organizer-semantics omission 0,
    over-budget 0이다.
- short `PPS-DEV-062`, attachment `PPS-DEV-194`, overflow `PPS-DEV-169`의 두 arm actual
  rendered messages를 `outputs/exp253-preflight/`, `outputs/exp254-preflight/`에서 읽었다.
  full catalog는 human-readable name/condition만 포함하고 internal status/code 배열을 노출하지
  않는다. source 자체의 제품 코드는 원문 provenance로 유지된다. EXP254 review는 모든 원문 뒤에
  있고 169의 세 source packs 모두 card/catalog/metadata와 final review instruction을 유지한다.
- active-v13 semantic-input audit는 두 arm의 세 fixtures에서 모두 pass했다.
- 최초 EXP254 mock은 generic MockClient가 새 nested schema를 잘못 채워 27 parse errors를 냈다.
  유료 실행을 중단하고 v13 schema-aware mock payload와 regression test를 추가했다. corrected exact
  mock은 20/20, 27 context reviews, parse error 0, 49 columns/unique IDs/evidence validation PASS다.
  EXP253 mock도 validation PASS다. targeted tests는 105 passed다.

두 arm의 실제 가설 구성요소가 구현·선택됐고 source/schema/mock gate가 모두 통과했다.
EXP253과 EXP254 fast20 provider runs만 승인한다.

## Fast20 결과와 independent-holdout gate — 2026-09-15

고정 fast20 provider 결과는 다음과 같다.

- EXP253 plain v13-only V/E: `TP 0 / FP 8 / FN 1`, precision `0`, recall `0`,
  v13 F1 `0`. EXP205 field replacement macro는 `0.325000`이다.
- EXP254 relation review V/E: `TP 1 / FP 10 / FN 0`, precision `0.090909`, recall `1.0`,
  v13 F1 `0.166667`. EXP205 field replacement macro는 `0.331944`이다.
- 두 arm 모두 parse error `0`이다. EXP254는 27 source-pack review를 보존했고, 최종 positive
  11건 중 evidence validity는 `0.727273`이었다. invalid evidence는 기존 validator에 의해 빈
  문자열로 정리됐으며 label override는 없었다.

따라서 EXP254는 사전 선언한 fast TP/F1 gate를 통과했다. 그러나 precision은 낮아 이 결과만으로
dev200 승격을 주장하지 않는다.

고정 `dev_prompt_holdout_v1`의 정답 분포를 실행 전에 감사한 결과 v13 positive가 20건 중
`0`건이다. 그러므로 이 cohort에서 TP/recall/F1 유지 여부를 측정하는 것은 논리적으로 불가능하다.
이 한계를 사후에 숨기거나 다른 label-selected cohort를 independent holdout이라고 부르지 않는다.
대신 다음의 비대칭 specificity gate를 provider 실행 전에 선언한다.

1. EXP253과 EXP254를 각각 policy-identical holdout20으로 실행한다.
2. parse/source/evidence contract failure가 없어야 한다.
3. EXP254의 false-positive 수가 EXP253보다 증가하지 않아야 한다.
4. fast20의 sensitivity 개선과 independent holdout20의 specificity 비열화를 함께 만족할 때만
   dev200 confirmation으로 간다. 이 경우에도 holdout이 sensitivity를 검증했다는 표현은 금지한다.

EXP255는 EXP253의 holdout control, EXP256은 EXP254의 holdout treatment다. 두 config의 유일한
effective 차이는 frozen cohort/output path이며 prompt, schema, cards, source admission, model
parameters와 merge policy는 각 fast parent와 동일하다.

### Holdout pre-provider gate

- preflight controlled differences는 EXP255/256 모두 `{}`다.
- exact Gemma tokenizer admission:
  - EXP255: 17×1 + 1×2 + 2×3 = 25 calls.
  - EXP256: 16×1 + 2×2 + 2×3 = 26 calls.
  - 두 arm 모두 holdout 20건의 공고문과 존재하는 규격서·과업지시서·제안요청서를 전부
    admitted pack에 포함한다. over-budget call은 없다.
- short `PPS-DEV-068`, attachment/two-pack `PPS-DEV-27`, attachment/three-pack
  `PPS-DEV-082`의 actual messages를 각각 `outputs/exp255-preflight/`와
  `outputs/exp256-preflight/`에 export하여 읽었다. 카드, 세부품명번호 human-readable metadata,
  full product catalog의 이름/조건, 각 pack의 실제 원문이 유지된다. EXP256은 각 원문 pack 뒤에
  v13 관계 review와 final v13/e13 지시가 있으며 raw internal status/code array는 없다.
- candidate semantic-input audit는 두 arm 모두 v13 card/CSV/metadata와 세 fixture의 실제 source
  type 전부를 추적하여 PASS했다. audit은 label/prediction을 읽지 않았다.
- exact mock은 양쪽 모두 20 rows, 49 columns, unique IDs, parse error 0, validation PASS다.
  EXP256은 26개 admitted context에 대해 26개 structured review를 만들었다. `errors.csv`의 13개
  행은 active item이 아닌 항목을 mock이 0으로 둔 평가 차이이며 schema/admission failure가 아니다.
- 전체 test suite: `226 passed`.

EXP255와 EXP256 holdout20 provider runs만 승인한다.

## Holdout20 결과와 결론

- EXP255 plain control: `TP 0 / FP 13 / FN 0`, predicted positive 13, evidence validity
  `0.846154`, parse error 0, runtime 25.8초.
- EXP256 structured treatment: `TP 0 / FP 14 / FN 0`, predicted positive 14, evidence validity
  `0.928571`, parse error 0, 26 structured reviews, runtime 34.6초.
- 두 출력 모두 20 rows/49 columns/unique IDs validation을 통과했다.

EXP256은 사전 선언한 independent specificity gate(`FP_treatment <= FP_control`)를
`14 > 13`으로 실패했다. fast20에서는 유일한 v13 양성을 회복했지만, independent negatives에서
false positive를 줄이지 못했고 오히려 하나 늘렸다. 따라서 dev200을 실행하지 않으며 canonical
또는 submission policy로 승격하지 않는다.

구조화 출력 자체는 malformed를 만들지 않았지만, 모델은 review의 `경쟁제품적용`,
`일반중기업참가`, `카드대조`가 서로 충돌하는 경우에도 최종 1을 자주 냈다. 이는 누락된 입력을
추가하면 자동으로 해결되는 문제가 아니라 Gemma가 긴 full catalog와 원문에서 관찰값과 최종
논리를 일관되게 결합하지 못하는 오류다. review를 Python label rule로 바꾸거나 enum/문구를
fast label에 맞춰 재튜닝하지 않는다. v13 관계 schema는 이 실험으로 종료한다.
