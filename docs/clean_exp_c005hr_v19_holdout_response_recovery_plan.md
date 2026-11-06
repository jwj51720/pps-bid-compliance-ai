# EXP-C005HR v19 holdout response recovery 계획

작성일: 2026-09-21  
상태: exact retry 실패, 추가 동일 retry 및 dev200 금지

## 결함 분류

C005H independent holdout20의 label 방향은 v19 FP `1 → 0`으로 개선됐지만 run status는
`INCOMPLETE`다. 원인은 `PPS-DEV-192__p01` 하나뿐이다.

- finish reason: `length`
- completion tokens: 정확히 1,536
- content: observation JSON을 시작한 뒤 긴 whitespace loop
- task hash: `73f45511372b5d0d815ee32ac955f6299a240afeb9821b9bdeea7a0941b3461e`
- failed response SHA-256:
  `45e9fcd00e65955b419480705ac14b72c5e02aceb44002588aaef2e10f0e0a12`

이는 source/법률 판단 가설의 실패가 아니라 structured-response serialization 실패다. 현재
baseline fallback label이 우연히 negative인 사실로 invalid를 무시하지 않는다.

## 통제 계약

- base manifest: `clean_exp_c005h_v19_requirement_holdout_v2.json`
- base output:
  `outputs/clean-exp-c005h-v19-requirement-holdout-v2/holdout20/`
- exact target: `PPS-DEV-192__p01` 하나
- retry attempts: 1
- 정상 response 17건 재호출: 0
- prompt, messages, schema, candidate view, task hash, model, temperature, seed, max tokens,
  provider preference: 변경 0
- failed response를 덮어쓰지 않고 `recovery_attempts/attempt_01/`에 append
- 성공 attempt만 assembly 시 target response로 선택
- 실패하면 C005H는 계속 INCOMPLETE이며 추가 자동 retry 또는 dev200 실행 금지

## 사전/사후 gate

1. 현재 코드로 holdout task 18개를 재구성하고 base preflight task hash와 18/18 일치
2. expected target은 unusable, 나머지 17개는 usable임을 확인
3. provider call count 정확히 1
4. recovered response가 stop/valid JSON/candidate-key complete인지 확인
5. 동일 positive-only quote resolution과 reducer로 20건을 재assembly
6. non-v19 changed cells 0, evidence exact substring, 49-column validation
7. 최종 invalid 0이어야만 holdout gate 판정

Holdout gate는 원 계획과 같다. v19 positive가 없는 cohort에서 FP `<=1`이면 비열화 통과,
FP `0`이면 목표 통과다. 복구 후에만 dev200 승격 여부를 결정한다.

## 결과

Task hash는 일치했고 정상 17건을 재호출하지 않은 채 target 한 건만 호출했으나, 두 번째 응답도
동일하게 1,536 tokens의 whitespace loop와 미완성 JSON으로 종료됐다. 계획의 최대 1회 retry를
소진했다. 상세는 `docs/clean_exp_c005h_c005hr_v19_holdout_result.md`에 기록한다.
