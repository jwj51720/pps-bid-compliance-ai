# 실험 비교와 호출 변동 분리 정책

작성: 2026-09-11, dev / mac

원격 Gemma는 temperature 0과 seed를 사용해도 완전히 결정적인 replay가 아니다.
따라서 항목 하나의 card/context만 바꾼 실험에서 다른 v가 바뀐 것을 그 정책의
인과 효과로 해석하지 않는다.

모든 local A/B는 `scripts/compare_experiment_predictions.py`로 다음을 분리한다.

1. input/label hash, cohort 크기, fast-panel path가 같은지 확인한다.
2. 전체 macro 변화를 보고한다.
3. 가설이 직접 바꾸는 `focus_items`의 TP/FP/FN/F1과 changed cell을 보고한다.
4. 나머지 항목의 changed cell을 `off_target` 호출 변동으로 분리한다.
5. focus 개선 없이 macro만 변하거나, off-target 변동이 큰 1회 실행은
   정책의 효과 증거로 승격하지 않는다.

이 비교는 같은 입력을 두 번 호출한 결과의 변동을 없애지 못한다. staged 실험에서
마지막 specialist/verifier만 바꾸는 경우에는 같은 upstream 출력을 재사용한
local-effect 비교를 먼저 하고, 이득이 있을 때 별도 end-to-end 재실행을 한다.
재사용 결과는 전체 전략의 재현 점수라고 부르지 않는다.
