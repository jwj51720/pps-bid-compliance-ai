# Clean EXP-C007D v4 parent-scope preflight

작성일: 2026-09-21

상태: **fast20 diagnostic paid run gate PASS**. C007D는 관계형 v4 role 관측만
검증하며 금액 scope를 포함한 canonical v4 전략은 아니다.

## 변경 통제

- base: `clean_exp_c007cr_v4_quote_replay_v1.json`
- manifest: `experiments/manifests/clean_exp_c007d_v4_parent_scope_fast_v1.json`
- 변경: label-blind exact preceding heading-trail view와 이를 읽는 v4 role 지시만.
- C007CR의 `r,m,x,a,n,q` schema, positive predicate, exact/unique-whitespace
  quote resolution, C005D 다른 23개 셀, provider setting은 불변.
- C007CR은 0-call replay였으므로 C007D에서는 저장 응답 source를 제거하고
  live specialist call을 명시적으로 재개한다.
- manifest diff PASS: undeclared differences 0, unused declarations 0.

## source coverage와 admission

Audit command:
`.venv/bin/python scripts/audit_v4_requirement_view.py --scope heading-trail --review-id PPS-DEV-049 --output outputs/clean-exp-c007d-v4-parent-scope-audit-v1`

- dev200 supplied documents 374/374 inspected, 109 candidate notices, 446 candidates.
- candidate with heading trail 397; exact heading lines 2,156, provenance errors 0.
  나머지 49 후보는 `없음`으로 표시하며 Python이 parent 역할을 추정하지 않는다.
- positive candidate coverage 6/6, nonempty gold evidence in candidate 5/5,
  C005D baseline error candidate 7/7 — C007B와 동일.
- exact Gemma tokenizer: 110 tasks, overflow 1, max 14,844 / budget 14,848,
  over-budget 0. 추가 1회는 PPS-DEV-11의 19 후보가 17+2로 분할된 것이다.
- fast20: 20 records, 18 candidate notices, 57 candidates, 18 calls,
  overflow 0, prompt tokens min/p95/max 1,548/8,307/8,307.
- fast task hash 18/18이 audit report와 일치.

## 실제 rendered message 사람 검토

다음 system/user/schema 파일을 직접 읽었다.

- short complete:
  `outputs/clean-exp-c007d-v4-parent-scope-audit-v1/rendered_inputs/short_PPS-DEV-061__p01.json`
- attachment:
  `outputs/clean-exp-c007d-v4-parent-scope-audit-v1/rendered_inputs/attachment_PPS-DEV-03__p01.json`
- overflow: `outputs/clean-exp-c007d-v4-parent-scope-audit-v1/rendered_inputs/overflow_PPS-DEV-11__p01.json`,
  `outputs/clean-exp-c007d-v4-parent-scope-audit-v1/rendered_inputs/overflow_PPS-DEV-11__p02.json`
- latent FP 049:
  `outputs/clean-exp-c007d-v4-parent-scope-audit-v1/rendered_inputs/manual_review_PPS-DEV-049__p01.json`

검토 결론:

- 049의 R001에 `7. 규격 입찰서(제안서) 제출`과 `라. 제출서류`가
  후보 원문 앞에 exact offsets로 나타난다. 제목 이력은 자동 parent 판정이
  아니라고 명시되어 있다.
- 061의 실적증명서는 실제 신청서 목록으로 보이며, 제목·후보를 함께 줘
  Q로 과장하지 말라는 계약이 있다.
- 첨부 예 03은 공고문 Q 후보와 과업지시서 C 후보를 doc-id별로 분리한다.
- 11의 분할은 후보 ID R001–R017과 R018–R019를 중복 없이 보존한다.
  같은 notice의 candidate observations를 모두 받은 뒤 reducer가 결합한다.
- 번호가 붙은 단순 목록행도 제목형 줄로 포함될 수 있다. Python은 이 줄의
  절 소속이나 법률 의미를 확정하지 않으며, Gemma에게 위치 단서라고 알린다.
  그러므로 heading provenance 0 오류는 semantic parent 정확도 100% 주장이 아니다.
- v4 applicability, 1 관계, 평가·서식·계약후 0 조건, 허용/필요 예외는
  system/user에 존재한다. v4 금액 gate는 의도적으로 제외된 진단 probe다.
  다른 23개 v는 C005D stored rows 그대로이며 새 prompt를 생성하지 않는다.
- 별도 semantic contract PASS. raw metadata/status, law text, gold label 없음.

## mock와 테스트

`.venv/bin/python scripts/run_v4_requirement_experiment.py --config experiments/manifests/clean_exp_c007d_v4_parent_scope_fast_v1.json --cohort fast20 --mock`

- mock PASS: 20 × 49 columns, 18 logical tasks, invalid 0,
  non-v4 changed cells 0, v4 positive-without-evidence 0, label mutations 0.
- UNKNOWN mock response는 기존 C005D v4로 fail-closed한다.
- full test suite: 87 passed.

## 유료 실행 직전 재확인

가설에 필요한 heading view, candidate rendering, role prompt, unchanged schema,
quote resolver, tokenizer pack, source audit report, task-hash check, C005D fallback,
isolated output, mock, metrics가 모두 구현·선택돼 있다. fast20에서
TP 3 / FP 0 / FN 0 및 invalid 0을 달성하지 못하면 holdout으로 확대하지 않는다.
