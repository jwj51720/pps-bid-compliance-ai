# S015 — 동일 task 독립 재호출 안정성 감사 결과

실행일: 2026-09-23

상태: **PASS — specialist reducer 안정성 확인, base arm repeat 증거 부재 확인**

## 무결성

- v3 identical task hash pairs: 10/10
- v19 identical task hash pairs: 17/17
- 두 response 모두 semantic parse valid: v3 10/10, v19 17/17
- external calls: 0
- preflight undeclared differences: 0
- 결과: `outputs/clean-exp-s015-exact-repeat-stability-audit-v1/audit_report.json`

동일 task 여부는 response 파일명이나 공고 ID가 아니라 기존 preflight의 tokenizer task SHA-256으로
검증했다. 각 pair는 같은 messages/schema/model parameter에 대한 서로 다른 저장 생성이다.

## 결과

| owner | pairs | content different | semantic field changes | final V changes |
|---|---:|---:|---:|---:|
| v3 keyed specialist | 10 | 5 (50.0%) | amount 3, basis 1 | 0 (0%) |
| v19 relation specialist | 17 | 16 (94.1%) | 다수 role/obligation field | 1 (5.9%) |

v3는 amount surface나 aggregate/single basis 표현이 달라도 최종 threshold relation이 모두 같았다.
이는 candidate-keyed observation + deterministic reducer가 생성 표면 변동을 흡수한다는 증거다.

v19는 typed field 자체가 자주 달랐지만 최종 V는 16/17건에서 같았다. 유일한 불일치는
`PPS-DEV-051`이었다.

```text
fast repeat: v19=0
dev repeat : v19=1
truth      : v19=0
```

dev repeat에서는 external issuer와 bid submission relation을 positive로 해석해 FP가 됐다. v19가
dev에서 가진 FP 4건 중 하나가 동일 task 재생성에 따라 바뀌므로, 현재 dev F1 0.75에는 generation
variance가 섞여 있다. 반대로 TP `PPS-DEV-036`은 두 repeat에서 모두 1이었다.

## 의미

1. response string equality는 매우 낮아도 deterministic reducer 뒤 V 안정성은 훨씬 높다.
2. S014에서 v3/v19를 rollback하지 않기로 한 결론과 양립한다. 특히 v3는 repeat final 10/10 일치다.
3. v19는 positive-only confirmation의 가능성이 있다. 전체 v19를 두 번 호출하지 않고 첫 pass
   positive만 동일 task로 재확인하면 예상 추가 호출은 positive rate에 비례한다.
4. 그러나 overlap positive는 두 건뿐이므로 바로 submission policy로 승격하지 않는다. 저장 dev
   positive 10건 중 아직 독립 repeat가 없는 8건을 사전 고정해 진단해야 한다.
5. r10/B/C24는 독립 identical-task repeat가 하나도 없다. local-public 괴리의 대부분을 담당하는
   base 22개 owner의 generation robustness는 아직 미검증이다.

## 다음 단계

- S016: v19 dev primary positive 10건을 고정하고, 기존 repeat 두 건은 재사용하며 나머지 8건만 exact
  task로 한 번 재호출한다.
- gate는 TP/FP별 repeat-positive rate, consensus F1, malformed, token/runtime다.
- 이것은 adaptive dev diagnostic이며 fast/holdout 독립 성능이라고 부르지 않는다.
- 효과가 구조적으로 보이면 positive-only confirmation을 fixed fast/holdout 정책으로 별도 검증한다.
- base generation gap은 그 다음에 r10/B/C24의 작은 hash-fixed exact-repeat panel로 검사한다.

재현:

```bash
python scripts/preflight_experiment.py --config experiments/manifests/clean_exp_s015_exact_repeat_stability_audit_v1.json
python scripts/audit_exact_repeat_stability.py --config experiments/manifests/clean_exp_s015_exact_repeat_stability_audit_v1.json
python -m pytest -q
```
