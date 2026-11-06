# S013 — v24 operational surface·오류군 모집단 감사 계획

상태: zero-call source/metadata 일반화 진단 계획

## 질문

S001의 C24 owner는 dev200에서 `TP/FP/FN=5/44/3`, F1 `0.175439`다. v24를 완벽하게
고쳐도 전체 Macro 상한은 `+0.034357`이지만, 단일 item 중 가장 크다. 기존 C002R은 복수값
관계를 도입해 fast20에서 양성 한 건을 회수했으나 다음 모순을 확인했다.

- metadata와 원문의 명시적 지역/계약 값이 달라도 label 0인 사례가 있었다.
- 네 축의 값이 모두 일치하거나 비교 불가인데도 label 1인 사례가 있었다.
- amount unit, 계약방법 우선순위, 제품번호/업종 역할이 typed extraction에서 혼동됐다.

따라서 새 prompt를 만들기 전에 organizer가 제공한 네 metadata 축과 실제 문서 source surface가
dev 오류군 및 20,000건에서 어떤 관측 구조를 갖는지 측정한다. 목적은 v24 정답을 lexical하게
재현하는 것이 아니라, 현재 truth condition을 표현할 입력이 존재하는지와 C24 FP가 어느 구조에
집중되는지를 판별하는 것이다.

## 변경 통제

- base config: `experiments/manifests/clean_exp_s012_v19_population_morphology_audit_v1.json`
- allowed change: `v24_operational_surface_audit` 추가만
- LLM/BGE calls: 0
- final prediction / pseudo-label: 없음
- active import: `src.pps_ai`만 사용
- output: `outputs/clean-exp-s013-v24-operational-surface-audit-v1/`

## 동일 source view

기존 `native-v24-multi-observation-view-v2`를 변경 없이 dev와 모집단 전체에 실행한다. 각 축에서
다음을 notice 단위로 센다.

1. metadata 대응값의 입력 상태
2. exact source candidate 유무
3. candidate가 둘 이상인 복수값 가능 surface
4. 첨부문서 candidate 유무
5. source budget 때문에 `UNOBSERVED`가 생겼는지
6. metadata와 source candidate가 모두 있는 comparable surface

이는 source availability이고 실제 값의 일치/불일치나 v24 label이 아니다. 모델 없이 역할을
확정하거나 문자열을 비교해 새로운 prediction을 만들지 않는다.

## dev 오류군 분석

S001 final CSV와 dev label로 C24의 TP/FP/FN/TN만 평가용으로 나눈다. 각 오류군에 대해 위 feature의
비율과 축별 candidate-count band를 기록한다. selector나 label rule에는 dev label을 사용하지 않는다.

오류군 feature enrichment는 다음과 같이 계산한다.

```text
RR(FP vs TN) = P(feature | FP) / P(feature | TN)
RR(FN vs TP) = P(feature | FN) / P(feature | TP)
```

표본이 작은 경우 RR를 성능 추정으로 부르지 않으며, 분모 0은 `null`로 기록한다. baseline C24
positive 49건과 true positive 8건의 ID는 hash 고정 source-review 표본을 고르는 데만 쓴다.

## 모집단 비교 gate

1. dev 200/200, population 20,000/20,000과 모든 제공 문서를 검사한다.
2. 입력·view·labels·S001 submission SHA-256을 기록한다.
3. notice 분모의 dev/pop rate, percentage-point 차이, RR를 기록한다.
4. `abs(rate difference)>=0.10` 또는 RR가 `[0.67,1.50]` 밖이면 large shift로 표시한다.
5. 축별 candidate-count band와 문서유형 분포의 total variation을 기록한다.
6. hash 고정 FP/FN/모집단 표본 ID만 결과에 남기고 원문을 복제하지 않는다.
7. label-free 모집단 morphology를 accuracy/F1/pseudo-label로 부르지 않는다.
8. C24 replacement는 이 감사만으로 만들지 않는다.

## 결정 기준

- FP가 multi-candidate·attachment·UNOBSERVED에 집중되면 C24는 full-value relation 입력이 부족한
  것이므로 현재 direct verdict owner를 유지할 근거가 약하다.
- FN이 `no comparable surface`에 집중되면 네 축 source view 또는 organizer operational definition이
  불완전하므로 새 extractor 호출을 중단하고 항목표/source semantics부터 재검토한다.
- 네 축 source morphology가 모집단에서 크게 이동하면 dev200 v24 튜닝을 public 기대값으로 쓰지 않는다.
- 다음 유료 실험은 이 감사가 가장 작은 표현 가능한 truth condition을 식별한 경우에만 한다.
