# S012 — v19 specialist 모집단 형태·효용 감사 결과

실행일: 2026-09-23

상태: **PASS — v19 owner 유지, v19-only rollback의 우선순위 하향**

## 실행 무결성

- dev: 200/200 records, 374 documents, 372 candidates
- organizer 비라벨 모집단: 20,000/20,000 records, 38,862 documents, 34,787 candidates
- 모든 제공 문서를 동일 `v19-requirement-instance-view-v1`으로 검사
- 입력·view·저장 observation·base/final CSV SHA-256 기록
- LLM/BGE calls: 0
- preflight undeclared differences: 0
- 단위 테스트: 3 passed
- runtime: 약 8.3초
- 결과: `outputs/clean-exp-s012-v19-population-morphology-audit-v1/audit_report.json`

이 감사의 형태 표면은 source-review strata일 뿐 v19 label 또는 pseudo-label이 아니다.

## dev 기여의 수학적 크기

v19 native owner는 base B를 다음처럼 바꿨다.

| owner | TP | FP | FN | precision | recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| base B | 5 | 10 | 1 | 0.3333 | 0.8333 | 0.4762 |
| native v19 | 6 | 4 | 0 | 0.6000 | 1.0000 | 0.7500 |

셀 전이는 11건이다. 0→1 세 건 중 1 TP/2 FP였고, 1→0 여덟 건은 모두 기존 FP 제거였다.
0→1 expansion precision은 1/3이고 기존 F1을 높이는 데 필요한 임계는
`F1_base/2=0.238095`이므로 expansion 자체도 dev F1에 양의 기여를 했다. 전체 v19 교체를
되돌리면 dev Macro는 `0.0114087` 하락한다.

이 수치는 adaptive dev 증거이며 public F1 추정값이 아니다. 다만 v19를 제거하려면 적어도
FP 감소 구조가 모집단에서 사라진다는 별도 근거가 필요하다.

## 모집단 이동

| 단위 | 형태 | dev | 모집단 | dev/pop RR |
|---|---|---:|---:|---:|
| notice | candidate route | 82.50% | 76.10% | 1.084 |
| notice | external issuer | 14.50% | 8.635% | 1.679 |
| notice | supply/tech | 11.00% | 6.650% | 1.654 |
| notice | external+supply+bid | 7.50% | 4.300% | 1.744 |
| candidate | self/form without external supply | 88.44% | 88.54% | 0.999 |
| candidate | external+supply+bid | 5.108% | 3.346% | 1.526 |

candidate의 대부분이 자기서약·서식인 구조는 거의 동일하다. v19의 핵심 어려운 표면인 외부
발행자+공급/기술지원+입찰 문맥은 모집단에서 dev보다 **적게** 나타난다. candidate 문서유형 TV는
0.0852, candidate 수 band TV는 0.0708로 route 전체가 다른 문제로 바뀌었다고 볼 정도는 아니다.

따라서 발견된 large shift는 native owner를 불리하게 만드는 노출 증가가 아니다. label이 없으므로
precision 일반화를 증명하지는 못하지만, v19 whole-owner rollback의 분포 근거로도 사용할 수 없다.

## hash 고정 source review

`external+supply+bid` 모집단 표본 8건을 실제 원문으로 읽었다. 모두 anchor가 source에 있었고
candidate view가 관계 판단에 필요한 주변 문맥을 보존했다. 표본에는 다음처럼 서로 구별해야 하는
실제 유형이 함께 있었다.

- 계약 시 또는 계약 전 제출만 요구하는 제조사 공급/A/S 확약
- 적격심사 전 제출하는 제조사 공급·기술지원 확약
- 계약 후 10일 이내 제출하는 기술지원 확약
- 제조사 공급확약서를 “제출 가능한 업체”라는 자격 문구와 계약서류 시점으로 함께 적은 경우
- 자기 각서와 외부 공급확약이 같은 1,400자 window에 공존하는 경우

즉 단순 `확약서` 또는 `제조사` lexical positive는 다수 FP를 만든다. 발행자, 서류 종류, 입찰 전
보유/동시 제출, 낙찰·계약 후 제출을 분리하는 typed observation은 모집단 source에도 필요한
구조다. 표본 원문은 결과 JSON이나 문서에 복제하지 않고 ID만 보존했다.

## 호출·token 해석

submission에서 native v19는 candidate notice의 B를 **대체**하며 추가 호출이 아니다.

```text
예상 test native tasks = 1,853 × 0.761 ≈ 1,410
예상 test B tasks      = 1,853 - 1,410 ≈ 443
v19 owner total        = 1,853 calls
```

동일 dev candidate notice 165건의 저장 usage는 다음과 같다.

| owner | prompt | completion | total |
|---|---:|---:|---:|
| native v19 | 548,326 | 77,050 | 625,376 |
| base B | 963,221 | 3,008 | 966,229 |
| native - base | -414,895 | +74,042 | -340,853 |

native는 총 token이 약 35.3% 적지만 completion이 훨씬 길고 candidate 수별 schema가 backend batch를
분절한다. 저장 OpenRouter token으로 evaluator vLLM wall time을 선형 추정할 수는 없다. S001이
95분 27초에 완주했으므로 현재 증거만으로 v19를 runtime 때문에 제거하지 않는다. runtime 개선은
의미 owner 제거가 아니라 serialization-only 실험으로 분리한다.

## 결정

1. v19 native owner를 유지한다.
2. v19-only rollback을 다음 public ablation으로 제출하지 않는다.
3. v19의 dev 이득을 public 성능이라고 부르지 않는다. holdout에 v19 양성이 없었던 recall blind는
   여전히 limitation이다.
4. 모집단의 핵심 candidate 구조와 수작업 표본은 발행자·역할·시점 분해가 필요한 이유를 지지한다.
5. 첫 one-change public 식별 후보는 S005의 v3 specialist 전체 제거로 유지한다.
6. 품질 탐색은 한 항목 최대 `1/24` 한계를 고려해 v24와 저가·소액수의 공통 owner 감사를 계속한다.
7. v19 runtime을 건드릴 경우 reducer·view·truth condition을 고정하고 serialization만 바꾼다.

재현:

```bash
python scripts/preflight_experiment.py --config experiments/manifests/clean_exp_s012_v19_population_morphology_audit_v1.json
python scripts/audit_v19_population_morphology.py --config experiments/manifests/clean_exp_s012_v19_population_morphology_audit_v1.json
python -m pytest -q
```
