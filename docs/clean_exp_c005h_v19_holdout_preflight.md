# EXP-C005H v19 independent holdout20 preflight

실행일: 2026-09-21  
결론: **PASS — holdout20 provider 실행 승인**

## 불변 정책

C005R fast winner의 candidate view, prompt, keyed schema, semantic predicate, positive-only quote
resolver와 provider parameters를 그대로 유지한다. Fast stored-response replay topology만 실제
holdout inference topology로 바꿨다.

- manifest: `experiments/manifests/clean_exp_c005h_v19_requirement_holdout_v2.json`
- base: `clean_exp_c005r_v19_quote_resolution_replay_v2.json`
- declared differences: replay section 제거, 동일 quote resolver runtime 선택, call description
- undeclared differences: 0
- prompt/card/schema/reducer/provider changes: 0

## exact holdout audit

- notices: 20
- supplied documents inspected: 41 / 41
- candidate notices: 18
- exact candidates: 38
- logical calls: 18
- natural overflow: 0
- prompt token min / p95 / max: 1,694 / 6,145 / 6,145
- budget: 14,848
- semantic contract: PASS
- mock invalid: 0
- mock non-v19 changed cells: 0
- mock v19 positive without evidence: 0
- candidate 없는 baseline fallback: 2
- tests: 56 passed

Human review paths:

- short: `outputs/clean-exp-c005h-v19-requirement-holdout-v2/holdout20/rendered_inputs/short_PPS-DEV-094__p01.json`
- attachment/largest: 같은 디렉터리의 `attachment_PPS-DEV-27__p01.json`
- prior holdout FP boundary: `error_panel_PPS-DEV-050__p01.json`

검토 결론: short는 일반 자기확약/품질증빙을 보존하고, attachment는 공고문·과업지시서·제안요청서
41-document ledger 중 해당 세 문서의 네 candidate를 순서대로 제공한다. DEV050에는 `적격심사 시`
제출과 제조업체 A/S확약서가 같은 candidate 안에 있어 post-bid 경계를 판단할 수 있다. 모든
메시지에 적용 전제, 두 1 조건, 핵심 0 조건과 실제 exact source span이 있다.

## 실행 gate

C004S holdout v19는 positive 0, FP 1이다. C005H 목표는 FP 0, 비열화 한계는 FP 1이다. Invalid
response 또는 non-v19 change가 있으면 dev200으로 승격하지 않는다. Holdout 실행 후 prompt나
schema를 조정하지 않는다.
