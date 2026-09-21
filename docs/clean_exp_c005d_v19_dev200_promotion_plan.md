# EXP-C005D v19 requirement-instance dev200 승격 계획

작성일: 2026-09-21

상태: 구현 전 계획

## 결정

현재 canonical 품질 baseline은 C004S dev200 Macro positive-F1
`0.8037378356650803`이다. C005R fast20과 C005H/C005HS independent holdout20이 서로 다른 class
측면에서 같은 방향을 보였고 C005HS가 유일한 transport failure까지 해소했으므로, 다음 유료 실험은
v19 policy의 dev200 승격 검증으로 한다.

새 item, 새 candidate view, 새 semantic field, 새 reducer를 동시에 추가하지 않는다. C005H의 verbose
task를 primary로 그대로 사용하고 strict semantic parse가 실패한 task만 C005HS compact schema로
최대 한 번 복구한다. Python은 compact code를 기존 verbose observation으로 1:1 변환할 뿐 label
default나 문구 판정을 하지 않는다.

## 수학적 우선순위

C004S dev200 v19 confusion matrix는 TP 5, FP 10, FN 1이고

```text
F1_v19 = 2TP / (2TP + FP + FN) = 10 / 21 = 0.4761904762
```

이다. 다른 23개 item은 byte-for-byte 고정하므로 C005D의 Macro는 정확히

```text
Macro_C005D = 0.8037378357 + (F1_v19_C005D - 0.4761904762) / 24
```

이다.

| v19 결과 | v19 F1 | 예상 Macro | baseline 대비 |
|---|---:|---:|---:|
| 5 TP / 9 FP / 1 FN | 0.500000 | 0.804730 | +0.000992 |
| 5 TP / 6 FP / 1 FN | 0.588235 | 0.808406 | +0.004669 |
| 5 TP / 3 FP / 1 FN | 0.714286 | 0.813659 | +0.009921 |
| 6 TP / 6 FP / 0 FN | 0.666667 | 0.811674 | +0.007937 |
| 6 TP / 3 FP / 0 FN | 0.800000 | 0.817230 | +0.013492 |
| 6 TP / 0 FP / 0 FN | 1.000000 | 0.825563 | +0.021825 |

즉 기존 TP를 보존하면 FP 하나의 순감소만으로 Macro가 상승한다. fast20에서는 유일한 v19 양성을
FN→TP로 바꾸었고, holdout20에서는 baseline FP 1을 0으로 줄였다. 양성 recall과 독립 음성 precision
양쪽 신호가 있어 dev200 승격 비용을 지불할 근거가 있다.

## base와 허용 변경

- base config: `experiments/manifests/clean_exp_c005h_v19_requirement_holdout_v2.json`
- cohort: dev200 200건
- 허용 변경:
  - `layers.decisions`: compact recovery serializer 추가
  - `v19_serialization_recovery`: invalid primary task에만 1회 compact retry
  - `runtime.expected_calls_per_record`
- 금지 변경:
  - source view/candidate admission
  - v19 semantic prompt/card/9개 field
  - v19 positive predicate와 quote resolver
  - provider model/temperature/max token/seed
  - v3 및 나머지 23개 owner/label/evidence

## call topology

C005 Phase A dev200에서 candidate notices 165, candidates 372, overflow 0이므로 primary logical call은
165다. recovery call 수를 `R`이라 하면 총 호출은 `165 + R`, `0 ≤ R ≤ 165`다. 각 task는 compact
recovery를 최대 한 번만 받고 동일 형식 재시도는 없다.

C005H holdout 관측 `1/18`에 uniform Beta(1,1) prior를 둔 posterior mean invalid rate는
`2/20 = 0.10`이므로 계획상 기대 recovery는 약 16.5건, 기대 총 호출은 약 181.5건이다. 이는 비용
예측일 뿐 label 판단이나 성공 기준에는 사용하지 않는다. 최악 330 calls까지 audit에 명시하며,
submission runtime 구조로 자동 승격하지 않는다.

## 구현 순서와 preflight gate

1. clean `src/pps_ai`에 conditional compact recovery를 구현한다.
2. primary response가 이미 semantic-valid면 compact call을 절대 만들지 않는 unit test를 둔다.
3. invalid primary만 compact task가 생성되고, candidate order/hash와 user/system semantic prefix가
   동일하며 adapter 후 기존 parser/reducer만 호출되는지 검사한다.
4. fully resolved manifest와 `allowed_policy_changes`를 preflight한다.
5. dev200 source coverage 374/374, candidate notices 165, candidates 372, overflow 0을 재확인한다.
6. short/attachment/largest rendered primary message와 compact recovery target template을 사람이 읽고
   semantic-input contract를 기록한다.
7. dev200 mock으로 200×49 output, non-v19 changes 0, evidence validity를 확인한다.
8. 유료 실행 직전에 manifest hash, primary task hashes, output path가 모두 선택됐는지 재확인한다.

## 성공·중단 기준

성공은 다음을 모두 만족해야 한다.

- primary + recovery 최종 invalid responses 0
- every evaluated notice에 실제 공고가 들어간 성공 Gemma call 존재
- non-v19 label/evidence changed cells 0
- v19 positive evidence 전부 unchanged source substring ≤500자
- v19 F1 > 0.4761904762
- Macro > 0.8037378357

invalid가 남거나 v19 F1이 baseline 이하이면 C005를 canonical baseline으로 승격하지 않는다. 결과가
좋아도 이 165+R call 구조를 submission에 바로 사용하지 않는다. 품질 승격과 2시간 evaluator runtime
설계는 별도 축으로 평가한다.
