# Clean EXP-C007H v4 parent-scope holdout preflight

작성일: 2026-09-21

상태: **독립 holdout20 diagnostic paid run gate PASS**.

- manifest: `experiments/manifests/clean_exp_c007h_v4_parent_scope_holdout_v1.json`
- base: C007D fast manifest; prompt/view/schema/reducer/provider 모두 동일.
- 유일한 effective policy 차이는 예상 호출 수의 cohort 표기(18→7)다.
  manifest preflight: undeclared 0, unused declaration 0.
- cohort는 `configs/dev_prompt_holdout_v1.json`의 고정 20개 ID만 사용한다.
- 20 records, 7 candidate notices, 30 candidates, 7 calls, overflow 0.
- exact tokenizer min/p95/max 1,799/9,276/9,276; budget 14,848.
- source-audit task hashes 7/7 동일, 문서 누락 0, semantic contract PASS.
- mock: 20×49, invalid 0, non-v4 changed cells 0,
  v4 positive-without-evidence 0, label mutations 0.
- tests: 87 passed.

실제 rendered system/user/schema를 직접 읽었다.

- short 및 기존 v4 FN:
  `outputs/clean-exp-c007h-v4-parent-scope-holdout-v1/holdout20/rendered_inputs/short_PPS-DEV-053__p01.json`
- attachment:
  `outputs/clean-exp-c007h-v4-parent-scope-holdout-v1/holdout20/rendered_inputs/attachment_PPS-DEV-27__p01.json`
- largest:
  `outputs/clean-exp-c007h-v4-parent-scope-holdout-v1/holdout20/rendered_inputs/largest_PPS-DEV-121__p01.json`

검토: 053의 공고문 실적 후보 앞에 `입찰참가자격` 제목과 의무 참가 문구가
exact 원문으로 있고, 제한된 발주기관군 실적 문장도 후보 안에 있다.
27의 과업지시서 실적 관리는 계약 후 업무이며, 제안요청서 평가·서식과
doc ID별로 구분된다. 121의 여러 첨부 후보에도 평가·서식·계약 후 역할이
혼재되어 있으나 모두 후보별 key와 위치로 구분되어 있다. 제목형 줄의
parent 소속을 Python이 확정하지 않고, Gemma가 후보와 비교하도록 한다.
금액 scope는 여전히 제외된 diagnostic probe라는 문구도 동일하다.

유료 실행 직전 필요한 source view, exact admission, stored C005D fallback,
quote resolver, independent cohort, isolated output, mock, metric writer가
모두 구현·선택돼 있다. 목표는 v4 TP 1 / FP 0 / FN 0, invalid 0이며,
미달 시 dev200으로 확대하지 않는다.
