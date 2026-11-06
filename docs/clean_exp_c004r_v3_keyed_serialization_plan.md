# EXP-C004R — v3 candidate-keyed serialization probe

작성일: 2026-09-21

## 가설

EXP-C004 fast20의 두 local-invalid 응답은 의미판정 실패가 아니라 배열 schema가 source ID
유일성과 전수성을 표현하지 못한 serialization 결함이다. `observations[]`를 candidate ID가
property key인 object로 바꾸면 JSON schema 단계에서 중복과 누락을 동시에 금지할 수 있다.

## base와 허용 변경

- base manifest: `experiments/manifests/clean_exp_c004_v3_monetary_v1.json`
- base responses: `outputs/clean-exp-c004-v3-monetary-v1/fast20/responses/`
- probe IDs: `PPS-DEV-165`, `PPS-DEV-169`
- allowed changes:
  - response serialization: array rows with `source_id` → candidate-ID keyed object
  - 이에 필요한 schema와 출력 형식 설명
  - probe task restriction과 isolated output path
- 고정:
  - source view와 exact candidate text
  - role/basis/mandatory/amount_surface 의미
  - 입찰추정가격, strict `>` reducer, fallback policy
  - provider/generation parameter
  - base L41 cells와 다른 23개 final cells

Legacy는 import·실행·복사·생성하지 않는다. 새 adapter는 `src/pps_ai`에서 기존 active v3
observation을 candidate-complete array로 되돌린 뒤 동일 reducer에 전달한다.

## schema

기존:

```json
{"observations": [{"source_id": "M01", "role": "..."}]}
```

후보가 M01/M02/M03일 때 변경:

```json
{
  "observations": {
    "M01": {"role": "...", "requirement_basis": "...", "mandatory": "...", "amount_surface": null},
    "M02": {"role": "...", "requirement_basis": "...", "mandatory": "...", "amount_surface": null},
    "M03": {"role": "...", "requirement_basis": "...", "mandatory": "...", "amount_surface": null}
  }
}
```

`observations.required`는 모든 candidate ID이고 `additionalProperties=false`다. 각 value에는
`source_id`가 없으므로 같은 ID를 배열의 다른 위치에서 반복할 수 없다.

## 단계별 gate

1. unit test: exact key set, missing/extra key 거부, adapter 후 v1 reducer 의미 동일.
2. active manifest preflight와 exact rendered prompt review.
3. 실패 2건만 유료 재호출:
   - finish `stop` 2/2
   - keyed local parse valid 2/2
   - candidate 전수성 2/2
   - C004의 해당 두 final v3와 동일(둘 다 0)
4. probe 통과 뒤에만 별도 full-fast manifest로 10건을 모두 새 schema로 재실행한다.

이 probe는 fast20 성능 결과가 아니며, 두 건 성공만으로 holdout에 진입하지 않는다.

## 유료 실행 전 검증

- active tests: 40 passed
- manifest diff: undeclared 0, unused declaration 0, PASS
- exact tokenizer:
  - PPS-DEV-165: 2,889 tokens, required keys M01/M02/M03
  - PPS-DEV-169: 2,201 tokens, required keys M01/M02
- rendered inputs:
  `outputs/clean-exp-c004r-v3-keyed-serialization-probe-v11/rendered_inputs/`
- human review:
  - 두 user message는 C004와 byte-identical이다.
  - system의 유일한 의미 차이는 배열 source-id 지시를 keyed-object 지시로 바꾼 것이다.
  - role, basis, mandatory, exact amount surface, strict threshold, source candidates는 동일하다.
  - schema는 모든 candidate key를 `required`로 선언하고 extra key를 금지한다.

따라서 2건 유료 serialization probe를 실행할 수 있다.

## 결과

2건 모두 PASS했다. required candidate keys가 정확히 한 번씩 반환됐고 local valid 2/2,
C004 final v3/e3 동일 2/2였다. 상세는
`docs/clean_exp_c004r_v3_keyed_serialization_probe_result.md`에 기록한다. 다음은 별도 full-fast
manifest로 10건 전체를 재실행한다.

## Full-fast 재실행 승인

- manifest: `experiments/manifests/clean_exp_c004r_v3_keyed_full_fast_v11.json`
- base: `clean_exp_c004_v3_monetary_v1.json`
- allowed changes: `layers.decisions`, `v3_serialization`
- undeclared/unused manifest changes: 0/0
- fast20 supplied documents inspected: 35/35, uninspected 0
- candidate notices/candidates: 10/14
- exact tokenizer: min 1,088 / p95 2,889 / max 2,889 / sum 14,965
- mock: 20 rows, output/evidence validation PASS, baseline score 재현
- active tests: 40 passed
- rendered review:
  `outputs/clean-exp-c004r-v3-keyed-full-fast-v11/fast20/rendered_inputs/`

short/error `PPS-DEV-062`, attachment `PPS-DEV-32`, largest/serialization-error
`PPS-DEV-165`, positive error-panel `042/051/062`를 읽었다. candidate text, 입찰추정가격,
role/basis/mandatory/amount 의미, strict `>` reducer 설명은 C004와 동일하고 output container만
required-key object로 바뀌었다. 따라서 후보 10건의 새 유료 fast20 실행을 승인한다.

## Full-fast 결과와 holdout 승인

Full-fast는 v3 TP 3 / FP 0 / FN 0 / F1 1.0, invalid response 0, 다른 23개 변화 0으로
PASS했다. 동일 manifest의 holdout20은 41/41 documents inspected, 후보 공고 3건/후보 5개,
tokens max 1,883, mock PASS이며 rendered positive/attachment/largest를 읽었다. 상세는
`docs/clean_exp_c004r_v3_keyed_fast20_result.md`에 기록한다. Independent holdout20 3호출을
실행할 수 있다.

## Holdout 결과와 dev200 승인

Holdout20은 v3 TP 1 / FP 0 / FN 0 / F1 1.0, invalid response 0, 다른 23개 변화 0으로
PASS했다. Dev200 keyed preflight는 374/374 documents inspected, 후보 공고 61건/후보 100개,
specialist 61 calls, token max 3,720, 200-row mock PASS다. 상세는
`docs/clean_exp_c004r_v3_keyed_holdout20_result.md`에 기록한다. 동일 manifest로 dev200을
실행할 수 있다.
