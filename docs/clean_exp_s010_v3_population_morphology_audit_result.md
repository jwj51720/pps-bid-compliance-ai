# S010 — v3 source-view 모집단 형태 감사 결과

실행일: 2026-09-23

상태: **PASS — v3 specialist의 모집단 source-role 혼합 증가 확인, 정책 변경 없음**

## 실행과 coverage

- dev: 200 records / 374 documents / 100 candidates / 61 routed notices
- organizer 비라벨 모집단: 20,000 records / 38,862 documents / 6,484 candidates /
  4,084 routed notices
- LLM calls: 0
- embedding calls: 0
- final prediction / pseudo-label: 없음
- runtime: 11.11초
- preflight undeclared differences: 0
- 결과: `outputs/clean-exp-s010-v3-population-morphology-audit-v1/audit_report.json`

입력, dev 저장 observation, basis replay, active v3 view module의 SHA-256을 결과에 기록했다.
candidate는 기존 `build_v3_monetary_view`를 그대로 실행해 모든 문서에서 `실적`과 금액이 함께
있는 exact window를 만들었다. 감사용 morphology는 source review 층화일 뿐 label rule이 아니다.

## notice-level 이동

| feature | dev200 | population 20k | dev/pop RR |
|---|---:|---:|---:|
| candidate route | 30.50% | 20.42% | 1.494 |
| multi-candidate route | 13.50% | 7.005% | 1.927 |
| qualification surface | 18.50% | 9.94% | 1.861 |
| single-contract surface | 14.00% | 6.685% | 2.094 |
| aggregate surface | 13.50% | 8.155% | 1.655 |
| aggregate without single surface | 6.00% | 5.275% | 1.137 |
| candidate amount above estimate | 18.50% | 13.95% | 1.326 |
| attachment candidate route | 16.00% | 12.465% | 1.284 |

dev는 v3 source route와 명시적인 참가자격·단일건 표현이 모집단보다 훨씬 농축돼 있다. 반면
`aggregate_without_single_surface`의 전체 공고 비율은 6.00% 대 5.275%로 가깝다. 마지막 한
셀을 고친 AGGREGATE 표현만 특별히 모집단에서 사라진다는 증거는 없다.

## routed candidate 내부의 난이도 이동

| candidate feature | dev 100 | population 6,484 | 차이 |
|---|---:|---:|---:|
| evaluation surface | 62.00% | 75.123% | population +13.123%p |
| form surface | 38.00% | 46.129% | population +8.129%p |
| qualification + form 동시 표면 | 13.00% | 20.635% | population +7.635%p |
| parsed amount 중 estimate 초과 포함 | 48.00% | 58.560% | population +10.560%p |
| qualification surface | 48.00% | 42.212% | population -5.788%p |
| single surface | 42.00% | 32.465% | population -9.535%p |
| aggregate surface | 32.00% | 30.691% | population -1.309%p |
| aggregate without single | 12.00% | 18.014% | population +6.014%p |

문서유형 분포의 total variation은 0.0539로 작았다. 즉 모집단에 제안요청서가 조금 더 많아서만
생긴 차이가 아니다. candidate 금액관계 분포의 TV는 0.1311이고, 모집단은 평가·서식 문구에
추정가격보다 큰 숫자가 같이 나타나는 비율이 더 높다. v3의 핵심 실패 모드는 금액 파싱보다
그 금액이 **입찰 참가요건인지 평가/서식인지** 구분하는 역할 판정이다.

공고당 candidate 수는 routed notice 기준 dev `100/61=1.639`, population
`6484/4084=1.588`로 비슷하다. 문제는 후보 수 폭증이 아니라 후보의 의미 혼합이다.

## 고정 표본 source review

`candidate_route` 모집단 active ID를 SHA-256 순으로 고정한 첫 8건의 exact candidate window를
읽었다.

- 적격심사 이행실적 평가금액
- 제안서 수행실적 서식
- 정량평가의 누적 용역비·실적 건수
- 평가용 실적증명서와 자기평가표

등이었고, **8/8이 평가 또는 서식 역할이며 입찰 참가자격 금액 제한은 0/8**이었다. 이는 모집단
후보가 role-negative 문맥을 다량 포함한다는 정성 확인이다. 표본은 label로 고르지 않았고 결과
JSON에는 원문을 복제하지 않았다.

## dev 저장 observation과 AGGREGATE 해석

dev 저장응답 98 observations 중 Gemma 분류는 다음과 같다.

- `BID_QUALIFICATION`: 20
- `EVALUATION`: 38
- `FORM`: 23
- `OTHER`: 15
- `EXPERIENCE_DESCRIPTION`: 2

입찰참가 필수라고 본 18 notices 중 AGGREGATE가 있는 것은 4 notices였다. v2 reducer replay가
실제 최종 v3를 바꾼 것은 `PPS-DEV-059` 한 셀뿐이다. AGGREGATE candidate 비율은 dev 32.0%,
population 30.69%로 안정적이고, aggregate-without-single의 전체 notice 비율도 안정적이다.

따라서 다음 두 명제를 구분한다.

1. `AGGREGATE`를 허용한 선택 과정은 한 dev FN을 본 뒤 이루어져 adaptive였다.
2. 그렇다고 AGGREGATE를 자동 0으로 되돌리는 것은 organizer truth condition에 없는
   single-contract 조건을 다시 발명하는 것이므로 일반화-safe correction이 아니다.

S010은 reducer-only rollback의 근거를 만들지 못했다.

## 수학적 판단과 다음 조치

dev에서 specialist FP는 routed 61건 중 1건이었다. 이 관측 오분류율 `1/61=1.64%`를 모집단
route 20.42%와 test 1,853건에 기계적으로 곱하면 약 378 routed calls와 약 6.2 FP라는 거친
규모가 나온다. 이는 독립 오차·동일 분포를 가정한 계산이라 추정치로 승격할 수 없지만, v3
양성이 희소하면 몇 FP만으로도 positive-F1이 크게 무너질 수 있음을 보인다. 더구나 모집단 후보는
dev보다 평가/서식 혼합이 높으므로 동일 오분류율 가정도 낙관적일 수 있다.

결론:

1. S001의 v3 dev F1 `0.941176`을 일반화 기대값으로 사용하지 않는다.
2. AGGREGATE만 lexical gate로 되돌리지 않는다.
3. 다음 public 식별 실험은 이미 완성된 S005 **v3 specialist 전체 단독 제거**가 가장 작은
   one-change ablation이다. v19, 지역금액, 다른 owner를 섞지 않는다.
4. S005는 dev Macro를 `0.8151466 → 0.7910824`로 낮추고 initial logical calls를
   `661 → 600`으로 줄인다. public 변화의 절댓값은 한 item 한계 `1/24=0.041667` 이내다.
5. 이 ablation은 상위권과의 `0.145+` 차이를 해결할 개선안이 아니라 v3 overlay의 public
   부호를 식별하는 실험이다. 병행 연구는 큰 headroom과 명시적 local defect가 있는 v24 및
   저가/소액수의 Python owner의 source-role 구조를 다룬다.

재현:

```bash
python scripts/preflight_experiment.py --config experiments/manifests/clean_exp_s010_v3_population_morphology_audit_v1.json
python scripts/audit_v3_population_morphology.py --config experiments/manifests/clean_exp_s010_v3_population_morphology_audit_v1.json
python -m pytest -q tests/test_v3_population_audit.py
```
