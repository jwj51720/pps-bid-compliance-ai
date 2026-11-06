# S005 — S001 v3 specialist 단독 제거 ablation 계획

상태: zero-call stored-row ablation. submission 후보 아님.

## 가설

S001의 v3 specialist는 알려진 dev 오류를 본 뒤 reducer까지 선택했고, S004에서 candidate route가
dev `30.50%`, organizer 20,000 `20.42%`로 `+10.08%p` 과대표집됐다. 반면 v19 route shift는
`+6.40%p`로 사전 large-shift gate를 넘지 않았다. 따라서 두 specialist를 함께 제거하기 전에
v3만 reference r10 owner로 되돌리면 가장 작은 단위로 local 기여와 runtime 감소를 고정할 수 있다.

이 실험은 public 향상을 증명하지 않는다. S001 stored final에서 v3/e3만 hash-pinned reference
stored row로 교체하는 counterfactual이며 새 모델 호출은 0회다.

## 변경 통제

- base: `experiments/manifests/clean_exp_s001_integrated_v3_v19_v1.json`
- allowed: v3 owner/view/reducer/recovery 비활성화, assembly의 v3 route 제거,
  runtime expected calls, `public_generalization_ablation` 기록
- 고정: v19 owner·responses·reducer, base 22 items, evidence cleaner, provider, batch/retry
- output: `outputs/clean-exp-s005-v3-revert-ablation-v1/`
- legacy import/execute: 0; frozen reference는 저장된 base row provenance로만 사용

## 사전 산술

```text
Macro_expected = 0.8151465658 -
                 (0.9411764706 - 0.3636363636) / 24
               = 0.7910823947
```

dev200 logical initial calls는 `661 → 600`이다. organizer 20,000 route rate를 test 1,853건에
단순 투영하면 v3 specialist 약 `1,853 × 0.2042 = 378.34` calls가 제거된다. 이는 test 분포가
20,000과 같다는 보장이 없는 계획값이다.

## gate

1. preflight undeclared diff 0.
2. 200 rows × 49 columns, ID/evidence validity PASS.
3. S001 대비 변경 필드는 v3/e3만; reference 대비 변경 필드는 v19/e19만.
4. 실제 Macro와 사전 산술 일치.
5. 이 결과만으로 canonical 또는 제출 승격 금지. exact reference public artifact 대응 또는
   다음 public one-change ablation 여부를 별도로 결정한다.
