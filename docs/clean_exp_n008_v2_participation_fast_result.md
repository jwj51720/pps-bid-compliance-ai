# N008 v2 정량 참가 문턱 observation: fast20 결과

작성일: 2026-09-22

## 결과와 승격 상태

고정 `configs/dev_fast_panel_v1.json` 20건에서
TP/FP/FN/TN=3/0/0/17, precision=recall=F1=1.0,
invalid=0, positive evidence valid=3/3이다. N007의 3/2/0,
F1 .75와 비교해 FP 2건이 사라지고 TP 3건은 유지됐다.
v2 단일 항목의 잠재 Macro 개선은 `(.25)/24 = .0104167`이지만,
전체 24항목 점수의 실측 상승을 뜻하지 않는다. fixed fast panel에
노출된 후보이므로 **아직 canonical 승격하지 않는다**. 독립
holdout20을 통과한 뒤 dev200을 검토한다.

## 실제 변경·재현

- 가설/범위: `docs/clean_exp_n008_v2_participation_axis_plan.md`.
- manifest: `experiments/manifests/clean_exp_n008_v2_participation_fast_v1.json`.
  base N007, 선언된 변경은 `prompt.task`와 task audit path뿐.
  manifest preflight PASS, undeclared/unused 0.
- exact task preflight: `docs/clean_exp_n008_v2_fast_preflight.md`.
  actual rendered short/attachment/largest 읽음, v2 semantic-input
  contract 점검, dev200 admission 200/200, fast20 hash 20/20.
- output: `outputs/clean-exp-n008-v2-participation-fast-v1/fast20/`의
  config, preflight, responses, observations, run_report.
- 20 logical/new calls, OpenRouter wall 23.019초. usage prompt 120,598,
  completion 1,301 tokens, response cost 필드 합계 USD 0.01107836.
  이 원격 시간은 evaluator vLLM runtime 근거가 아니다.
- mock은 별도 `fast20-mock` 20건 invalid 0. 테스트 158 passed.

## 오류 변화의 실제 축

N007 FP `PPS-DEV-058`(정량 하한 없는 수행 경험)과
`PPS-DEV-165`(제안서 평가용 실적)의
`performance_participation`이 모두 Y→N으로 바뀌었다.
N007 invalid `PPS-DEV-169`도 Y→N 및 quote=null로 바뀌어
invalid가 0이 됐다. 세 TP `PPS-DEV-062`, `PPS-DEV-042`,
`PPS-DEV-069`은 Y와 exact-source evidence를 유지했다.
view/card/schema/threshold/parser/provider는 변경되지 않았으므로
이 fast panel의 개선은 observation 문구 한 가지 변경과 일치한다.

독립 holdout20의 양성은 1건이다. 따라서 그 panel의 F1=1이 나와도
추정 불확실성이 매우 크고 dev200 검증을 생략할 수 없다.
