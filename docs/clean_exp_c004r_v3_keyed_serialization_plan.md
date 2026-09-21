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

