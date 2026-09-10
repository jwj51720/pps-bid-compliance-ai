# EXP176 source-first exception taxonomy ablation

작성일: 2026-09-10 (dev / mac)

## 출발점

Complete-source source-first v1은 dev200에서 one-stage보다 높았지만, v1 fact inventory의
7개 category는 참가자격·제품·규격·서류·계약·일정·금액 사실을 보존할 뿐 제한을 완화하거나
적용 범위를 바꾸는 문구를 독립적으로 수집하지 않는다. 후보 수를 일괄 3→4로 높인 EXP174와
navigation 위치를 바꾼 EXP175는 fast20에서 모두 하락했다.

## 가설과 단일 변경

EXP176은 v1 7개 category를 그대로 유지하고 **`예외_허용_적용범위`** category 하나를
versioned v4 schema에 추가한다. 이 category에는 “예외”, “면제”, “허용”, “대체 가능”,
“동등 이상”, “참석하지 않아도”, “해당하지 않는 경우”처럼 제한·요구의 실제 적용 범위를
바꾸는 source substring만 최대 3개 복사한다.

Stage 1은 여전히 final label, 법률 해석, metadata 값, 허용/위반 결론을 내지 않는다.
Stage 2는 complete original source를 다시 받으며 category null은 final 0이 아니다. cards,
metadata/product fact, schema, decoder, token admission, merge와 Python final-label
postprocess는 바꾸지 않는다.

## 판단 기준

이것은 dev label이나 특정 v의 오류를 보고 만든 rule이 아니라, public procurement notice의
제한 문구는 예외·대체·적용범위 문구와 함께 읽어야 한다는 source-structure 가설이다.
v1보다 fast20 macro 및 evidence quality가 모두 나쁘지 않을 때만 holdout20으로 간다.
악화하거나 final source omission/parse warning이 증가하면 확대하지 않는다.

## 유료 전 검토

Preflight는 EXP167 대비 `staged_run.mode` v1→v4 하나만 바뀐 것을 확인했다. exact tokenizer
admission은 dev200 source 374/374, metadata 21/21, active card 24/24, over-budget 0이며
pack 분포는 1회 186·2회 12·3회 2건이다. semantic contract은 24/24 PASS, full regression은
144 passed였다.

`outputs/exp-176-source-first-full-final-v4-fast-panel-c4-mock/staged_input_examples.md`의
PPS-DEV-062/169/01을 검토했다. Stage 1 schema, instruction, navigation 모두 8개 category를
동일 순서로 가지며 추가 category는 raw source exception/allowance scope만 요구한다. final은
cards/metadata/product fact와 모든 original source를 다시 포함한다. mock은 20/20이며,
extra category가 artifact에 실제 기록되는 것을 확인했다.

## EXP176 valid fast-20 결과

EXP176은 20/20 complete, stage-1 parse error/final recovery 0, CSV validation PASS였다.
새 category는 총 46개 후보(공고당 중앙 2.5, 최대 6)를 실제로 남겼고 navigation 중앙값은
12→15가 됐다. macro F1은 **0.287500**으로 EXP167 v1의 0.286111보다 +0.001389였다.

v1/v4/v12는 개선됐고 v9/v17 FP도 하나씩 줄었지만, v22 TP 하나가 FN으로 바뀌고 v13 FP
하나가 생겼다. evidence validity는 .789(v1 .700), warning은 4(v1 6)로 개선됐으며 total
tokens 667,016(v1 659,207), runtime 144.3초(v1 165.0초)다. remote variance와 작은 fast
cohort를 고려하면 이 결과만으로 candidate를 선택할 수 없다.

계획의 확대 gate(quality/evidence가 동시 악화하지 않을 것)를 겨우 충족하므로 동일 policy
holdout20을 실행한다. holdout이 v1보다 낮거나 동등 이득이 재현되지 않으면 v4를 기각한다.

## EXP177 independent holdout 결과 및 결론

EXP177은 20/20 complete, stage-1 parse error/final recovery 0, CSV validation PASS였다.
exception category는 42개 후보를 남겼고 navigation 중앙값은 v1 14→16이었다. 그러나 macro
F1은 **0.166667**로 policy-identical EXP168 v1의 **0.229167**보다 -0.062500이었다.
evidence validity도 .875(v1 .900)로 개선되지 않았다.

주요 손실은 v1 TP 1건과 v23 TP 1건이 FN으로 바뀐 것이며, v13/v17 FP가 하나씩 추가됐다.
따라서 fast20의 +.001389는 일반화되지 않았고, extra exception taxonomy는 **reject**한다.
v1의 7-category source-first/full-final만 complete-source branch incumbent로 유지한다.
