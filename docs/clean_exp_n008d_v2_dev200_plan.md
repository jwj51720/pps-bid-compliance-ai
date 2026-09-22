# N008D: 동일 v2 정책 dev200 promotion gate

작성일: 2026-09-22

## 수학적 이유

N008 fast20 F1=1.0 (양성 3), 독립 holdout20 F1=1.0 (양성 1)이지만
두 패널 합계 양성 4건만으로 frozen v2 dev200 7/0/0을 대체할 수 없다.
holdout에는 malformed 1/20이 있었다. dev200 전체 200건에서
TP/FP/FN, invalid, evidence validity, runtime을 확인한다.
최대 보존 가치가 v2 Macro `1/24`이며, dev200에서 F1<1이면
frozen L41 셀보다 낮으므로 promotion하지 않는다.

## 정책 고정과 필수 gate

Base config는 N008H holdout manifest. `allowed_policy_changes`는
`evaluation.cohort`, `evaluation.panel_path`만이다. card=v32,
view=v2, task=v2, schema, model/generation, price threshold,
parse/evidence rule, source scan, call topology는 변경하지 않는다.
dev200 전체 200건을 쓰며 panel path는 null이어야 한다.

유료 실행 전: exact task audit hash 200/200, source coverage 374문서,
gold e2 7/7, token admission 200/200, short/attachment/largest actual
rendered message review, v2 semantic-input contract, preflight PASS,
isolated mock, tests가 필요하다. 결과에는 per-item TP/FP/FN,
malformed 종류, evidence validity, usage/calls/runtime을 보존한다.

성능 목표는 TP/FP/FN=7/0/0이며, invalid=0이 안정성 목표다.
invalid가 음성에서만 나와 F1이 1이어도 transport 정책의 완결
검증으로 간주하지 않는다. 이 dev200 역시 24항목 독립 native
Macro 측정은 아니다.
