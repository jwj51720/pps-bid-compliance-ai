# S014 — dev200 성능의 organizer 20,000건 공변량 이동 스트레스 계획

상태: zero-call post-stratification 진단 계획

## 목적

S004는 dev200이 제한·일반경쟁, 1억원 이상, 첨부 공고를 과대표집하고 수의계약·1억원 미만을
과소표집함을 보였다. S007/S011은 개별 Python owner를 통째로 제거할 근거는 부족하다고 결론냈다.
S014는 두 사실을 연결한다. S001의 dev200 prediction/label을 고정한 채 organizer 비라벨 20,000건의
공고형태 분포로 post-stratification하여, local Macro와 item F1이 어느 방향으로 이동하는지 계산한다.

이는 public 성능 추정이 아니라 **covariate-shift stress test**다. 다음의 강한 가정이 성립할 때만
재가중 F1이 모집단 기대값과 연결된다.

```text
P(correct | fixed stratum, dev) = P(correct | fixed stratum, population)
```

dev가 adaptive development data이고 stratum 내부 표현 이동도 있으므로 이 가정은 검증되지 않았다.
결과는 owner 제거 순위를 정하는 위험 신호로만 사용한다.

## 변경 통제

- base config: `experiments/manifests/clean_exp_s013_v24_operational_surface_audit_v1.json`
- allowed change: `covariate_shift_stress_audit` 추가만
- LLM/BGE calls: 0
- prediction 변경: 없음
- output: `outputs/clean-exp-s014-covariate-shift-stress-v1/`

## 사전 고정 strata

label이나 prediction을 보기 전에 organizer metadata와 문서 개수만으로 아래 3개 이진축을 고정한다.

1. 계약방법: `수의` 포함이면 `direct`, 아니면 `competitive`
2. 입찰추정가격: `<100,000,000` 또는 `>=100,000,000`
3. 문서구조: 공고문 한 건만 있으면 `notice_only`, 둘 이상이면 `attachment`

총 8개 strata다. 금액 0도 organizer 입력값 그대로 `<100m`에 포함하며 임의 보정하지 않는다.

## 계산

dev stratum `s`의 record weight는 다음과 같다.

```text
w_s = P_population(s) / P_dev(s)
```

weighted TP/FP/FN으로 24개 positive-class F1과 Macro를 다시 계산한다. weight 평균은 1이 되도록
검증한다. `n_dev(s)=0, n_population(s)>0`인 cell은 추정하지 않고 unsupported population mass로
별도 기록한다.

weight 집중도는 다음 effective sample size로 기록한다.

```text
ESS = (sum_i w_i)^2 / sum_i w_i^2
```

각 item은 raw dev F1, weighted F1, 차이, 오류 weight가 가장 큰 strata를 기록한다. weighted F1이
낮아졌다는 이유만으로 owner를 자동 제거하지 않는다. 기존 source audit의 의미 결함과 함께
나타나는 item만 다음 one-change 후보가 된다.

## gate

1. dev 200/200, population 20,000/20,000과 S001 CSV/labels ID 완전 일치
2. 여섯 관측 strata와 두 unsupported strata를 모두 명시
3. supported population mass와 ESS 기록
4. raw metric이 저장 S001 metric과 machine precision으로 일치
5. 24개 item별 weighted confusion/F1 기록
6. bootstrap이나 독립 validation으로 과장하지 않음
7. 결과로 lexical correction, notice-specific rule, Python override를 만들지 않음
