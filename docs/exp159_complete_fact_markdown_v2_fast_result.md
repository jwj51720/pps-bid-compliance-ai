# EXP159 — complete-source Markdown v2 fast-20 결과

작성일: 2026-09-09 (dev / mac)

## 가설과 통제

EXP159는 EXP154의 complete-fact policy에서 `prompt.layout`만 `plain → markdown_v2`로
바꿨다. 즉, 32k exact-token source admission, card v6, 21 metadata field, friendly
competition-product fact, V/E schema, per-pass absence AND, frozen `exp123_v1`, model,
temperature, output reserve는 모두 유지했다. 새 사실·법령·rule·merge·추가 call을 넣지
않고, heading/bullet/output skeleton이 24개 card의 경계를 읽기 쉽게 하는지만 본다.

## 유료 실행 전 검증

- `scripts/preflight_experiment.py`: declared diff `prompt.layout` 하나만 PASS.
- `scripts/audit_complete_fact_admission.py`: dev-200 source 374/374, metadata 21 field,
  active card 24/24, configured product fact, token-budget pack 모두 PASS.
- `scripts/audit_candidate_semantic_contract.py`: short `PPS-DEV-01`, attachment
  `PPS-DEV-03`, overflow `PPS-DEV-143`에서 24/24 PASS.
- exact overflow input: `outputs/exp159-prompt-review/pps-dev-143.messages.md`.
  System에는 역할·기본 규칙·v별 card·JSON output contract, user에는 metadata·제품
  applicability·원문 문서가 분리되어 있으며 internal key/code/status를 지시로 넣지 않는다.
- mock fast20 및 regression 140 tests PASS.

## 결과

| 정책 | macro positive-F1 | passes | prompt tokens | completion tokens | wall time |
| --- | ---: | ---: | ---: | ---: | ---: |
| EXP154 complete-source plain | 0.241667 | 22 | 336,480 | 14,370 | 40.5초 |
| **EXP159 complete-source Markdown v2** | **0.244444** | **23** | **353,170** | **18,666** | **53.4초** |

형식 오류는 없었다. evidence validity는 `0.8261 → 0.8500`으로 소폭 올랐고 span F1은
둘 다 `0.5833`이었다.

## 해석

차이는 `+0.002778`이며, fast20 승격 근거가 아니다. macro 상승의 직접 원인은 v23 F1
`0.3333 → 0.4000`(FP 4→3) 하나다. v13은 FP 3개를 없앴지만 여전히 gold positive를
찾지 못해 F1 0이고, v24는 새 FP 2개를 만들어 F1 0이다. 핵심 FN(v4, v6–v12,
v14, v16–v18, v20)은 회복되지 않았다.

또한 heading·output skeleton의 토큰 오버헤드로 20 notices의 admission pass가 22→23,
prompt tokens가 약 5.0% 늘고 wall time도 약 13초 증가했다. 따라서 EXP159는 independent
holdout/dev-200/제출로 확대하지 않는다. 다만 rendering style이 all-source input에서
format failure를 일으키지 않는다는 구현 검증으로 보존한다.

다음 후보는 source를 축소하지 않으며, stage-2에도 complete source를 유지한
source-first/full-final architecture의 **runtime admission feasibility**를 먼저 측정한다.
