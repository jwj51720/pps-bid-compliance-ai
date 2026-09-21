# EXP-C002RA v24 code-provenance offline replay 계획

작성일: 2026-09-21

결과: **PASS**. 외부 호출 0회로 저장 response 20개를 재생했고, 예상한 correctness defect 두 건만
1→0으로 바뀌었다. v24는 TP 1 / FP 2 / FN 2 / F1 0.333333이 됐지만 기존 fallback 1건을
그대로 보존했으므로 holdout으로 승격하지 않는다. 상세 결과는
`docs/clean_exp_c002ra_v24_code_provenance_replay_result.md`에 기록한다.

## 목적

C002R fast20에서 확인된 두 implementation defect만 교정한다. 새 Gemma 호출 없이 저장된 exact
20개 response를 동일 source view에 재적용해 reducer 변화만 측정한다.

1. 업종 비교에는 organizer와 공고 양쪽의 exact 4자리 업종코드만 사용한다.
2. 업종명 surface validation 실패가 source에 존재하는 4자리 code provenance를 무효화하지 않게
   code/name validation을 분리한다.

이 작업은 v24 truth condition을 확장하거나 fast20 고유 ID/문구를 예외 처리하지 않는다.

## base와 허용 변경

- base manifest: `experiments/manifests/clean_exp_c002r_v24_multi_observation_v2.json`
- response source:
  `outputs/clean-exp-c002r-v24-multi-observation-v2/fast20/responses/`
- allowed policy changes:
  - `layers.decisions`
  - `layers.assembly`
  - `v24_policy`
- prompt/schema/view/provider/generation 변경: 0
- external calls: 0
- 다른 v1-v23/e1-e23 cell 변경: 0

새 reducer는 기존 v2 module을 수정하지 않고 별도 active module로 둔다.

```text
src/pps_ai/decisions/v24_code_provenance_v21.py
```

## reducer contract

```text
valid_industry_codes(row) = {
  c | c matches ^[0-9]{4}$
      AND c is an exact digit substring of row.source_id's source text
}

valid_industry_names(row) = {
  n | normalized(n) is in normalized(source text)
}
```

v24 industry comparison에는 `valid_industry_codes`만 사용한다. name은 diagnostic으로 보존하되 code
validity에 영향을 주지 않는다. 10자리 세부품명번호는 업종코드 집합에 들어갈 수 없다.

금액·계약·지역 reducer는 v2와 동일하다. fallback response는 재시도하거나 복구하지 않고 그대로
fallback으로 유지한다.

## 검증

- label-independent unit fixture:
  - 4자리 code + 10자리 product code에서 product code 제외
  - name surface mismatch가 valid 4자리 code를 제거하지 않음
  - source에 없는 4자리 code 제외
- manifest preflight PASS
- response/task/source ID coverage 20/20
- response file hash ledger 기록
- replay calls 0
- v2 대비 prediction 변화는 두 implementation defect로 설명되는 notice만 허용
- v1-v23/e1-e23 완전 동일
- fallback 1은 그대로 유지

성능은 correctness audit의 결과이지 새로운 paid candidate의 승격 근거가 아니다. 예상대로
`TP>=1, FP<=3`이 되더라도 serialization fallback을 별도 해결하기 전에는 holdout을 실행하지 않는다.
