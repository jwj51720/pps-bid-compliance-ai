# EXP243 — v5 minimal numeric-relation review

작성: 2026-09-14, dev / mac

## 관찰된 실패

EXP229/231의 v5 numeric card는 fast, independent holdout, dev200에서 v5 recall을 크게
개선했지만 dev200 false positive 4건이 남았다. 그 사례들은 rendered input에 적용 분기,
입찰추정가격과 임계값이 모두 있는데도 Gemma가 명백한 `추정가격 < 임계값`을 무시했다.
EXP242는 evidence 출력을 제거해도 labels가 전혀 바뀌지 않음을 확인했다.

따라서 다음 최소 가설은 출력 길이가 아니라, model이 최종 v5 전에 두 숫자와 그 semantic
role을 명시적으로 결합하지 않는 문제다.

## 가설과 schema

v5-only Gemma가 final v5/e5 전에 다음 observable review를 먼저 출력하면, true positive의
지역 제한은 유지하면서 threshold 미만 false positive를 줄일 수 있다.

- `적용분기`: 국가일반 / 공기업준정부기관 / 지방세종시군구 / 지방기타시도 /
  별도기준용역 / 불명.
- `입찰추정가격`: organizer metadata의 정수 값 또는 null.
- `적용임계값`: card에서 선택한 정수 값 또는 null.
- `금액관계`: 이상 / 미만 / 불명.
- `지역문구역할`: 참가자격 / 현장납품지 / 지역명기타 / 없음 / 불명.
- `허용사유`: 있음 / 없음 / 불명.
- 그 뒤 기존 model-owned v5/e5 `판정`.

Python은 schema parse와 audit 저장만 한다. 필드 간 산술 일관성으로 v5를 계산하거나
override하지 않는다. review 숫자는 evidence가 아니며 e5는 계속 실제 source substring이어야
한다.

## 통제 정책

- base: `configs/config.exp229-v5-only-threshold-card-fast-panel-c4.yaml`.
- sole allowed policy change: `prompt.mode`.
- active item, v12 card, V/E output, metadata/product facts, organizer semantics, all original
  source, exact tokenizer admission, merge, postprocess와 provider parameters는 동일하다.
- 큰 multi-item schema로 일반화하지 않으며 v5 하나의 실제 truth-condition에 필요한 필드만
  사용한다.

## 게이트와 승격

preflight, exact dev200 admission, actual short/attachment/overflow rendered review, v5
semantic contract, schema/parser/malformed recovery, exact mock, 49-column validation과 tests를
먼저 완료한다. fast20에서 EXP229의 true positive를 유지하면서 false positive를 줄여 v5 F1
`.666667`을 넘어야 independent holdout으로 간다. holdout 방향이 같을 때만 dev200으로
확장한다. 실패하면 same-response 필드를 더 늘리거나 Python 산술 label rule을 만들지 않는다.

## Fast20 결과와 중단 결정

- preflight는 base EXP229 대비 `prompt.mode` 하나만 바뀌었음을 확인했다.
- exact dev200 admission은 374/374 source documents를 보존했고 source/metadata/card/
  organizer-semantics omission과 over-budget pack은 모두 0이었다. topology는 199×1 +
  1×2 = 201 calls다.
- short `PPS-DEV-062`, attachment `PPS-DEV-194`, overflow `PPS-DEV-169`의 실제 rendered
  message에서 active v5 semantic contract가 모두 통과했다. exact mock과 216 tests도
  통과했다.
- provider call은 20 calls, 22.9초, prompt/completion 264,915/2,905 tokens, parse error 0이었다.
- EXP229 raw macro `.152778`에서 EXP243 `.125000`으로 하락했다. v5는 TP/FP/FN
  `1/1/0 -> 0/0/1`, F1 `.666667 -> 0`이 됐다.

구조화 review는 기존 false positive `PPS-DEV-039`에서 국가/준정부기관 7억1천만원
분기와 63,636,364원 미만 관계를 올바르게 적어 0으로 고쳤다. 그러나 true positive
`PPS-DEV-049`에서는 지방계약법·일반용역·600,000,000원·실제 경상남도 참가제한을 모두
읽고도 `소관구분: 교육기관`을 `지방기타시도`, 임계값 null, 관계 불명으로 두어 0으로
회귀했다. 따라서 same-response 구조화는 계산 FP를 제거했지만 현재 카드가 표현하지 못한
지방 기관 적용분기를 보수적으로 불명 처리하게 만들었다.

주최 측 지방계약법 시행규칙 제24조 원문은 일반 물품·용역 기준을 단순 기관 단계가 아니라
`법 제5조제1항 적용 지방자치단체`와 `비적용 지방자치단체`로 나눈다. 현재 v12 카드는 이를
`세종시·시·군·구` 대 `그 밖의 시·도`로 축약했고 교육기관 분기를 설명하지 않는다. 이는
EXP243으로 새로 확인된 card/source 표현 충돌이다. 다만 dev label을 이용해 교육기관
threshold를 발명하지 않는다. EXP243은 holdout/dev200으로 승격하지 않으며, v5 schema를 더
확장하거나 Python 비교로 label을 override하지 않는다.
