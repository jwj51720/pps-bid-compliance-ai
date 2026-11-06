# S011 — 제품·기업범위 Python owner 단계 기여 감사 계획

상태: zero-call counterfactual 진단 계획

## 질문

S007은 v10~v18 Python funnel이 dev와 비라벨 모집단에서 얼마나 다르게 발화하는지 보였지만,
shift가 있다는 이유만으로 final owner를 제거하면 안 된다. 각 refinement가 dev에서 초기 판정을
몇 개 바로잡고 몇 개 망가뜨렸는지, 그리고 positive-F1 관점에서 추가 양성 집합이 어느 정도까지
precision 하락을 견딜 수 있는지를 먼저 계산한다.

S011은 hash-pinned L41 내부의 동일 `r2_absence.predict`를 dev200에 재생해 초기 v10/v11/v16/v17/v18
셀을 복원하고, S001 final 셀과 비교한다. v12/v13/v14는 대체 owner가 없으므로 final owner를 0으로
제거하는 극단 counterfactual만 산술적으로 기록한다. 새로운 label rule이나 prediction을 만들지
않는다.

## 변경 통제

- base config: `experiments/manifests/clean_exp_s010_v3_population_morphology_audit_v1.json`
- allowed change: `python_owner_stage_attribution_audit` 추가만
- frozen import: hash-pinned loader를 통해서만 사용
- LLM/BGE calls: 0
- output: `outputs/clean-exp-s011-python-owner-stage-attribution-v1/`
- submission/policy change: 없음

## 수학적 판정

기존 `TP=A, FP=B, FN=C`인 owner에 0→1 expansion이 `t`개의 TP와 `f`개의 FP를 추가하면,
positive F1이 개선되는 필요충분조건은 다음과 같다.

```text
t / (t + f) > A / (2A + B + C) = F1_before / 2
```

즉 추가 집합 precision이 기존 F1의 절반보다 높으면 FP가 TP보다 많더라도 F1은 개선될 수 있다.
S011은 item별로 다음을 기록한다.

- initial/final TP, FP, FN, precision, recall, F1
- 0→1 중 true/false additions와 expansion precision
- 1→0 중 corrected FP와 lost TP
- `F1_before/2` 임계값과 관측 margin
- 해당 item 하나만 initial로 되돌릴 때 dev Macro 변화
- S007 population funnel rate와 그 단계가 BGE 미실행 upper bound인지 여부

## gate와 해석 경계

1. dev 200건과 v10/v11/v16/v17/v18 initial/final 셀을 모두 계산한다.
2. frozen ZIP, frozen script, dev input, final submission, S007 report SHA-256을 기록한다.
3. API/embedding calls 0, final prediction false를 명시한다.
4. stage transition 합계가 initial/final positive count 차이와 일치해야 한다.
5. single-item rollback의 Macro 산술이 `(F1_initial-F1_final)/24`와 일치해야 한다.
6. dev 추가집합 precision은 adaptive-development 관측일 뿐 public precision 추정치가 아니다.
7. population no-BGE survivor는 final activation이 아니라 upper-bound funnel이다.
8. shift만 크거나 local net benefit만 작다는 이유로 owner를 제거하지 않는다. 제거 후보는 source
   truth-condition 결함과 수학적 취약성이 함께 확인되어야 한다.

이 감사의 목적은 과적합을 무조건 덜어내는 것이 아니라, 제거로 F1을 더 망칠 owner와 실제로
취약한 owner를 구분하는 것이다.
