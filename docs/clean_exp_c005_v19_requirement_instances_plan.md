# EXP-C005 v19 requirement-instance observation/reducer 계획

작성일: 2026-09-21  
상태: C005R로 fast20 PASS, independent holdout20 승인

## 1. 기준선과 단일 변경 범위

품질 기준선은 C004S composition이다.

- base manifest: `experiments/manifests/clean_exp_c004s_v3_basis_reducer_replay_v2.json`
- base output: `outputs/clean-exp-c004s-v3-basis-reducer-replay-v2/`
- dev200 Macro positive-F1: `0.8037378356650803`
- v19: TP 5 / FP 10 / FN 1 / F1 `0.4761904762`
- final owner 변경: v19/e19만 허용
- v1-v18, v20-v24는 C004S와 cell 단위로 완전히 같아야 한다.

이 실험은 frozen L41의 B19 출력을 직접 수정하거나 legacy 코드를 재사용하지 않는다. 새 구현은
`src/pps_ai/views/`, `src/pps_ai/decisions/`와 clean runner에만 둔다. Hash-pinned L41 artifact는
비교 기준 행과 다른 23개 항목을 읽는 격리 loader로만 사용한다.

## 2. 왜 v19가 다음인가: 수학적 우선순위

다른 23개 항목을 고정하면

```text
F1 = 2TP / (2TP + FP + FN)
DeltaMacro = (F1_new - F1_base) / 24
```

현재 저성능 항목의 완전교정 상한은 다음과 같다.

| item | 현재 F1 | 완전교정 DeltaMacro | 현재 판단 |
| --- | ---: | ---: | --- |
| v24 | .175439 | .034357 | operational truth가 불명확하여 추가 paid run 중단 |
| v9 | .428571 | .023810 | 고정 fast 양성의 source-gold 정합성 미확인 |
| v19 | .476190 | .021825 | 11개 오류가 동일 requirement 관계식으로 감사 가능 |
| v4 | .533333 | .019444 | 구조화/독립 verifier의 holdout 일반화 실패 이력 |
| v17 | .631579 | .015351 | 아직 최소 truth-condition 진단 없음 |

단순 상한이 아니라 `검증 가능한 회수량`을 기준으로 v19를 선택한다. v19에서 FN 1건을 회수하고
FP 4건만 제거하면 TP/FP/FN은 `6/6/0`, F1은 `.666667`, DeltaMacro는 `.007937`이다. 오류 감사에서
명확히 분리되는 FP 7건을 제거하면 `6/3/0`, F1 `.800000`, DeltaMacro `.013492`다. 완전교정 상한은
`.021825`다. v9의 상한은 더 크지만 source가 입증되지 않은 positive를 목표로 최적화할 수 없고,
v4의 기존 구조 실험은 out-of-panel 개선을 입증하지 못했다.

## 3. 확인된 결함

L41 B19는 하나의 대표 요구를 8개 `h` 선택지로 압축한 뒤 final `y`를 같은 Gemma 응답에서
출력한다. dev200 오류는 FN 한 건이 `h=7`이고 FP 열 건이 모두 `h=1,y=1`이다. 즉 parse나 evidence
문제가 아니라 관계 압축의 오판이다.

Organizer 항목표와 기존 compact card가 요구하는 경계는 다음과 같다.

- 대상: 외부 제조사·공급사·기술지원사의 물품공급 또는 기술지원 이행보장 서류
- 1: 입찰서/제안서 제출 전에 발급·보유하거나 입찰/제안 제출과 함께 의무 제출
- 0: 단순 목록, `제출 가능한 업체`, 시점 없는 언급, 낙찰·계약 후에만 제출
- 0: 제조자/대리점 지위 증명, 입찰자 자신의 이행약속, 일반 자격증빙

L41 clarification은 `낙찰자 결정 전`까지를 한 시점으로 넓혀 적격심사 단계와 입찰 제출 단계를
합칠 수 있고, 단일 h는 복수 서류의 발급자·내용·의무·시점을 한 요구로 잘못 결합할 수 있다.
과거 EXP285-288은 이런 review field와 final label을 같은 Gemma가 함께 출력하여, 모델이
`기타서류` 또는 `입찰마감후`라고 관찰하고도 v19=1을 내는 모순을 막지 못했다. C005는 final
label을 다시 묻는 실험이 아니다.

## 4. 가설

모든 제공 문서를 순서대로 스캔해 assurance/certificate 후보가 있는 exact source window를
빠짐없이 만들고, Gemma가 **각 requirement instance를 서로 독립적으로** typed observation으로
분류하게 한다. Python은 exact source와 candidate identity만 검증한 뒤 organizer truth condition의
명시적 논리식을 계산한다.

여러 후보의 issuer/content/deadline/mandatory를 서로 합치지 않는다. 후보 하나가 0 역할이라고
다른 후보의 1 가능성을 지우지도 않는다.

## 5. source view 계약

