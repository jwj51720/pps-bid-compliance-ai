# Clean EXP-C007CR: v4 evidence-serialization replay

작성일: 2026-09-21

## 목적과 범위

C007C fast20은 v4 TP/FP/FN `3/0/0`을 기록했지만 18개 응답 중 3개가
인용문 형식 검증에서 실패하여 전체 상태가 `INCOMPLETE`다. 저장된 원응답만
재생하며 추가 모델 호출·프롬프트 수정·판정 필드 변경은 하지 않는다.
이것은 C007C의 관계형 v4 진리조건을 확장하거나 canonical로 승격하는 실험이 아니다.

## 사전 원인 확인

- `PPS-DEV-30`, `PPS-DEV-191`: negative predicate 후보에 불필요한 `q`가 있음.
  해당 인용은 label/evidence에 사용하지 않는다.
- `PPS-DEV-049`: positive predicate 인용의 줄바꿈 공백만 원문과 다름.
  기존 clean v19 resolver의 exact-first / unique-whitespace 방식으로 해당
  candidate 원문에서 변경 없는 207자 span을 유일하게 복원할 수 있다.
- 양성의 문자 치환·편집거리 보정은 금지한다. 유일하게 복원되지 않으면 기존
  baseline fallback이다. 음성의 `r,m,x,a,n`은 그대로 검증·사용한다.

## 통제와 예측

- `experiment.base_config`: `clean_exp_c007c_v4_relation_probe_v1.json`
- `allowed_policy_changes`: v4 quote serialization/replay source/output only.
- 18개 task hash, model response, v4 semantic predicate, 다른 23개 항목,
  baseline rows, provider 설정은 byte-identical.
- zero paid calls; 저장 응답 18개를 별도 `outputs/...`에 재생한다.
- 성공 기준: malformed 0, evidence 검증 PASS, non-v4 변경 0.
- C007C에서 유효했던 15개 task의 최종 v4/e4는 동일해야 한다.
- C007CR의 fast20 TP/FP/FN은 **재측정**한다. 특히 049의 복원은 새로운
  positive로 이어질 수 있으므로 `3/0/0` 유지라고 미리 가정하지 않는다.
  FP가 생기면 이 실험은 quote parser 개선 성공과 관계없이 품질 후보로 기각한다.

## 실행 순서

1. quote-resolution parser 단위 테스트: exact, unique-whitespace, ambiguous,
   non-whitespace edit, negative quote ignored, semantic field unchanged.
2. manifest diff/preflight; task hash 및 stored response coverage 확인.
3. mock/zero-call replay; 49열·evidence 검증과 per-item metric 비교.
4. 품질과 invalid 결과를 기록하고, 통과 시에만 independent holdout20을 검토한다.

이 재생은 prompt 실험이 아니므로 새 유료 호출 전 rendered-input/semantic-contract
gate를 대체하지 않는다. C007C의 기존 rendered review와 contract는 동일 task hash로
계승한다.
