# EXP200 — corrected-input source-first dev200 confirmation

작성: 2026-09-11, dev / mac

## 목적

EXP171의 source-first/full-final 구조와 모델·merge·후처리를 그대로 유지한 채, Astra 감사에서
확인하고 EXP192–197에서 구현한 입력 교정을 dev200 전체에서 측정한다.

- v6·v7 공식 적용범위 교정 card v10
- 경쟁제품 행의 `특이사항`과 사람이 읽는 출처 전달
- organizer 익명화 표기 의미 전달
- metadata의 제품·업종 raw code 제거

fast20 EXP196은 `.213889`로 낮았고 EXP197은 기술검증만 수행했다. 사용자가 입력 교정 상태의
dev200 실행을 명시적으로 요청했으므로, 이 실행은 통상 fast→holdout gate를 건너뛰는 진단이다.
낮은 결과를 숨기지 않으며 canonical 승격은 별도 판단한다.

## 비교 계약

- base config: `configs/config.exp197-human-readable-metadata-fast-panel-c4.yaml`
- `allowed_policy_changes`: 없음
- 데이터 선택만 fixed fast20에서 dev200 전체로 확장
- cards, product renderer, organizer semantics, metadata renderer, source scope, exact-token
  admission, 7-category inventory, final full-source, V/E schema, merge, evidence,
  `exp123_v1` frozen postprocess, provider/model parameters: EXP197과 동일
- primary historical comparison: EXP171 dev200 `.307962`
- rule-free score는 저장된 model judgment를 별도 재계산하여 보고

## 완료된 유료 실행 전 gate

- dev raw audit: 200 unique IDs / 374 supplied documents / structural error 0
- exact tokenizer final admission: source·metadata·card·semantics omission 0, over-budget 0
- source-first profile: stage 1 source omission 0, final source omission 0
- product/metadata delivery: conditional product condition omission 0, prompt-owned code leak 0
- semantic-input contract: 24/24 PASS
- rendered review: short PPS-DEV-062, attachment PPS-DEV-194, overflow PPS-DEV-169,
  conditional product PPS-DEV-054 PASS
- staged mock: 20 rows / 49 columns / IDs/evidence PASS
- preflight는 실행 직전 다시 수행

## 산출물

`outputs/exp-200-corrected-input-source-first-dev200-c4/`에 config, predictions, submission,
metrics, per-item TP/FP/FN, parse/evidence, call/runtime와 postprocess audit을 보존한다.

## 실행 중 발견된 recovery 결함

최초 dev200 실행은 2026-09-11 완료됐으나 14개 record의 source-first final parse 실패를
과거 pipeline이 동일 final message로 재시도하지 않고 일반 direct `predict(record)`로
대체했다. 7개 record의 malformed inventory도 local은 빈 contribution으로 두는 반면
submission은 동일 message를 재시도했다. 따라서 최초 `.334844`는 유망한 관측이지만 순수
정책 결과로 확정하지 않는다.

shared pipeline을 submission과 같이 malformed inventory/final message만 1회 동일하게
재시도하도록 수정했다. one-stage fallback은 제거했고 재시도 후에도 malformed인 pass는
parse-visible zero contribution을 유지한다. 영향 record union 20개는 versioned
`configs/exp200_recovery_panel_ids.json`과 EXP201 config로만 재실행한 뒤, 나머지 180개와
exact-ID overlay하여 EXP200 repaired 결과를 산출한다. 이 panel은 후보 순위를 매기는
fast20이 아니라 실행 결함 복구 cohort다.
