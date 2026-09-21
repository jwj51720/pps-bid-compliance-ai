# Clean EXP-C007C v4 relation probe preflight

작성일: 2026-09-21

상태: fast20 diagnostic paid run 승인

## 선택과 변경 통제

- manifest: `experiments/manifests/clean_exp_c007c_v4_relation_probe_v1.json`
- quality base: C005D stored dev200 rows
- active owner change: v4 only
- prompt/schema/reducer: C007B native requirement-instance v1
- status: relation-only diagnostic, canonical 아님
- fixed: 다른 23개 owner/cell, model, temperature, completion limit, seed, evidence validator

manifest preflight는 undeclared difference 0, unused declaration 0으로 PASS다. 허용 변경은
`layers.views`, `layers.decisions`, `layers.assembly`, `v4_policy`,
`runtime.expected_calls_per_record`뿐이다.

## source coverage와 exact admission

- fast records: 20
- supplied documents: 전부 inspected
- candidate notices / candidates: 18 / 57
- specialist logical calls: 18
- overflow passes: 0
- exact prompt tokens min / p95 / max: 1,308 / 6,729 / 6,729
- C007B label-blind audit task hashes: 18/18 identical

후보가 없는 2개 공고는 C005D v4를 그대로 유지한다. 후보 미탐지를 0으로 바꾸지 않는다.

## rendered message 사람 검토

다음 실제 system/user/schema를 읽었다.

- short:
  `outputs/clean-exp-c007c-v4-relation-probe-v1/fast20/rendered_inputs/short_PPS-DEV-062__p01.json`
- attachment:
  `outputs/clean-exp-c007c-v4-relation-probe-v1/fast20/rendered_inputs/attachment_PPS-DEV-26__p01.json`
- largest:
  `outputs/clean-exp-c007c-v4-relation-probe-v1/fast20/rendered_inputs/largest_PPS-DEV-199__p01.json`
- baseline FN review:
  `outputs/clean-exp-c007c-v4-relation-probe-v1/fast20/rendered_inputs/error_panel_PPS-DEV-042__p01.json`

검토 결과:

- 042의 제출서류용 실적증명서 후보와 실제 참가자격 특정실적 후보가 서로 다른 key로 보존된다.
- 199의 평가표·서식·계약 후 언급이 모두 들어가며 role로 배제할 수 있다.
- 062의 실제 참가자격, 특정 발주기관군, 단일 실적 조항이 한 candidate에 들어간다.
- system은 final v4를 요구하지 않고 역할·제한·허용·필요성 facts만 요구한다.
- positive candidate만 exact quote를 요구하고 negative candidate quote는 null이다.
- raw metadata/internal code, law text, label은 없다.
- semantic contract 자동 검사 PASS다.

## mock와 tests

- fast20 mock: PASS
- 20 rows x 49 columns
- invalid responses: 0
- non-v4 changed cells: 0
- evidence validation label mutations: 0
- mock는 모든 observation을 UNKNOWN으로 만들어 v4도 baseline에 fail-closed한다.
- tests: 81 passed

## limitation과 실행 gate

이 probe는 organizer 항목명의 금액 scope를 최종 reducer에 넣지 않는다. 그 사실을 숨기지 않으며,
relation schema의 표현력만 측정한다. fast target TP/FP/FN `3/0/0`을 달성해야 holdout으로 간다.
minimum `2/0/1`만 유지하면 자동 승격하지 않는다. FP 증가, TP 감소, invalid/evidence 오류가 있으면
즉시 중단한다.

