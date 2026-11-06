# EXP-C002RB v24 serialization probe preflight

검토일: 2026-09-21

## 결론

C002RB의 단일 diagnostic probe는 유료 1회 실행 전 조건을 통과했다. 이 승인은 C002R에서 length
failure가 발생한 동일 공고 한 건에만 적용한다. 성능 실험이나 fast20 전체 실행 승인이 아니다.

## 검증 결과

- active tests: 31 passed
- manifest preflight: PASS
- undeclared policy changes: 0
- probe records/logical calls: 1/1
- organizer documents inspected: 2/2
- exact tokenizer admission: 7,619 / 14,848 tokens
- task hash: `cce79681843fb4255cfb3b69c9fe8d5738c2f304686eeff8f695bb7cf430c72a`
- mock parse/reducer fallback: 0
- labels read by probe: 0
- legacy import/execute: 0

허용된 변경은 `layers.decisions`, `layers.assembly`, `v24_policy`뿐이다. source view, metadata,
candidate text, reducer v2.1의 비교식, provider/model/temperature/max completion/seed는 고정했다.

## rendered input 검토

exact rendered artifact:

`outputs/clean-exp-c002rb-v24-distinct-serialization-probe-v22/rendered_input.json`

사람 검토 결과:

- friendly metadata의 예산/추정가격/계약/지역/업종 7개 필드가 존재한다.
- 공고문과 규격서의 exact source span이 doc ID/type/offset와 함께 존재한다.
- 원래 length failure가 시작된 amount 후보에 기초금액 66,000,000원과 추정가격 60,000,000원이
  같은 exact span으로 들어 있다.
- amount source enum은 `A01`-`A04`, contract는 `C01`-`C04`, industry는 `I01`로 실제 candidate와
  일치한다.
- region candidate가 없으므로 region array의 `maxItems=0`이다.
- amount `value_won`은 integer/null이고 free string이 아니다.
- industry code pattern은 정확히 4자리다.
- 모든 axis array의 최대 distinct observation은 4개다.
- final y/different/mismatch field는 없다.
- raw metadata JSON, 별도 법령/RAG context, internal status는 없다.

## semantic equivalence

v2.2 adapter는 amount integer를 decimal string으로 바꾼 뒤 C002RA의 동일 v2.1 reducer에 전달한다.
계약 enum, 지역 원자, 4자리 업종코드는 값 변경 없이 전달한다. 따라서 serialization 성공 후의
final truth function은 C002RA와 같다.

## 승인 command와 gate

```bash
.venv/bin/python scripts/run_v24_serialization_probe.py \
  --config experiments/manifests/clean_exp_c002rb_v24_distinct_serialization_probe_v22.json
```

성공 조건:

- external calls 1
- finish reason `stop`
- completion tokens < 1,536
- serialization/reducer fallback 0
- result는 `diagnostic_probe=true`, `performance_result=false`

하나라도 실패하면 fast20 전체 실행을 만들지 않는다.
