# S011 — 제품·기업범위 Python owner 단계 기여 감사 결과

실행일: 2026-09-23

상태: **PASS — v10/v16/v17/v18 wholesale rollback 기각, 정책 변경 없음**

## 실행 무결성

- dev: 200/200 records
- frozen ZIP/script hash: 기록 및 검증
- S001 final submission, dev labels, S007 population report SHA-256: 기록
- LLM/BGE calls: 0
- transition count integrity: PASS
- preflight undeclared differences: 0
- runtime: 약 2.5초
- 결과: `outputs/clean-exp-s011-python-owner-stage-attribution-v1/audit_report.json`

hash-pinned L41 loader로 frozen `r2_absence.predict`를 그대로 실행해 초기 셀을 복원했고, S001
final 셀과 대조했다. 이는 새 prediction 또는 submission이 아니라 저장 정책의 단계별 attribution이다.

## F1 expansion 판정식

초기 `TP=A, FP=B, FN=C`에서 0→1 expansion이 `t`개 TP와 `f`개 FP를 추가한다면 F1 개선의
필요충분조건은 다음과 같다.

```text
precision_added = t / (t + f)
precision_added > A / (2A + B + C) = F1_initial / 2
```

따라서 추가 FP 수가 TP 수보다 많다는 사실만으로 expansion을 제거하면 안 된다. 기존 recall이
매우 낮으면 비교적 낮은 추가 precision도 F1을 높인다.

## initial → final 전이

| item | initial F1 | final F1 | 0→1 true/false | 추가 precision | 필요 precision | rollback Macro |
|---|---:|---:|---:|---:|---:|---:|
| v10 | 0.0000 | 0.9333 | 7 / 1 | 87.50% | 0.00% | -0.038889 |
| v11 | 0.6667 | 0.6667 | 0 / 0 | 해당 없음 | 33.33% | 0 |
| v16 | 0.2857 | 0.8000 | 5 / 3 | 62.50% | 14.29% | -0.021429 |
| v17 | 0.2857 | 0.6316 | 5 / 7 | 41.67% | 14.29% | -0.014411 |
| v18 | 0.2500 | 0.7778 | 6 / 4 | 60.00% | 12.50% | -0.021991 |

v10은 0→1 여덟 건 외에도 기존 FP 한 건을 1→0으로 바로잡았다. v11은 refinement 전후 변화가
없다. v16/v17/v18은 모두 순수 expansion이다.

관측 추가 precision이 임계까지 하락할 수 있는 상대 폭은 v16 약 77.1%, v17 약 65.7%, v18
약 79.2%다. 이는 public 보장을 뜻하지 않지만, 단순 분포 이동만으로 whole-owner rollback을
정당화하려면 매우 큰 precision 붕괴를 추가로 가정해야 함을 뜻한다.

## S007 모집단 funnel과 결합

- v16 no-BGE survivor: dev 4.50%, population 2.415%, RR 1.863
- v17 no-BGE survivor: dev 9.00%, population 7.16%, RR 1.257
- v18 no-BGE survivor: dev 6.00%, population 4.235%, RR 1.417

v16은 큰 shift지만 모집단 발화가 **더 적은 방향**이다. 즉 dev에서 선택한 expansion precision이
public에서 낮아질 가능성은 남지만, 잘못된 expansion에 노출되는 절대 route가 증가한다는 증거는
아니다. v17·v18은 사전 large-shift gate를 넘지 않았다. 세 값은 BGE 미실행 upper bound이며 final
activation으로 부르지 않는다.

v10의 S007 `r2_initial_v10`은 dev 0.5%, population 2.0%지만 final v10은 BGE bridge가 추가되므로
이 비율로 final public activation을 추정할 수 없다. v11은 initial이 final이며 dev 1.5%, population
0.735%다.

## 대체 owner 없는 v12~v14

zero-owner 극단 counterfactual은 다음 local 손실을 만든다.

| item | final TP/FP/FN | final F1 | zero rollback Macro |
|---|---:|---:|---:|
| v12 | 3/0/3 | 0.6667 | -0.027778 |
| v13 | 5/1/1 | 0.8333 | -0.034722 |
| v14 | 7/0/1 | 0.9333 | -0.038889 |

S007의 route shift 때문에 이 owner들의 dev 수치를 일반화 성능으로 믿을 수는 없다. 하지만 대체
semantic owner 없이 0으로 지우는 것은 검증된 TP를 모두 잃으므로 일반화 전략이 아니다.

## 결정

1. v10/v16/v17/v18을 initial R2로 wholesale rollback하지 않는다.
2. v11은 단계 변화가 없어 제거할 refinement가 없다.
3. v12/v13/v14를 대체 owner 없이 0으로 만들지 않는다.
4. S007의 scope/product 결함은 계속 실제 문제지만, 해결은 final owner 삭제가 아니라 role·제품
   적용성을 source-grounded semantic candidate로 넘기는 최소 item 실험이어야 한다.
5. 현재 제거 근거가 가장 강한 것은 dev-adaptive하고 모집단 role 혼합이 확인된 v3 specialist다.
6. 다음 zero-call 감사는 두 번째 adaptive overlay인 v19의 candidate morphology와 runtime/local
   기여를 다룬다. v19는 dev200에서 165 specialist calls를 추가했으므로 일반화와 runtime 양쪽의
   기대효용을 확인할 필요가 있다.

재현:

```bash
python scripts/preflight_experiment.py --config experiments/manifests/clean_exp_s011_python_owner_stage_attribution_v1.json
python scripts/audit_python_owner_stage_attribution.py --config experiments/manifests/clean_exp_s011_python_owner_stage_attribution_v1.json
python -m pytest -q
```
