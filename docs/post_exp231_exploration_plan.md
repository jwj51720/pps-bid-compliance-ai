# Post-EXP231 exploration plan

작성: 2026-09-14, dev / mac

## 현재 결론

현재 최고 dev200 결과는 EXP208의 all-item relation-checklist 판정에 EXP221
v4-only와 EXP231 v5-only 결과를 순서대로 field replacement한 `0.329265`다.

점프는 하나의 원인으로 설명되지 않는다.

- EXP209 direct `0.257457`에서 EXP208 relation checklist `0.292959`로의
  `+0.035502`는 카드와 입력을 고정한 채, 원문 뒤에서 주체·역할·조항·날짜·대응
  metadata 관계를 다시 확인시킨 효과다.
- EXP208에서 EXP221 v4 composition `0.306117`로의 `+0.013158`은 잘못된 v4
  금액 적용범위 수정과 all-item attention 분리를 함께 포함한다.
- EXP221에서 EXP231 v5 composition `0.329265`로의 추가 개선은 v5-only 집중과
  빠져 있던 수치 비교 operand를 카드에 넣은 효과다.

따라서 `기존 카드 전체가 나빴다`고 일반화하지 않는다. v2, v3, v21은 dev200 F1
1.0이고 v22는 0.909다. 반면 v4에는 organizer-law source와 충돌하는 적용범위 gate가
있었고, v5에는 `고시금액 이상`을 판정할 실제 숫자 operand가 없었다. v15/v17의
법적으로 더 정확한 카드 수정은 independent holdout에서 성능 개선으로 이어지지 않았다.

현재 입력 완결 감사에서는 374/374 source documents, cards, 필요한 human-readable
metadata, exact-code product facts와 organizer semantics가 모두 final rendered input에
존재한다. 남은 주 병목은 입력 누락보다 다음 두 가지다.

1. 일부 item card의 실제 truth-condition 불완전성 또는 적용범위 충돌.
2. Gemma가 긴 원문에서 찾아낸 사실을 24개 카드의 동일 주체·역할·수치·예외 관계로
   안정적으로 결합하지 못하는 문제.

## 우선순위 1: 수정 v5 카드를 all-item base에 직접 적용

### 가설

EXP231의 개선 중 수치 operand 완결 효과가 item-only attention 없이도 유지된다면,
EXP208의 219-call topology 안에서 v5 recall과 precision을 회복할 수 있다.

### 최소 실험

- base: EXP208.
- active items, prompt mode, V/E schema, source admission, metadata/product facts, merge,
  postprocess와 provider parameters를 고정한다.
- v5 외 card text가 byte-equivalent인 card artifact를 사용한다.
- 유일한 허용 policy change는 `prompt.decision_cards_path`다.
- fast20에서 v5와 전체 macro/TP를 확인하고, independent holdout 방향이 같을 때만
  dev200으로 확장한다.

이 실험이 성공하면 v5 specialist 200 calls를 제거할 수 있다. 실패하면 all-item card
문구를 반복 조정하지 않고 v5의 attention isolation이 필수였다고 기록한다.

## 우선순위 2: v4와 v5 specialist를 한 호출로 통합

### 가설

이미 fast/holdout/dev200에서 각각 검증된 두 item만 같은 subset prompt에서 판단해도
서로의 recall/precision을 훼손하지 않는다면 현재 dev200 topology를 619 calls에서 약
419 calls로 줄일 수 있다.

### 최소 실험

- base output은 EXP208으로 고정한다.
- active items는 정확히 `[v4, v5]`다. 전체 v-grouping으로 확대하지 않는다.
- v4 corrected scope와 v5 numeric operand를 동시에 보존하는 결합 card artifact를
  사용한다. v4/v5 외 card text는 바꾸지 않는다.
- output은 v4/e4와 v5/e5만 model-owned field replacement한다. OR, majority 또는 Python
  label inference를 사용하지 않는다.
- 먼저 별도 specialist 합성과 비교해 v4/v5 TP/FP/FN, malformed, evidence validity와
  exact call topology를 측정한다.
- fast와 independent holdout에서 두 item 모두 방향을 유지할 때만 dev200으로 간다.

419 calls도 이전 438-call 후보가 evaluator 120분을 초과했다는 점에서 안전하지 않다.
이 후보는 현재 최고 quality를 압축하는 중간 단계이며 runtime 통과를 보장하지 않는다.

## 우선순위 3: v5의 명시적 수치 관계 판정

EXP231의 네 false positives는 카드와 rendered metadata에 임계값과 입찰추정가격이 모두
있는데도 Gemma가 명백한 `추정가격 < 임계값`을 무시한 사례다. 이는 추가 입력 문제가
아니라 관계 실행 문제다.

다음 후보는 v5 하나에서만 다음 observable fields를 가장 작게 요구한다.

1. 적용 법체계와 organizer-provided 기관 분기.
2. 입찰추정가격.
3. 적용 임계값.
4. 두 금액의 대소 관계.
5. 실제 참가자격 지역 제한의 존재.
6. model-owned final v5/e5.

Python은 원문/metadata provenance와 parse만 검증하고 비교 결과로 label을 계산하거나
override하지 않는다. 동일 응답의 큰 reasoning schema가 논리 일관성을 강제하지 못한
EXP222를 반복하지 않도록, enum과 필드는 v5 truth condition에 필요한 최소치로 제한한다.

## 후순위: item별 source/card audit

현재 zero-F1 item을 일괄 specialist화하지 않는다. v6, v7 및 absence items를 포함한 각
항목에 대해 다음 순서로 하나씩 진단한다.

1. gold evidence와 필요한 organizer fact가 actual rendered prompt에 존재하는가.
2. card가 organizer law source의 적용범위·1 조건·중요 0 조건을 충실히 압축했는가.
3. 오류가 참가자격·평가·제품·시설·제출서류 등 semantic role 혼동인가.
4. absence item이면 적용대상 확인과 whole-notice presence inversion 중 어느 단계가
   실패했는가.

source로 입증된 card defect가 있는 가장 작은 item만 수정한다. v15/v17처럼 법적 문구는
개선됐지만 independent holdout이 실패할 수 있으므로, card 정확성과 모델 성능을 별도
결론으로 기록한다.

## 중단 및 승격 규칙

- full-split x v-group, source-first x grouping, 반복 V-only consensus, raw-law RAG와
  Python label rules는 재시도하지 않는다.
- 한 실험에서 card, schema, merge, provider parameter와 routing을 섞지 않는다.
- 모든 후보는 complete semantic input, 모든 admitted original source와 final source
  recheck를 유지한다.
- paid run 전 preflight, exact tokenizer admission, short/attachment/overflow rendered
  review, active-item semantic contract, mock와 isolated output을 완료한다.
- fast20은 고정 panel만 사용하고 independent holdout 확인 후에만 dev200으로 확장한다.
- local quality와 evaluator runtime을 별도로 판단한다. batch size는 호출 수를 줄이지 않는다.
