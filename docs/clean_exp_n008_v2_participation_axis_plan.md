# N008: v2 정량 실적·참가 단계 관측 축 명확화

작성일: 2026-09-22

## 기준과 정량 가설

N007 fixed fast20은 TP/FP/FN=3/2/0, F1=0.75, invalid 1이다.
frozen v2 dev200 cell F1=1.0은 보존 대상이다. N007의 FP 2건이
오직 `performance_participation=Y` 오관측에서 왔다는 per-notice
증거가 있으므로, 문구 하나의 기대 상한은 FP 2→0, TP 3 유지,
F1 0.75→1.0, 24항목 Macro 기여 `+0.25/24 = +0.0104167`이다.
반대로 TP 한 건을 잃으면 TP/FP/FN=2/0/1, F1=0.8이므로
같은 fast panel의 상승만으로 일반화됐다고 보지 않는다.

## 유일한 정책 변경

Base manifest는
`experiments/manifests/clean_exp_n007_v2_performance_fast_v1.json`이다.
`allowed_policy_changes`는 `prompt.task`, `data.source_audit_path`만
선언한다. v32 card, bounded source view, metadata, schema, provider,
max tokens, threshold, parser, evidence gate, fast panel, grouping/call
topology는 그대로 둔다.

새 system 문구에서 `performance_participation=Y`는 두 조건이 모두
원문에서 확인될 때만 허용한다.

1. 과거 완료 실적의 **명시적인 최소 금액·규모·수량**이 있다.
2. 그 하한이 제안서 점수·낙찰 후 이행·증명서 서식이 아니라
   **입찰/제안 참가 가능 여부**를 가른다.

단순 `경험이 있는`, `관련분야 수행`, 기관유형 제한은 정량 하한이
없으면 이 축에서 N이다. 평가표의 배점/등급/실적 서식은 금액·수량이
적혀 있어도 참가 문턱이 아니면 N이다. 특정 실패 ID나 문장을 prompt에
넣지 않는다. `quote`는 Y의 두 조건을 직접 지지하는 원문 substring이다.

## 실행 gate

1. v2 task v1과 v2의 schema/metadata/view/decision 동등성 테스트.
2. 200건 actual-task exact tokenizer audit 및 task hash; gold e2 7/7,
   모든 제공 문서 scan, admission 200/200.
3. short, attachment, overflow/largest의 실제 system/user를 출력·읽고
   v2 applicability, 1/0, 예외, 문서, metadata semantic-input contract
   재확인.
4. `scripts/preflight_experiment.py` PASS, mock 20건, isolated output.
5. fixed fast20에서 TP/FP/FN, malformed, evidence, call count/runtime를
   기록. 목표 TP/FP/FN=3/0/0 및 invalid 0. 부족하면 승격하지 않는다.
6. 목표 도달 시 독립 holdout20, 그 후에만 dev200.

유료 실행 전에는 위 요소가 실제 manifest에서 모두 선택됐는지 다시
확인한다. 일부만 구현한 상태의 호출은 N008 완결 실험으로 취급하지
않는다.
