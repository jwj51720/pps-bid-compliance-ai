# EXP264–266 — v6 missing threshold operand and V/E versus V-only

작성: 2026-09-15, dev / mac

## Source audit and hypothesis

v6은 `고시금액 미만 지역제한 시·군·구`인데 v10 card는 숫자 operand 없이
`고시금액 미만인지`만 요구한다. 이는 tokenizer나 source-document 누락이 아니라 final semantic
input의 법적 비교 기준 누락이다.

organizer 항목표는 v6을 국가계약 시행규칙 제25조, 지방계약 시행규칙 제25조와 지방 수의계약
운영요령에 연결한다. organizer 법령 원문에서 국가 물품·용역 고시금액은 2억 3천만원이고,
공기업·준정부기관의 별도 selector는 7억 1천만원이다. 지방계약 시행규칙의 일반 물품·용역
기준은 적용 지방자치단체 범위에 따라 행정안전부 고시금액 또는 5억원이며, 제한입찰의 본점
소재지 범위는 원칙적으로 시·도다. 국가·지방 모두 현장·납품지가 걸치거나 적격업체가 적은
명시 상황에 인접 시·도 확대를 허용한다. 별도의 2인 이상 견적 수의계약은 요건 충족 시
시·군 단위 제한을 허용할 수 있으므로 계속 0 조건으로 둔다.

source audit 뒤 dev labels를 대조했다. v6 양성은 국가 1건 96,521,864원과 지방 5건
34,545,455원–427,272,727원이며 모두 해당 비교구간 아래다. 기존 범위 교정 이후에도 best
all-item은 fast v6 양성 1건을 전부 놓쳤다. 가설은 v6 하나에 숫자 selector와 비교 필드를
명시하면 item-only Gemma가 all-zero를 벗어난다는 것이다.

## Controlled arms

- EXP264: 기존 v10 card, v6/e6만 판단하는 V/E attention control.
- EXP265: EXP264와 같은 입력·schema에서 card path만 v17로 바꾼 V/E treatment. v17은 v10
  대비 v6 text 하나만 다르다.
- EXP266: EXP265와 user input이 같고 output contract만 labels-only인 V-only treatment.
- 세 arm 모두 human-readable metadata, 조건부 exact-code product fact, 모든 admitted 원문,
  exact tokenizer budget/overflow, merge, frozen postprocess와 provider parameters를 유지한다.
  Python 금액·지역·법률 label rule은 없다.

## Gates

유료 실행 전에 declared preflight, card structural diff, dev200 exact source coverage/provenance,
short/attachment/overflow rendered review, v6 semantic-input contract, exact mock와 full tests를
완료한다. frozen fast20에는 v6 양성 1건이 있다. EXP265/266 중 하나가 EXP264보다 v6 TP/F1을
개선해야 frozen independent holdout20으로 간다. holdout에는 v6 양성이 없으므로 winner와
control의 FP를 비교하고, specificity 비열화가 없을 때만 dev200으로 확장한다. V-only는 label
성능이 V/E보다 실제로 나을 때만 evidence recovery 후속 가설의 후보가 된다. 동률이면 source
evidence를 보존하는 V/E를 선택한다.

## Pre-provider gate

- v17 artifact는 v10 대비 v6 text 하나만 다르며 2억 3천만원·7억 1천만원·5억원 selector,
  입찰추정가격 비교, 시·도 원칙과 2인 이상 견적 수의계약 예외를 포함한다. regression test로
  이 경계를 고정했다.
- preflight는 EXP264에서 active-items/profile/mode, EXP265에서 card path, EXP266에서 output
  mode만 각각 검출했다.
- exact Gemma tokenizer dev200 audit는 세 arm 모두 200 records, 374/374 documents, source·
  metadata·card·organizer-semantics omission 0, over-budget 0, 200 single-pass calls다.
- frozen fast20도 세 arm 모두 20 single-pass calls다. 최대 prompt는 EXP264 29,222,
  EXP265 29,449, EXP266 29,375 tokens로 budget 30,268 이하다.
- short `PPS-DEV-062`, attachment `PPS-DEV-194`, long `PPS-DEV-169`, v6 fast positive
  `PPS-DEV-072`의 실제 rendered messages를 세 arm에서 export하고 읽었다. 필요한 card,
  계약법·소관구분·업무구분·계약방법·낙찰방법·입찰추정가격 metadata, organizer semantics와
  존재하는 공고문·규격서·제안요청서가 모두 있다. raw metadata JSON/internal status/code
  array나 raw law text는 없다.
- active-v6 semantic-input contract는 세 arm·네 fixture에서 PASS했다.
- EXP265/266의 20개 user messages hash는 모두
  `9251d14bc33ad655b5fcfbde85cfa3b3e86ff25b6a753b07cdbcc3cde2bc156f`로 동일하다.
  차이는 V/E와 V-only system/output schema뿐이다.
- exact mock은 각 arm 20 rows, 49 columns, unique IDs, parse error 0, validation PASS다.
- full tests: `228 passed`.

세 fast20 provider arm만 승인한다.

## Fast20 result

| arm | v6 TP/FP/FN | F1 | completion | runtime |
| --- | --- | ---: | ---: | ---: |
| EXP264 existing-card V/E | `0/0/1` | `0` | 856 | 20.5s |
| EXP265 corrected-card V/E | `0/0/1` | `0` | 829 | 20.5s |
| EXP266 corrected-card V-only | `0/0/1` | `0` | 160 | 20.4s |

- 세 arm 모두 parse error 0, validation PASS이며 20 calls다.
- EXP265와 EXP266의 20개 v6 labels는 완전히 동일한 all-zero다. V-only는 EXP265 대비
  completion을 80.7% 줄였지만 label gain은 없고 evidence를 잃었다.
- fast positive `PPS-DEV-072`에서 두 V/E arm은 실제 참가자격 문장인 `본점 소재지를 ...
  [지역:r1|단위=기초|광역=경기도] 또는 제주도`를 정확히 생성했으나 `위반여부: 0`으로
  판정했다. 즉 source navigation과 threshold operand는 확보됐지만, 한 조항 안의 기초지역
  제한과 광역지역 추가를 v6/v7 관계로 분해하지 못했다.

사전 gate에 따라 세 arm 모두 기각하고 holdout/dev200으로 확대하지 않는다. 다음 v6 후보가
있다면 범용 category extraction이나 카드 재문구가 아니라, `참가자격 대상 지역들 → 각 지역
단위 → 현장/납품지 기준 지역 → 계약상 허용 특례`의 관계를 source-only로 구조화한 가장 작은
v6 사실 검토여야 한다. final은 그 facts를 자동 신뢰하지 않고 card·metadata·모든 원문과 다시
대조해야 한다.
