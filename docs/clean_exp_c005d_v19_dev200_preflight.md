# EXP-C005D v19 dev200 promotion preflight

작성일: 2026-09-21

상태: 유료 dev200 실행 승인

## 선택 확인

- manifest: `experiments/manifests/clean_exp_c005d_v19_dev200_promotion_v1.json`
- manifest SHA-256:
  `4962f4c8c13299aba161b518f562e2c38c0614f2ea1cd09273ac5f6397c6d015`
- base: C005H holdout manifest
- quality baseline: C004S dev200 Macro `0.8037378356650803`
- active owner change: v19 only
- primary task: C005H/C005R에서 검증된 verbose 9-field source-only observation
- recovery: strict semantic parse 실패 task만 compact 9-field schema로 최대 한 번
- output: `outputs/clean-exp-c005d-v19-dev200-promotion-v1/dev200/`

manifest diff는 undeclared difference 0, unused declaration 0으로 PASS다. model, temperature,
max completion token, seed, source view, reducer, quote resolution 및 다른 23개 item owner는 변하지 않았다.

## source coverage와 admission

- records: 200/200
- organizer documents inspected: 374/374
- uninspected documents: 0
- candidate notices: 165
- exact candidates: 372
- primary logical calls: 165
- overflow passes: 0
- token min/p95/max: 1,336 / 6,725 / 9,344
- prompt budget: 14,848
- C005 Phase A primary task hashes: 165/165 MATCH

모든 supplied document를 admission scan했으며 후보가 없는 35개 공고만 specialist call이 없다. 이
35개도 C004S frozen baseline에서 실제 공고를 포함한 성공 Gemma call을 이미 갖는다. C005D는 v19
owner ablation이므로 그 결과를 그대로 보존한다.

## rendered input 사람 검토

다음 실제 JSON의 system/user/schema를 읽었다.

- short complete:
  `outputs/clean-exp-c005d-v19-dev200-promotion-v1/dev200/rendered_inputs/short_PPS-DEV-077__p01.json`
- attachments:
  `outputs/clean-exp-c005d-v19-dev200-promotion-v1/dev200/rendered_inputs/attachment_PPS-DEV-04__p01.json`
- largest admitted:
  `outputs/clean-exp-c005d-v19-dev200-promotion-v1/dev200/rendered_inputs/largest_PPS-DEV-063__p01.json`
- compact recovery exact example:
  `outputs/clean-exp-c005hs-v19-compact-serialization-probe-v1/rendered_inputs/probe_PPS-DEV-192__p01.json`

dev200에는 overflow가 0이므로 overflow 표본 대신 largest admitted 9,344-token 공고를 검토했다.
attachment 표본은 공고문·과업지시서·제안요청서 세 문서 유형의 후보를 모두 포함한다. 세 primary
메시지 모두 v19 대상, 두 1-condition, 중요한 0-condition/exception, 모든 candidate ID와 exact
source span을 포함한다. raw metadata/internal code, 법령 원문, legacy context는 없다.

compact recovery는 primary user가 byte-identical이고 primary system 전체가 byte-identical prefix다.
추가 suffix는 9개 field의 key/enum을 1:1 code로 표현할 뿐이다. C005HS에서 이 계약을 실제 실패
target에 대해 검증했고 127 completion token으로 정상 종료했다.

## semantic-input contract

v19 active contract:

- applicability: 외부 제조사·공급사·기술지원사의 물품공급/기술지원 이행보장
- 1-condition A: 입찰·제안 마감 전에 발급 또는 보유 의무
- 1-condition B: 입찰서·제안서와 함께 의무 제출
- material 0: 단순 목록, 제출 가능 업체, 시점 없는 언급, 낙찰·계약 후에만 제출,
  지위·정품 증명, 입찰자 자기확약
- required source: 모든 supplied notice document를 scan한 exact candidate
- metadata/organizer CSV: 이 item truth condition에는 별도 metadata/product fact가 필요하지 않음
- evidence: positive predicate candidate의 unchanged source substring만 허용

rendered semantic contract는 PASS다. 다른 23개 item은 C004S frozen output과 byte-for-byte 동일하게
assembly하며 새 prompt를 만들지 않는다.

## mock와 테스트

- dev200 mock: PASS
- output shape: 200 rows × 49 columns, unique complete IDs
- non-v19 changed cells: 0
- mock invalid responses: 0
- evidence validation label mutations: 0
- pytest: 63 passed
- legacy import/실행/생성: 없음

mock v19 F1=0은 mock observation이 의도적으로 모두 음성이기 때문에 품질 결과로 해석하지 않는다.
mock evidence report의 v15/v24 positive-without-evidence는 frozen C004S row의 기존 진단이며 C005D가
변경하거나 label mutation한 값이 아니다.

## 유료 실행 gate

실행 시 165 primary calls를 만들고, strict semantic-invalid task에만 compact recovery를 최대 한 번
호출한다. 유효 primary에는 recovery task를 생성하지 않는다. 최종 invalid 0, non-v19 change 0,
v19 F1 및 Macro의 baseline 초과를 모두 만족해야 승격한다. 실패한 compact 형식은 재시도하지 않는다.
