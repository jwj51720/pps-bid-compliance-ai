# EXP263 — corrected v14 card in the all-item relation policy

작성: 2026-09-15, dev / mac

## Hypothesis

EXP262 v14-only V/E는 dev200 v14 F1을 `0 -> .588235`로 회복했지만 200 calls가 추가된다.
EXP263은 누락된 2억 3천만원 operand와 법정 selector가 all-item relation-checklist 안에서도
v14 판단을 움직이는지 분리한다. 성공하면 EXP208과 같은 약 219-call topology에서 v14 회복을
얻어 specialist 200 calls를 제거할 수 있다.

## Controlled policy

- base: `configs/config.exp205-relation-checklist-after-source-fast-panel-c4.yaml`.
- sole allowed change: `prompt.decision_cards_path` from v10 to v16.
- v16 artifact는 v10 대비 v14 text만 다르다.
- 24 active items, V/E schema, relation checklist, human-readable metadata, conditional exact-code
  product facts, organizer semantics, all admitted original sources, tokenizer budget, overflow merge,
  frozen postprocess와 provider parameters는 고정한다.
- Python threshold/label rule, specialist replacement, V-only, extra pass를 사용하지 않는다.

## Gates

유료 실행 전에 card diff/preflight, exact dev200 source coverage, short/attachment/overflow rendered
review, 24/24 semantic contract, exact mock와 tests를 완료한다. fast20에서 EXP205의 v14
`TP 0 / FP 0 / FN 2`를 개선하고 전체 macro가 악화되지 않아야 holdout으로 간다. holdout에는
v14 positive가 없으므로 전체 macro와 v14 FP 비열화를 본다. 두 방향이 유지될 때만 dev200을
실행한다. 실패하면 all-item wording을 재튜닝하지 않고 specialist 결과만 보존한다.

## Pre-provider gate

- `scripts/preflight_experiment.py`는 base EXP205 대비 선언된
  `prompt.decision_cards_path` 하나만 검출했다. v16 card artifact의 구조 비교도 v10 대비
  `v14` text 하나만 다름을 확인했다.
- exact Gemma tokenizer로 dev200 전체를 재구성한
  `outputs/exp263-preflight/complete_admission.json`은 200 records, 374 source documents,
  source omission 0, metadata omission 0, missing active card 0, organizer-semantics omission 0,
  over-budget pack 0이다. pass 분포는 `182 x 1 + 15 x 2 + 3 x 3 = 221 calls`다.
- frozen fast20의 exact admission은 `17 x 1 + 2 x 2 + 1 x 3 = 24 calls`다.
- short complete `PPS-DEV-062`, attachment `PPS-DEV-194`, overflow `PPS-DEV-169`의 실제
  system/user messages를 `outputs/exp263-preflight/`에 export하여 읽었다. 수정 v14 card의
  2억 3천만원 operand, 필요한 human-readable metadata와 condition-aware product fact,
  존재하는 공고문·규격서·제안요청서 원문이 보존되며 raw metadata JSON/internal status/code
  array와 raw law text는 없다. overflow 공고의 두 원문도 admitted pack 전체에서 확인했다.
- candidate semantic-input audit는 위 세 fixture의 v1-v24 모두 PASS다. 각 item의 card,
  metadata/CSV fact와 요구 source document type이 final rendered messages에 추적되며 policy
  failure는 0이다.
- exact staged mock은 frozen fast20 20 rows, 49 ordered columns, unique IDs, parse error 0,
  evidence/CSV validation PASS다. full tests는 `227 passed`다.

따라서 EXP263 fast20 provider call만 승인한다.

## Fast20 result

- EXP263 macro positive-F1: `.298611` (EXP205 control `.325000`, `-.026389`).
- v14: `TP 0 / FP 0 / FN 2`, F1 `0`; EXP205와 완전히 동일한 all-zero다.
- parse error 0, output validation PASS, evidence validity `.90`; evidence warning은 2건이다.
- exact topology는 24 calls이며 prompt/completion tokens는 `382,003 / 16,067`, OpenRouter wall
  time은 49.9초다.
- 비대상 항목도 생성 변동이 있었다. v15와 v19는 회복했지만 v1·v8·v12·v13·v17·v22·v23
  등이 악화되었고, 유일한 declared semantic change인 v14에는 아무 효과가 없었다.

수정 v14 card가 v14-only EXP258/261/262에서는 sensitivity와 specificity를 모두 개선했지만,
같은 card를 24-item response에 넣으면 fast 양성 두 건을 전혀 회복하지 못했다. 이는 operand가
다시 누락된 문제가 아니라 all-item attention/output competition 아래에서 v14 truth condition이
사용되지 않은 결과다. 사전 gate에 따라 EXP263은 기각하고 holdout/dev200으로 확대하지 않는다.
v14-only V/E specialist가 local-quality incumbent로 남으며, 이 200-call 비용을 없애려면 단순
card-path 통합이 아닌 call topology 자체의 새로운 압축 가설이 필요하다.
