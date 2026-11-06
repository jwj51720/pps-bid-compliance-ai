# S013 — v24 operational surface·오류군 모집단 감사 결과

실행일: 2026-09-23

상태: **PASS — C24 direct verdict 고위험 확인, prompt 재튜닝 및 evidence-label veto 기각**

## 실행 무결성

- dev: 200/200 records, 모든 374 documents 검사
- organizer 비라벨 모집단: 20,000/20,000 records, 모든 38,862 documents 검사
- 동일 `native-v24-multi-observation-view-v2`와 축별 6,850자 source budget 사용
- 입력·labels·S001 submission·view module SHA-256 기록
- preflight undeclared differences: 0
- LLM/BGE calls: 0
- 단위 테스트: 5 passed
- runtime: 약 19초
- 결과: `outputs/clean-exp-s013-v24-operational-surface-audit-v1/audit_report.json`

source surface는 값의 역할이나 불일치를 확정하지 않으며 모집단 pseudo-label이 아니다.

## C24 오류의 수학적 상태

| TP | FP | FN | TN | precision | recall | F1 | predicted positive rate | label prevalence |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 44 | 3 | 148 | 10.20% | 62.50% | 0.175439 | 24.50% | 4.00% |

v24를 완벽히 고칠 때 전체 Macro 상한은 `(1-0.175439)/24=0.034357`이다. 중요하지만 이 한
항목만으로 public `0.60535`에서 5위권 하단 `0.75`까지의 `0.14465` 차이를 메울 수는 없다.

## 입력 누락이 주원인인가

아니다. dev 오류군의 surface coverage는 다음과 같다.

| feature | TP | FP | FN | TN |
|---|---:|---:|---:|---:|
| 네 축 모두 comparable | 60.0% | 52.3% | 66.7% | 36.5% |
| 어떤 축이든 multi-candidate | 100% | 100% | 100% | 98.0% |
| 어떤 축이든 attachment candidate | 0% | 50.0% | 0% | 44.6% |
| 어떤 축이든 budget UNOBSERVED | 0% | 9.1% | 0% | 10.1% |

UNOBSERVED는 FP보다 TN에서 오히려 약간 많았다. attachment와 multi-candidate도 FP만의 특징이
아니다. 따라서 C24의 44 FP를 source omission이나 tokenizer admission 하나로 설명할 수 없다.
문제의 중심은 여러 문구 중 metadata 대응 공식값을 정하는 우선순위, 계약방법과 낙찰방법의 구별,
지역/업종 제한의 organizer operational annotation 범위다.

## C24가 양성을 만든 evidence surface

문구 자체에 포함된 축 표면만 센 결과다. semantic reason을 추측하지 않는다.

| evidence surface | TP | FP |
|---|---:|---:|
| amount | 1 | 2 |
| contract | 1 | 9 |
| region | 0 | 13 |
| industry | 2 | 6 |
| unclassified | 1 | 14 |

지역 evidence는 dev에서 13개 모두 FP였다. 그러나 이를 근거로 region을 Python veto하면 안 된다.
항목표가 지역축을 명시하고 있으며 label 양성은 8건뿐이다. 대신 direct C24가 지역 제한 문구의
존재 또는 표현 차이를 metadata contradiction으로 과잉 해석한다는 강한 진단 신호다.

## strict evidence counterfactual과 기각

C24 positive 49건 중 4건은 생성 응답에 인용문이 있었지만 exact source substring resolution에
실패해 최종 `e24`가 비었다. 그런데 assembly는 `v24=1`을 그대로 보존했다. 네 건은 모두 FP였다.

```text
initial: TP/FP/FN = 5/44/3, F1 = 0.1754385965
strict : TP/FP/FN = 5/40/3, F1 = 0.1886792453
Macro delta = +0.0005516937
```

그러나 이 국소 개선을 label policy로 승격하지 않는다. S001 전체 전수 감사에서 v15에도 최종
evidence가 빈 positive 두 건이 있었고 둘 다 TP였다. 이를 전 항목 strict gate로 내리면 v15 F1은
하락한다. 또한 C24 네 응답의 생성 인용은 모두 실제 source와 의미상 대응했고, 세 건은 whitespace
제거만으로, 나머지 한 건은 구두점 제거까지 하면 source에서 찾을 수 있었다. 즉 이것은 source 없는
hallucination이라기보다 exact resolver의 표면형 실패다.

따라서 v24 네 FP만 0으로 내리면 dev label을 본 adaptive veto가 된다. V는 그대로 두고 evidence를
유일한 원문 span으로 복구할 수 있는지 별도 serialization/evidence 실험에서 검증해야 한다. 위
counterfactual은 크기 비교용으로만 보존하며 S014 label correction은 만들지 않는다.

## dev FN source review

FN 세 건을 네 축 원문과 metadata로 다시 읽었다.

- 한 건은 metadata 지역과 참가업체 지역 집합이 달라 기존 C002R multi-observation이 실제로 회수한
  표현 가능한 relation이다.
- 나머지 두 건은 현재 view에서 금액·계약방법·지역·업종의 명시값이 일치하거나, 대응 source가
  없었다. organizer가 제공한 네 축의 단순 값 불일치만으로 label 1을 설명할 수 없었다.

따라서 네 축 array schema를 더 크게 만드는 것만으로 recall 100%에 도달할 수 없다. 알려진 FN
문구를 새 축이나 예외로 넣는 것은 dev 과적합이므로 하지 않는다.

## 모집단 이동

가장 큰 이동은 지역축이다.

| feature | dev | 모집단 | dev-pop |
|---|---:|---:|---:|
| region candidate/comparable | 44.50% | 57.17% | -12.67%p |
| region multi-candidate | 16.00% | 26.645% | -10.645%p |
| region attachment candidate | 4.50% | 8.045% | -3.545%p |

region candidate-count band TV는 0.1267로 네 축 중 가장 컸다. dev에서도 region evidence positive가
0 TP/13 FP였는데 모집단에서는 지역 후보와 복수 후보 노출이 더 많다. 이는 public 정확도를
직접 측정한 값은 아니지만, 현재 C24 direct verdict의 과잉 양성 위험이 감소한다고 볼 근거가 없다.

## 결정

1. C24 prompt를 dev 오류에 맞춰 다시 다듬는 실험을 중단한다.
2. v24 multi-observation 계열을 즉시 dev200으로 확장하지 않는다. 네 축만으로 설명되지 않는 FN이
   남고 operational annotation 범위가 불명확하다.
3. strict evidence 실패를 V=0으로 바꾸는 S014는 기각한다. evidence resolver 개선은 label 불변의
   별도 serialization/evidence 변경으로만 검토한다.
4. 다음 public one-change 후보는 여전히 S005 v3 specialist 제거다.
5. v24는 높은 headroom 때문에 버리지는 않지만, 다음 재개 조건은 organizer 제공 source에서
   operational truth의 더 좁은 정의를 증명하거나 새 public ablation으로 C24 과잉 양성을 식별하는
   것이다.
6. 전체 일반화 개선은 v24 한 항목이 아니라 저가·소액수의에 공통된 v10~v18 owner와 generation
   환경 차이를 함께 다뤄야 한다.

재현:

```bash
python scripts/preflight_experiment.py --config experiments/manifests/clean_exp_s013_v24_operational_surface_audit_v1.json
python scripts/audit_v24_operational_surface.py --config experiments/manifests/clean_exp_s013_v24_operational_surface_audit_v1.json
python -m pytest -q
```
