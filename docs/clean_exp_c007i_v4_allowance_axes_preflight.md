# Clean EXP-C007I v4 allowance axes preflight

작성일: 2026-09-21

상태: **fast20 diagnostic paid run gate PASS**. 금액 scope가 의도적으로
빠진 relation-only probe이며 canonical v4 정책이 아니다.

## 의미 근거와 최소 정책 차이

Organizer `항목표.json`의 v4 이름은 `특정기관, 특정실적`의 두 제한축을
명시한다. versioned v4 card도 특정 발주기관 실적의 독점과 특정 명칭·유형
실적 제한을 별도 조건으로 다룬다. C007H의 053 원문과 Gemma 응답은
발주기관 제한(I)을 인정하면서도 동등 사업내용 허용(E)을 같은 단일 `a`
필드에 합쳤다. 그 결과 기관 제한까지 사라진 것으로 계산했다. 이 두 축의
허용을 분리하는 것이 이번 하나의 변경이다. 문서 원문, 기관명, 사업내용을
Python rule로 해석하거나 053 ID 예외를 만들지 않는다.

- base: `clean_exp_c007h_v4_parent_scope_holdout_v1.json`
- candidate: `experiments/manifests/clean_exp_c007i_v4_allowance_axes_fast_v1.json`
- manifest diff PASS, undeclared 0, unused declaration 0.
- 바뀐 것: v4-only system/user wording, `i` field 추가 및 `a` 의미 제한,
  이 두 field를 사용하는 reducer. r/m/x/n/q, source view, quote resolution,
  other 23 item cells, provider settings는 고정.
- `i`: 발주기관군 밖 실적 허용 B / 명시적 확장 없음 N / 불명 U.
- `a`: 동등한 사업내용 허용 E / 확장 없음 N / 불명 U.
- `x=I`에는 `i`만, `x=S`에는 `a`만 해당 허용축으로 적용한다.

Source ledger:
`outputs/clean-exp-c007i-v4-allowance-axis-audit-v1/observability_report.json`
안에 organizer item table/card의 경로·SHA-256·v4 관련 필드가 기록돼 있다.

## source coverage와 exact admission

Audit command:
`.venv/bin/python scripts/audit_v4_requirement_view.py --scope heading-trail --allowance-axes --review-id PPS-DEV-053 --output outputs/clean-exp-c007i-v4-allowance-axis-audit-v1`

- dev200 374/374 supplied documents inspected; 109 candidate notices,
  446 exact candidates. C007D candidate ledger와 byte-identical.
- heading line 2,156개, source provenance errors 0.
- positive candidate 6/6, nonempty gold evidence covered 5/5,
  C005D baseline errors with candidate 7/7.
- tokenizer admission: 110 tasks, overflow 1, max 14,812 / budget 14,848,
  over-budget 0. 따라서 extra schema field가 call topology를 늘리지 않는다.
- fast20: 35/35 supplied documents inspected, 18 candidate notices,
  57 candidates, 18 calls, overflow 0, token min/p95/max 1,516/8,275/8,275.
- fast task hashes 18/18이 label-blind full audit와 동일.

## 실제 rendered input 검토

다음 exported system/user/schema를 직접 읽었다.

- short complete: `outputs/clean-exp-c007i-v4-allowance-axis-audit-v1/rendered_inputs/short_PPS-DEV-061__p01.json`
- attachment: `outputs/clean-exp-c007i-v4-allowance-axis-audit-v1/rendered_inputs/attachment_PPS-DEV-03__p01.json`
- overflow: `outputs/clean-exp-c007i-v4-allowance-axis-audit-v1/rendered_inputs/overflow_PPS-DEV-11__p01.json`,
  `outputs/clean-exp-c007i-v4-allowance-axis-audit-v1/rendered_inputs/overflow_PPS-DEV-11__p02.json`
- prior holdout FN: `outputs/clean-exp-c007i-v4-allowance-axis-audit-v1/rendered_inputs/manual_review_PPS-DEV-053__p01.json`

검토 결과: system은 기관군/사업내용의 허용을 분리하고 다른 축을 임의로
상쇄하지 말라고 명시한다. 053에는 참가자격 제목, 같은 기관군 발주실적
요구, 동등 사업내용 표현이 함께 있지만 기관군 외 허용은 나타나지 않는다.
061의 서류목록과 03의 공고문/첨부 후보도 역할 구분이 유지된다.
overflow 11은 R001–R017과 R018–R019를 누락·중복 없이 나눈다.
C007D와 candidate ledger가 byte-identical이며 해당 rendered user는
허용축 문구 한 곳 이외에는 byte-identical이라는 비교를 확인했다.
새 schema는 모든 candidate ID에 `r,m,x,i,a,n,q`를 요구한다.
semantic-input contract PASS. 금액 scope 제외는 명시돼 있고,
다른 23개 v는 C005D stored rows를 byte-identical로 승계한다.

## mock와 paid gate

`.venv/bin/python scripts/run_v4_requirement_experiment.py --config experiments/manifests/clean_exp_c007i_v4_allowance_axes_fast_v1.json --cohort fast20 --mock`

- mock PASS: 20×49, invalid 0, non-v4 changed cells 0,
  v4 positive-without-evidence 0, label mutations 0.
- UNKNOWN axis observation은 C005D v4로 fallback; automatic positive 없음.
- full suite 93 passed.
- fast20 목표: C007D의 v4 TP/FP/FN `3/0/0`, invalid 0 유지.
  실패하면 holdout으로 확대하지 않는다. 달성하면 independent holdout20에서
  v4 `1/0/0`과 evidence exact를 확인한 뒤에만 dev200을 검토한다.
