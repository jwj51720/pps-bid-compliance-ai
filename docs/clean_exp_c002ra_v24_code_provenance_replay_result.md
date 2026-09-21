# EXP-C002RA v24 code-provenance offline replay 결과

작성일: 2026-09-21

## 결론

C002RA는 외부 호출 없이 C002R의 저장된 fast20 response 20개를 그대로 재생했다. 사전 식별한
두 reducer correctness defect에 해당하는 prediction 두 개만 1에서 0으로 바뀌었고 나머지
prediction은 유지됐다.

- external calls: 0
- responses replayed: 20/20
- response hash ledger: 20/20
- fallback: 1, C002R과 동일
- non-v24 changed cells: 0
- C002R v24: TP 1 / FP 4 / FN 2 / F1 0.25
- C002RA v24: TP 1 / FP 2 / FN 2 / F1 `0.3333333333`
- C002RA fast20 Macro positive-F1: `0.6930555555555555`
- canonical fast20 대비 Macro: `+0.0138888889`

이 결과는 prompt 개선이나 새 모델 호출의 성능 결과가 아니라, 사전 계획과 구현을 일치시킨
deterministic replay 결과다.

## 검증된 변화

prediction 변화는 정확히 두 건이었다.

1. 10자리 세부품명번호를 업종코드 집합에서 제외해 거짓 업종 불일치를 제거했다.
2. 업종명 surface mismatch와 독립적으로 source에 존재하는 4자리 업종코드를 유지해 거짓 집합
   누락을 제거했다.

두 변화 모두 특정 notice ID, 지역명, 업종명 또는 정답 label을 final rule에 넣지 않는다. reducer는
모든 공고에 동일하게 다음 식을 적용한다.

```text
valid_code = regex_fullmatch([0-9]{4}) AND exact_digits_in_source
```

## 재현성

- manifest:
  `experiments/manifests/clean_exp_c002ra_v24_code_provenance_replay_v21.json`
- command:

```bash
.venv/bin/python scripts/replay_v24_code_provenance.py \
  --config experiments/manifests/clean_exp_c002ra_v24_code_provenance_replay_v21.json
```

- output:
  `outputs/clean-exp-c002ra-v24-code-provenance-replay-v21/fast20/`
- response ledger:
  `outputs/clean-exp-c002ra-v24-code-provenance-replay-v21/fast20/response_ledger.json`
- result report:
  `outputs/clean-exp-c002ra-v24-code-provenance-replay-v21/fast20/run_report.json`

Manifest preflight는 PASS였고, base C002R 대비 선언된 변경은 `layers.decisions`,
`layers.assembly`, `v24_policy`뿐이었다. source view, prompt, response schema, provider, generation
parameter는 변경하지 않았다.

## 해석과 다음 gate

correctness correction 후 performance 수치는 C002R의 fast20 성능 조건 `TP>=1`, `FP<=3`을
충족한다. 하지만 한 response가 여전히 `finish_reason=length`이고 fallback이 1이므로 원래 gate의
fallback 0을 충족하지 않는다.

따라서 holdout20으로 자동 승격하지 않는다. 다음 실험은 다음 한 가지에만 제한한다.

- distinct observation serialization contract로 동일 source/role/value 반복과 whitespace loop를
  줄인다.

그 실험은 reducer v2.1과 source view를 고정하고 response schema/prompt serialization만 바꾸는 별도
manifest여야 한다. fast20 전체를 다시 호출하기 전에 problematic response와 작은 mock/one-record
probe에서 finish reason, completion tokens, semantic reducer input의 동등성을 입증해야 한다.
