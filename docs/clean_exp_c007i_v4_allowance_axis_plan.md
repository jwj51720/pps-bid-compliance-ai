# Clean EXP-C007I: v4 allowance-axis observation plan

작성일: 2026-09-21

## 가설과 최소 변경

C007H는 053의 role(Q), mandatory(Y), issuer restriction(I)를 정확히
관측했지만 범용 allowance `a=E`가 사업내용의 동등 허용과 발주기관군의
개방을 혼동해 FN을 냈다. 따라서 허용을 제한축별로 관측한다.

- 기존 `a`를 **사업내용·범위에 대한 동등/유사 허용**으로 의미를 좁힌다.
- 새 `i`를 **발주기관군에 대한 허용**으로 추가한다.
- `x=I`의 배제 조건은 `i=B`(기관군 폭넓게 허용)일 때만, `x=S`의
  배제 조건은 `a=E`(사업내용 동등 허용)일 때만 적용한다.
- 역할 `r`, 의무 `m`, 제한 `x`, 필요성 `n`, quote `q` 및 source view는
  C007H 그대로 둔다. Python은 원문 문구를 읽어 `i`를 채우거나
  053 ID 예외·keyword override를 만들지 않는다.

이는 다른 23개 v를 묶은 새 framework가 아니라 v4 한 항목에서 이미
증명된 표현 손실만 복구하는 실험이다. 053의 원문은 source view에 존재하고
위반 판단의 두 제한축도 organizer 항목표의 `특정기관, 특정실적`과 연결된다.
금액 scope는 relation-only diagnostic에서 계속 제외한다.

## 비교와 수학적 gate

- base manifest: `clean_exp_c007h_v4_parent_scope_holdout_v1.json`.
- C007D fast20 v4 `3/0/0`, macro `0.736111`; 이를 유지해야 한다.
- C007H holdout20 v4 `0/0/1`, macro `0.430556`.
- holdout 목표 `1/0/0`, v4 F1 `1`; 다른 23개 고정이면 macro
  상승량 `1/24 = 0.0416667`, 목표 macro `0.472222`.
- malformed 0, positive exact evidence 100%, non-v4 changed cells 0,
  dev200 task topology는 C007D의 110 calls에서 증가하지 않아야 한다.
- fast20을 먼저 실행하고 독립 holdout20 확인 후에만 dev200으로 확대한다.

## 실행 전 요구

1. 완전한 새 manifest와 `allowed_policy_changes`: v4 schema·prompt·reducer만.
   provider, quote resolution, candidate scope, 다른 item owner 고정.
2. v4 진리조건을 organizer item table/card/source의 exact span에 추적하고,
   새 `i`와 기존 `a`가 별개 허용축인지 053 및 negative 사례에서 확인.
3. source coverage/provenance, exact tokenizer admission, overflow,
   0-call mock, isolated output, task-hash and call count audit.
4. short complete / attachment / overflow / 053 실제 rendered system/user/schema를
   내보내 직접 읽고 semantic-input contract 확인.
5. fast20 → holdout20 → dev200 순서. 각 단계에서 per-item TP/FP/FN,
   invalid, evidence validity, token/call/runtime, field observations 저장.

이 실험도 통과 전에는 canonical policy 또는 제출 후보가 아니다.
