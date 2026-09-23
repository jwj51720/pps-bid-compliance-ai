# S014 — dev200 성능의 organizer 20,000건 공변량 이동 스트레스 결과

실행일: 2026-09-23

상태: **PASS — 단순 rollback 전부 기각, v17 precision 개선과 generation robustness 우선**

## 실행 무결성

- dev: 200/200, population proxy: 20,000/20,000
- fixed strata: 계약방법 2 × 입찰추정가격 2 × 첨부여부 2
- LLM/BGE calls: 0
- S001 raw Macro 재현: `0.8151465658238104`
- unsupported population mass: `0.00115` (23/20,000)
- mean dev record weight: `1.0`
- effective sample size: `122.827`
- preflight undeclared differences: 0
- 결과: `outputs/clean-exp-s014-covariate-shift-stress-v1/audit_report.json`

## strata와 weight

| stratum | dev | population | record weight |
|---|---:|---:|---:|
| competitive, >=1억, attachment | 67 | 4,791 | 0.716 |
| competitive, >=1억, notice only | 27 | 853 | 0.316 |
| competitive, <1억, attachment | 39 | 4,351 | 1.117 |
| competitive, <1억, notice only | 32 | 1,044 | 0.327 |
| direct, <1억, attachment | 27 | 6,203 | 2.300 |
| direct, <1억, notice only | 8 | 2,735 | 3.423 |

dev에 없는 `direct, >=1억` 두 cell은 population 23건, 0.115%이며 추정에서 제외했다.

## weighted stress 결과

```text
raw dev Macro      = 0.8151465658
post-stratified    = 0.7953858534
difference         = -0.0197607124
observed public gap= -0.2097937663
```

강한 conditional-stability 가정 아래에서도 이 세 공변량의 mix 변화가 설명하는 하락은 관측
local-public 괴리의 약 9.42%다. 따라서 `수의계약·저가·첨부 비율이 달라서 0.815→0.605가 됐다`고
설명할 수 없다. 더 미세한 표현/역할 이동, adaptive selection, OpenRouter와 evaluator INT8 vLLM의
generation 차이가 남는다.

재가중 하락이 큰 항목은 다음과 같다.

| item | raw F1 | weighted F1 | delta |
|---|---:|---:|---:|
| v17 | 0.6316 | 0.4810 | -0.1506 |
| v19 | 0.7500 | 0.6064 | -0.1436 |
| v10 | 0.9333 | 0.8262 | -0.1071 |
| v23 | 0.8000 | 0.6936 | -0.1064 |
| v16 | 0.8000 | 0.7244 | -0.0756 |
| v13 | 0.8333 | 0.7697 | -0.0637 |
| v18 | 0.7778 | 0.7169 | -0.0608 |

v17의 weighted FP는 direct/<1억 strata가 가장 크게 기여했다. 이는 다음 의미 실험의 최우선
precision 대상이다. 다만 weighted 하락만으로 owner를 제거하지 않는다.

## one-change rollback 비교

동일 weight에서 실제 대체 owner를 비교했다.

| item | current weighted F1 | rollback/base weighted F1 | current advantage |
|---|---:|---:|---:|
| v3 specialist vs r10 | 0.9204 | 0.2668 | +0.6536 |
| v19 native vs base B | 0.6064 | 0.3720 | +0.2344 |
| v10 final vs initial | 0.8262 | 0.0000 | +0.8262 |
| v16 final vs initial | 0.7244 | 0.2420 | +0.4824 |
| v17 final vs initial | 0.4810 | 0.1214 | +0.3596 |
| v18 final vs initial | 0.7169 | 0.3869 | +0.3301 |

따라서 S005 v3 revert, v19 base 복귀, Python refinement wholesale rollback은 모두 일반화 성능
향상 후보로 기각한다. 특히 S005는 source-role 이동을 식별하는 public diagnostic일 수는 있어도,
하루 한 번뿐인 제출을 쓸 기대품질 후보가 아니다.

## 해석 한계

post-stratification은 각 coarse stratum 안에서 오류율이 dev와 population에 같다는 가정을 쓴다.
이는 입증되지 않았고 ESS도 122.8로 감소했다. raw/weighted F1 모두 adaptive dev label에서 나온
값이다. 그러므로 `0.7954`는 public 예상점수가 아니며 confidence interval도 아니다.

그럼에도 이 감사가 단순 빈도 비교보다 강한 이유는 같은 오류 셀에 organizer population weight를
직접 부여하고, 실제 rollback owner까지 같은 식으로 비교했기 때문이다. 그 결과 적어도 “최근
구조를 제거하면 일반화가 좋아질 것”이라는 가설은 현재 증거와 반대다.

## 결정

1. S005 v3-only revert를 다음 기대품질 public 후보에서 제외한다.
2. v19 native와 v10/v16/v17/v18 final refinement를 유지한다.
3. 다음 품질 후보는 v17 하나에서 direct/<1억 FP의 제품 적용성·기업범위·예외 관계를 source-grounded
   observation으로 검증하는 precision guard다. initial owner로 되돌리지 않는다.
4. v23은 두 번째 위험 항목으로 날짜 역할/interval source audit을 갱신한다.
5. 실제 public 괴리의 대부분은 coarse covariate mix로 설명되지 않으므로 evaluator generation
   robustness를 별도 축으로 감사한다. 저장 OpenRouter response 점수만으로 새 정책을 승격하지 않는다.
6. v17 semantic owner, generation/serialization 안정성, runtime 변경을 한 실험에 섞지 않는다.

재현:

```bash
python scripts/preflight_experiment.py --config experiments/manifests/clean_exp_s014_covariate_shift_stress_v1.json
python scripts/audit_covariate_shift_stress.py --config experiments/manifests/clean_exp_s014_covariate_shift_stress_v1.json
python -m pytest -q
```
