# EXP-C005D v19 requirement-instance dev200 결과

작성일: 2026-09-21

상태: PASS — 새 로컬 품질 baseline

## 핵심 결과

| 실험 | Macro positive-F1 | v19 TP/FP/FN | v19 F1 |
|---|---:|---:|---:|
| C004S 이전 baseline | 0.8037378357 | 5 / 10 / 1 | 0.4761904762 |
| C005D | **0.8151465658** | **6 / 4 / 0** | **0.7500000000** |

- Macro delta: **+0.0114087302**
- v19: 기존 TP 5개 전부 보존, FN 1개 회복, FP 순 6개 감소
- non-v19 label/evidence changed cells: 0
- final invalid responses: 0
- v19 positive without evidence: 0
- 200 rows × 49 columns, unique complete IDs: PASS

예측식
`0.8037378357 + (0.75 - 0.4761904762) / 24 = 0.8151465658`과 실제 결과가 정확히
일치한다. 따라서 점수 상승은 오직 선언한 v19 owner 교체에서 왔으며 변동 혼입이 없다.

## 호출과 completeness

- candidate notices / candidates: 165 / 372
- primary calls: 165
- overflow passes: 0
- runtime: 195.381초
- prompt tokens sum/max: 548,326 / 9,346
- completion tokens sum/max: 77,050 / 1,568
- primary semantic-invalid tasks: 0
- compact recovery calls: 0

이번 dev200에서는 primary 응답 165개가 모두 valid여서 compact recovery가 실제로 발동하지 않았다.
recovery 경로 자체는 C005HS holdout failure target에서 1회 실제 호출로 검증됐다. 즉 C005D 결과는
verbose primary semantics의 결과이며 compact schema가 정상 응답의 판정을 바꾸지 않았다.

## label 변화 감사

v19 label은 11건 변했다.

- true positive 추가: `PPS-DEV-036`
- false positive 제거: `PPS-DEV-050`, `057`, `096`, `112`, `133`, `152`, `158`, `178`
- false positive 추가: `PPS-DEV-051`, `190`

false positive 8개를 제거하고 2개를 새로 만들어 순 6개 감소했다. retained positive의 evidence도
긴 주변문맥 대신 판정을 직접 지지하는 짧은 exact span으로 교체됐다. 최종 v19 positive 10건의
evidence를 독립 재검사한 결과 모두 supplied document의 unchanged substring이고 500자 이하다.

## fallback 해석

report의 fallback 37건 중 35건은 exact admission candidate가 없어 C004S v19를 보존한 공고다.
나머지는 positive predicate evidence를 exact/unique-whitespace로 resolve하지 못해 fail-closed로
baseline을 보존한 경우다. invalid response나 Python label default는 아니다.

## 결론과 제한

C005D는 fast20에서 양성 recall, independent holdout20에서 음성 precision, dev200에서 양쪽을 모두
개선했고 transport completeness도 충족했다. 따라서 C005D를 새 로컬 품질 baseline으로 승격한다.

다만 165 notice-level calls는 품질 실험 topology다. 과거 2시간 submission timeout을 고려하면 이
구조를 곧바로 submission candidate로 부르지 않는다. 품질 policy의 승격과 evaluator runtime을
만족하는 배치/호출 구조는 별도 실험으로 다룬다.

## 재현 경로

- manifest: `experiments/manifests/clean_exp_c005d_v19_dev200_promotion_v1.json`
- output: `outputs/clean-exp-c005d-v19-dev200-promotion-v1/dev200/`
- run report: 위 output의 `run_report.json`
- recovery audit: 위 output의 `serialization_recovery.json`
- metrics: 위 output의 `metrics.json`
- submission CSV: 위 output의 `submission.csv`
- tests: 63 passed