새 label-blind view는 공고문 → 규격서 → 과업지시서 → 제안요청서 → 예외공표서 순서를 보존하고
모든 제공 문서를 inspected ledger에 기록한다.

- assurance/certificate 계열 표면형 주변의 문장/목록/상위 제목을 exact substring window로 만든다.
- 겹치는 window만 deterministic하게 합치며 원문 문자를 고치지 않는다.
- candidate ID, doc_id, 문서 유형, 원문 offset, SHA-256을 보존한다.
- 후보가 없으면 `NOT_FOUND`, 문서를 읽지 못했으면 `UNOBSERVED`로 구분한다.
- selector 미탐지를 v19=0으로 바꾸지 않는다. 후보 없는 공고는 frozen B19 결과를 유지한다.
- 후보가 너무 많아 budget을 넘으면 exact tokenizer 기준으로 notice-level pass를 나누고 candidate
  coverage를 보존한다. candidate를 조용히 자르지 않는다.

Python 표면형은 후보 admission만 담당한다. `제출 가능`, `계약 시`, `적격심사` 같은 문구로
label이나 semantic field를 직접 정하지 않는다.

## 6. Gemma observation schema

출력은 candidate ID가 key인 JSON object로 강제하여 duplicate/missing array ID 문제를 막는다.
각 candidate는 다음을 가진다.

```text
source_id: exact candidate ID
quoted_text: candidate 안의 변경 없는 핵심 substring
requirement_role:
  BID_OR_PROPOSAL_QUALIFICATION | POST_BID_REVIEW | CONTRACT_PERFORMANCE |
  FORM_OR_TEMPLATE | INFORMATION_ONLY | OTHER | UNKNOWN
document_kind:
  EXTERNAL_SUPPLY_OR_TECH_ASSURANCE | EXTERNAL_STATUS_OR_AUTHENTICITY_CERTIFICATE |
  BIDDER_SELF_PROMISE | OTHER_DOCUMENT | UNKNOWN
acquisition_actor:
  BIDDER_FROM_EXTERNAL_PARTY | BIDDER_SELF | AGENCY | UNKNOWN
obligation:
  MUST_OBTAIN_OR_HOLD | MUST_SUBMIT | CAPABLE_ONLY | MENTION_ONLY | UNKNOWN
deadline:
  BEFORE_BID_DEADLINE | WITH_BID_OR_PROPOSAL | AFTER_BID_BEFORE_AWARD |
  AFTER_AWARD_OR_CONTRACT | MULTIPLE | UNSPECIFIED | UNKNOWN
adverse_effect:
  BID_INVALID_OR_EXCLUDED | AWARD_EXCLUDED | CONTRACT_ONLY | NONE_STATED | UNKNOWN
```

Gemma는 법률 label `v19`나 최종 0/1을 출력하지 않는다. 한 후보에 복수 시점이 있으면
`MULTIPLE`만 내고 끝내지 않고, before-bid obtain/hold와 later-submit 사실을 각각 보존할 수 있는
구조를 구현 단계에서 확정한다. 이 요구를 한 enum으로 표현할 수 없다면 schema를 최소한의
`before_bid_obtain`, `with_bid_submit`, `post_bid_submit` 3-state 필드로 분해한다.

## 7. Python reducer

candidate별 positive predicate는 organizer source로 추적 가능한 다음 식만 사용한다.

```text
external_assurance
AND bidder_obligation
AND (
  mandatory_obtain_or_hold_before_bid
  OR mandatory_submit_with_bid_or_proposal
)
AND valid_exact_source
```

`AFTER_BID_BEFORE_AWARD`는 `BEFORE_BID_DEADLINE`과 같지 않다. `CAPABLE_ONLY`, 단순 목록·시점
불명, 계약 후에만 제출, 지위/진품/대리점 증명, 입찰자 자기 확약은 predicate를 충족하지 않는다.
최종 v19는 valid candidate predicate의 OR이다. e19는 positive candidate의 exact `quoted_text`
중 문서순/offset순 첫 문자열을 사용하고 500자를 넘지 않는다.

UNKNOWN, missing candidate output, invalid quote는 positive로 승격하지 않는다. 다만 candidate가
있는데 응답 전체가 unusable이면 frozen v19를 유지하고 fallback을 보고한다. 이 fallback은
실험 결과에서 별도 집계하며 candidate-level negative와 혼동하지 않는다.

## 8. base config와 allowed policy changes

Fully resolved C005 manifest는 다음 effective changes만 허용한다.

- `layers.views.v19`: frozen B19 view → `v19-requirement-instance-view-v1`
- `layers.decisions.v19`: frozen B19 final → `v19-requirement-instance-observation-reducer-v1`
- `layers.assembly.v19/e19`: C004S row의 해당 두 cell만 replacement
- v19 task schema/system/user message
- v19 candidate task의 tokenizer overflow policy

금지:

