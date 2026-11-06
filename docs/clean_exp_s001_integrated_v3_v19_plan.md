# EXP-S001 v3/v19 통합 실행 계획

작성일: 2026-09-22

## 목적

검증된 L41 dev200 결과에서 `v3`와 `v19`의 최종 owner만 각각 C004S와 C005D의
native owner로 교체한 정책을 하나의 실행 topology로 구성한다. 목표값은 저장 응답으로
계산된 Macro positive-F1 `0.8151465658238104`이며, 새 결과가 C005D의 200행 49열 출력과
cell 단위로 일치해야 한다.

이 실험은 완전 독립 24-owner 구현이 아니다. 나머지 22개 항목은 hash-pinned L41 실행을
사용한다. 제출물 내부에는 이 연구 계보를 넣지 않고 실행에 필요한 파일만 포함하며, 계보와
제약은 이 문서와 결과 문서에서 관리한다.

## 기준과 허용 변경

- base config: `experiments/manifests/clean_exp_c005d_v19_dev200_promotion_v1.json`
- allowed policy changes:
  - 저장 base와 specialist 결과의 사후 결합을 실제 단일 실행 topology로 변경
  - 구조적/의미적 invalid 응답의 최대 재시도 횟수를 2회로 변경
  - submission batch size를 128로 고정
  - 한 task의 실패를 다른 정상 task에 전파하지 않는 batch bisection
- 판정 prompt, candidate selector, v3/v19 reducer, evidence 규칙은 변경하지 않는다.

## 실행 topology

dev200의 initial logical calls는 다음과 같다.

```text
r10: 200
C24: 200
v19: 공고별로 native candidate task 또는 B task 하나 = 200
v3 specialist: candidate가 있는 61건 = 61
합계: 661 initial calls
```

v19 native response가 2회 재시도 뒤에도 invalid이거나 positive evidence가 원문에 resolve되지
않는 경우에만 그 공고의 B fallback을 추가 호출한다. v3 specialist가 끝까지 invalid이면 r10의
기존 v3 cell을 보존한다. 정상 task는 재호출하거나 다른 task 결과로 덮지 않는다.

## 재시도 계약

- initial attempt 뒤 invalid task만 attempt 1, attempt 2를 순서대로 실행한다.
- 각 attempt는 task별 독립 상태이며 정상 응답은 그대로 보존한다.
- batch transport 예외는 재귀 이분해 단일 실패만 invalid placeholder로 격리한다.
- v3는 keyed semantic parser, v19는 requirement semantic parser, base arm은 strict JSON/schema
  검증을 통과해야 valid다.
- 끝까지 해결되지 않아도 전체 CSV 생성을 중단하지 않는다.

## 검증 순서

1. 기존 실제 응답의 task hash를 현재 task와 대조한다.
2. fast20, holdout20, dev200을 동일 결합식으로 replay한다.
3. dev200 결과를 C005D final CSV와 49열 cell 단위 비교한다.
4. 새 submission archive를 별도 이름으로 만들고 기존 ZIP은 변경하지 않는다.
5. staged ZIP 10건 mock, invalid 2-round recovery, batch failure isolation, 49열/ID/evidence를
   archive 내부 코드로 검증한다.

fresh OpenRouter 재호출은 prompt나 모델 정책 변화가 없으므로 하지 않는다. replay 결과는 기존
실제 Gemma 응답을 task hash로 묶어 새 조합을 검증하는 dev200이며, evaluator vLLM runtime 검증은
아니다.
