# Saved dev200 item-wise research upper bound

작성: 2026-09-15, dev / mac

## 목적

현재까지 저장된 complete-input 시대의 dev200 결과에서 각 v마다 관측된 최고 F1만 골랐을 때
어디까지 갈 수 있는지 계산한다. 이는 label을 보고 arm을 고르는 oracle 진단이며 runnable policy,
submission candidate 또는 Python merge 승인이 아니다.

재현:

```bash
.venv/bin/python scripts/analyze_dev200_item_upper_bound.py \
  --output outputs/dev200-item-upper-bound-20260915/report.json
```

필터는 EXP200 이상, Gemma 4 26B, input_count 200, non-mock, non-merged run이다. 현재 9개 run이
포함된다.

## 결과

item별 저장된 최고 결과를 모두 선택해도 Macro positive-F1은 **`.4202688401`**이다.

| 범주 | items | 관측 최고 F1 |
| --- | --- | --- |
| 매우 강함 | v2, v3, v21, v22, v19 | `1.0, 1.0, 1.0, .9091, .9231` |
| 중간 | v1, v4, v5, v7, v8, v9, v14 | `.7143, .3158, .7778, .5, .5, .5263, .5882` |
| 약함 | v10, v12, v15, v20, v23, v24 | `.1039, .4444, .25, .1316, .1667, .2353` |
| 관측 최고도 0 | v6, v11, v13, v16, v17, v18 | 모두 `0` |

현재 현실적인 composition 중 EXP262+EXP312는 `.3746082750`이고, runtime-부적합 EXP281까지
합친 연구 상한은 `.3800907311`이다. 따라서 현재 specialist 결과를 더 잘 조합하는 것만으로는
`.7`에 접근할 수 없다. item attention dilution은 실제 병목이지만 유일한 병목이 아니다.

## 방향 결정

1. v4/v5/v7/v14 specialist를 더 쌓는 방식은 local score를 조금 올리지만 호출 수를 증가시키고
   `.42` 부근의 관측 상한을 넘지 못한다.
2. 다음 큰 개선은 v6/v11/v13/v16/v17/v18의 zero-recall 적용성 문제와
   v10/v20의 과호출 precision 문제를 해결해야 한다.
3. 이 항목들은 제품 적용성 또는 absence truth condition을 포함한다. raw full catalog와
   unknown→일반제품 변환은 이미 FP를 폭증시켰으므로 반복하지 않는다.
4. V-only 다중 호출도 저장된 draft stage에서 `.109~.136`에 불과해 해결책이 아니다.
5. 다음 구조 후보는 공고 전체에서 `실제 계약대상`, `적용 제품 후보`, `기업범위 참가제한`,
   `명시 예외`, `부재 확인 범위`를 source-only notice model로 한 번 구성하고, final이 원문과
   다시 대조하는 **제품·기업범위 전용 notice-level relation model**이어야 한다. 단, 기존 v13
   schema/full catalog를 반복하지 않도록 먼저 zero-recall items의 공통 source 관계가 실제로
   동일한지 label-blind 사례 감사로 입증해야 한다.