- v19 compact truth condition/card 변경
- 다른 v의 prompt, owner, merge, evidence, card, metadata/product context
- provider model/temperature/token limit/concurrency 변경
- notice ID, dev label, 금액/문구 allowlist를 사용한 label override
- legacy import, legacy script 실행, compatibility shim, generated legacy source

## 9. 실행 단계와 stop rule

### Phase A — 무료 구조 검증

1. source view unit fixtures와 dev200 label-blind coverage report
2. positive를 보기 전 고정한 schema/reducer unit test
3. candidate key completeness, exact quote, duplicate/missing recovery test
4. fully resolved manifest와 active `scripts/preflight_experiment.py`
5. short complete, attachment, largest, synthetic/natural overflow, 오류 panel의 exact rendered messages
6. v19 semantic-input contract: 적용 전제·1 조건·핵심 0 조건·필요 문서가 rendered input에 모두 존재
7. exact tokenizer admission, mock, 49-column/evidence validation

Phase A에서 모든 organizer v19 positive가 selector candidate를 갖는지는 **coverage 진단**으로만
보고한다. 이를 이용해 phrase list를 추가 최적화하지 않는다. 일반 surface family가 빠졌다면
source-first 원칙에 따라 한 번 보완하고 selector version을 올린다.

### Phase B — 고정 fast20

`configs/dev_fast_panel_v1.json`만 사용한다. C004S fast의 v19는 `0/0/1`, F1 0이다.

승격 조건:

- FN `PPS-DEV-036` 회수(TP >= 1)
- FP <= 1
- unusable/fallback 0 또는 원인이 serialization-only로 분리됨
- positive evidence 100% exact substring
- non-v19 changed cells 0

### Phase C — independent holdout20

C004S holdout v19는 positive 0, FP 1이다. 동일 manifest/policy로 실행한다.

- FP = 0 목표, FP <= 1 비열화 한계
- fast에서 확인한 observation/reducer를 수정하지 않는다.
- 새 phrase/card/schema 조정 없이 통과한 경우에만 dev200으로 간다.

### Phase D — dev200

최소 성공은 `TP>=6, FP<=6, FN=0`으로 v19 F1 `.666667`, Macro 약 `.811674`다.
목표는 `TP>=6, FP<=3, FN=0`으로 v19 F1 `.800000`, Macro 약 `.817230`다.
다른 23개 항목 cell 변화는 0이어야 한다.

## 10. runtime 해석

C005는 v19 final owner를 교체하는 실험이지 기존 B19에 verifier call을 더하는 실험이 아니다.
후보 공고에 한해 한 observation call을 만들고 후보 없는 공고는 C004S/frozen result를 유지하는
quality probe로 시작한다. 품질 통과 뒤 submission topology를 별도로 설계할 때는 frozen B19와의
중복 호출을 제거하여 공고당 전체 call 수가 증가하지 않는 구성을 우선한다.

OpenRouter 시간은 evaluator vLLM 시간의 근거가 아니다. 결과 문서에는 candidate notices,
logical calls, overflow passes, prompt/completion tokens, p95/max, malformed/retry를 따로 기록한다.

## 11. 산출물

```text
outputs/clean-exp-c005-v19-requirement-instances-v1/
  resolved_manifest.json
  preflight.json
  source_coverage.json
  rendered_inputs/
  semantic_contract.json
  mock_responses/
  responses/
  observations.json
  writer_trace.json
  submission.csv
  metrics.json
  run_report.json
```

각 단계 결과는 별도 문서로 남기며, paid call 전 계획 문서의 상태를 승인으로 갱신한다.

## 12. Phase A 결과

2026-09-21에 clean 구현, declared-diff preflight, dev200 374/374 source audit, exact tokenizer
admission, short/attachment/largest/error-panel rendered review, active-v19 semantic contract,
dev200·fast20 mock, 49-column/evidence/owner isolation과 52 tests를 완료했다. 자연 overflow는 없고
max prompt는 9,344/14,848 tokens였다. Synthetic low-budget test는 candidate를 누락 없이 두
pass로 나눈다. 상세는 `docs/clean_exp_c005_v19_requirement_instances_phase_a.md`에 기록한다.

가설의 모든 구성요소가 구현·선택됐으므로 fast20의 17 candidate calls만 승인한다. Fast gate
실패 시 holdout을 실행하지 않는다.

## 13. Fast20 및 C005R

원 C005 fast 응답은 14건이 negative candidate의 `N/A` 또는 공백 정규화 quote 때문에 전체
fallback되어 quality 판정이 불가능했다. Semantic task를 바꾸지 않은 C005R positive-only quote
resolution 0-call replay에서 invalid가 0이 됐고 v19 `TP/FP/FN=1/0/0`, F1 `1.0`, fast Macro
`.741667`을 기록했다. 따라서 계획의 fast gate는 C005R 결과로 PASS다. 상세는
`docs/clean_exp_c005r_v19_quote_resolution_fast20_result.md`를 따른다.
