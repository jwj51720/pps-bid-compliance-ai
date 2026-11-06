# S005 — S001 v3 specialist 단독 제거 결과

실행일: 2026-09-23

상태: **zero-call replay PASS — public ablation 후보, 아직 submission 아님**

## 결과

| cohort | S001 | v3 revert | 변화 |
|---|---:|---:|---:|
| fast20 | 0.7277777778 | 0.7069444444 | -0.0208333334 |
| holdout20 | 0.4305555556 | 0.3888888889 | -0.0416666667 |
| dev200 | 0.8151465658 | **0.7910823947** | -0.0240641711 |

사전 산술과 실제 dev200 Macro가 machine precision으로 일치했다. v3는
`TP/FP/FN=8/1/0, F1=.941176`에서 reference r10의 `2/1/6, F1=.363636`으로 돌아갔다.
변경은 v3 8셀, e3 10셀뿐이며 다른 23개 v/e는 보존됐다. final CSV 200×49와 evidence cleaner를
통과했다.

## runtime 영향

- dev200 initial logical calls: `661 → 600`, 61 calls 감소
- S004 organizer 모집단 v3 route 20.42%를 test 1,853건에 단순 적용한 계획값:
  약 378.34 calls 감소
- 실제 evaluator runtime 감소량은 측정하지 않았으며 선형 비례를 주장하지 않는다.

## 해석

이 결과의 local 하락은 의도된 것이다. dev 오류를 보고 만든 specialist를 제거하는 실험이므로
adaptive dev200을 다시 최대화하는 것이 목적이 아니다. S004에서 v3 route가 dev에 1.49배
과대표집됐고, S001 public 괴리를 두 item local gain만으로 설명할 수 없다는 점 때문에
v3-only revert는 다음 public에서 specialist 효과를 식별하는 가장 작은 ablation이다.

다만 reference r10 v3의 recall이 dev에서 25%뿐이므로, public 근거 없이 곧바로 제출하면 실제
v3를 크게 잃을 수 있다. 이 후보의 최대 public 개선·손실 절댓값은 한 item이므로 `1/24=.041667`다.
5위권 하단 0.75와의 차이 약 0.14465를 단독으로 메울 수 없다.

## 다음 결정 gate

1. hash-pinned original reference ZIP의 정확한 public 점수를 확인한다.
2. 동일 artifact 점수가 0.688686보다 높았다면 v3/v19만으로 차이를 설명할 수 없으므로,
   v3 revert 제출 전에 base runtime parity 원인을 함께 추적한다.
3. 제출한다면 지역금액 correction이나 다른 owner 변경을 섞지 않는다.
4. 병행 연구는 모집단 다수인 소액수의·1억원 미만 strata의 base owner source-role 감사다.

재현:

```bash
python scripts/preflight_experiment.py --config experiments/manifests/clean_exp_s005_v3_revert_ablation_v1.json
python scripts/run_v3_revert_ablation.py
python -m pytest -q
```
