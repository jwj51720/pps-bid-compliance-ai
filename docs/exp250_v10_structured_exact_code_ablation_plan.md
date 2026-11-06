# EXP250 — v10 structured V-only with exact-code product facts

작성: 2026-09-15, dev / mac

## 배경과 가설

EXP247/248의 구조화 V-only review는 fast와 independent holdout에서 v10의 zero recall을
회복했고, EXP249 dev200에서도 v10 F1 `.103896`로 방향이 유지됐다. 그러나 EXP249는 전체
organizer product catalog 약 8.9k Gemma tokens를 모든 pass에 반복해 252 calls,
5.28M prompt tokens와 심한 반복 출력을 만들었으며 precision은 `.057143`에 그쳤다.

아직 개선 원인이 다음 중 무엇인지 분리되지 않았다.

1. `실제구매대상 → 제품 적용성 → 공고 전체 직접생산 요구 존재 → final v10`을 명시한
   구조화 review 자체.
2. exact-code가 unknown일 때도 후보를 찾게 하는 전체 product catalog.

EXP250의 최소 가설은 **구조화 review 자체가 핵심이라면**, 전체 catalog를 제거하고 기존
exact-code 기반 human-readable 제품 사실만 제공해도 EXP244의 all-zero v10보다 개선된다는
것이다. 반대로 fast positives가 다시 모두 사라지면 전체 catalog 또는 다른 organizer-grounded
제품 매핑이 recall에 필요하다는 뜻이다.

## Base와 유일한 정책 변경

- base: `configs/config.exp247-v10-product-presence-review-fast-panel-c4.yaml`.
- `experiment.allowed_policy_changes`:
  `[prompt.competition_product_context_mode]`.
- `prompt.competition_product_context_mode`만 `full_catalog_v1`에서
  `conditions_and_provenance_v2`로 되돌린다.
- v10-only, V-only output, `v10_product_presence_review_v1` schema/prompt, v10 card,
  exact-code lookup artifact, metadata, organizer semantics, 모든 admitted source, merge,
  postprocess, provider parameter는 고정한다.
- Python은 label을 계산·교정하지 않고 schema parse, optional source substring 검증,
  source/doc-id 연결과 병합만 수행한다.

## Paid-run 전 gate

1. preflight가 선언된 product-context mode 차이 하나만 보고해야 한다.
2. exact tokenizer admission으로 374/374 source coverage, fixed-input completeness,
   omission/over-budget 0과 call topology를 기록한다.
3. short complete `PPS-DEV-062`, attachment `PPS-DEV-194`, overflow `PPS-DEV-169`의 실제
   rendered system/user messages를 내보내 사람이 읽는다.
4. active v10 semantic-input contract에서 적용 전제, 1 조건, 핵심 0 조건, 모든 source type,
   organizer product fact가 실제 span으로 존재하는지 확인한다.
5. 동일 config exact mock에서 20/20 rows, parse recovery, 49 columns, unique IDs와 evidence
   validation을 확인한다.

## 승격·중단 기준

- fast20은 `configs/dev_fast_panel_v1.json`만 사용한다.
- EXP244 exact-code V-only `TP 0 / FP 0 / FN 2`, F1 0보다 v10 F1과 TP가 개선되고
  parse/source failure가 없어야 policy-identical independent holdout으로 간다.
- EXP247 full-catalog structured result `TP 2 / FP 5 / FN 0`, F1 `.444444`와 함께 precision,
  recall, calls, tokens, latency를 비교한다.
- fast에서 TP가 0이면 wording/schema를 dev에 맞춰 수정하지 않고 ablation을 기각한다.
- fast가 통과해도 independent holdout에서 방향이 재현된 뒤에만 dev200으로 확장한다.
- 이 실험은 구조화 V-only와 catalog의 인과 분리를 위한 진단이다. 통과하더라도 현재 최고
  all-item + v4/v5 composition에 추가하는 runtime-safe submission 구조는 별도로 검증한다.

## Pre-provider gate — 2026-09-15

- preflight는 EXP247 대비 선언된
  `prompt.competition_product_context_mode: full_catalog_v1 -> conditions_and_provenance_v2`
  하나만 검출했다.
- 최초 rendered review에서 전체 catalog가 없는 후보인데도 system이 “대회 제공 전체 목록”에서
  후보를 고르라고 지시하는 의미 계약 불일치를 발견했다. 유료 실행 전에 renderer가 product
  context mode를 받아 exact-code 후보에서는 “제공된 exact-code 확인 결과만 사용하고 제공되지
  않은 전체 목록을 추정하지 않는다”고 쓰도록 수정하고 regression test를 추가했다. full-catalog
  mode의 historical wording은 그대로 보존한다.
- exact Gemma tokenizer dev200 admission은 374/374 source documents, metadata/card/product/
  organizer-semantics omission 0, over-budget 0이다. catalog 제거로 topology는 EXP249의
  252 calls에서 `199×1 + 1×2 = 201 calls`로 감소했다. 유일한 overflow는 `PPS-DEV-11`이며
  두 pass가 공고문+과업지시서 / 제안요청서를 나눠 모두 보존한다.
- short `PPS-DEV-062`, attachment `PPS-DEV-194`, overflow `PPS-DEV-11`의 exact rendered
  messages를 `outputs/exp250-preflight/`에서 읽었다. 세 메시지 모두 카드, 필요한 metadata,
  exact-code 제품 조회의 한계 설명, 실제 원문, 원문 뒤 구조화 review 순서를 보존한다.
  제공되지 않은 전체 catalog나 raw status/code 배열은 노출하지 않는다.
- candidate semantic-input audit는 v10 applicability, 1/0 condition, `세부품명번호목록`,
  organizer CSV fact, 각 fixture의 모든 source type에 대해 통과했다.
- exact mock은 fast20 20/20, 20 calls, parse error 0, 49 columns/unique IDs/evidence validation
  PASS다. 관련 pipeline tests는 101 passed다.

이번 가설에 필요한 구조화 V-only, exact-code product facts, 모든 admitted source와 source-wide
absence check가 모두 구현·선택됐고, full catalog만 제거됐음을 확인했다. EXP250 fast20
provider run을 승인한다.

## Fast20 결과와 결정

- provider run은 20 records / 20 calls, 21.8초, prompt/completion
  `263,281/2,830` tokens, parse error 0이었다.
- v10은 `TP 0 / FP 0 / FN 2`, F1 0으로 EXP244 exact-code V-only와 같은 all-zero 결과로
  돌아갔다. EXP247 full-catalog structured의 `TP 2 / FP 5 / FN 0`, F1 `.444444`를 재현하지
  못했다.
- 두 gold positive `PPS-DEV-062`, `PPS-DEV-069` 모두 exact-code 조회가 unknown이고, review는
  실제 행사대행 구매대상을 찾았지만 고시후보를 null, 경쟁제품 적용을 비적용으로 기록했다.
- catalog 제거는 dev200 projected topology를 252 -> 201 calls로 줄이고 반복 장문 출력을
  없앴지만, 성능 gate를 실패했다.

결정: holdout/dev200으로 확장하지 않는다. v10의 알려진 positives를 회복하려면 현재 organizer
input만으로는 full catalog와 같은 organizer-grounded name/condition mapping이 필요하다. 다음
실험은 catalog를 유지하고 두 번째 독립 V-only final owner가 첫 판정의 과잉 positive를 줄일 수
있는지 검증한다. Python consistency/label rule은 사용하지 않는다.
