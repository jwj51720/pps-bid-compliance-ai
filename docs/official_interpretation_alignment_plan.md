# 공식 판정기준 정합화 실험계획

## 배경

E0 원문 증거 관측성 audit는 4,000자 context가 nonempty gold evidence의 87.0%를
이미 포함함을 보였다. 따라서 full context·retrieval은 현 시점의 대형 개선 가설이
아니다. 반면 DACON 운영진은 공개 질의 답변에서 일부 항목의 정확한 판정 축을
명시했다. 이는 dev label을 암기하는 정보가 아니라, 모든 평가에 공통인 대회 운영
기준의 해석이다.

이번 실험은 “법령을 더 많이 주입”하는 것이 아니라, `decision_cards_v6`의 문장을
배포 항목표와 공식 해석에 정합시키는 **한 가지 prompt-policy 변화**다.

## source와 범위

공개 답변은 [official_interpretations_v1.md](official_interpretations_v1.md)에
출처 URL·적용 범위와 함께 기록한다. 이 파일은 연구 provenance이며, API 호출이나
제출물에 외부 웹 문서를 넣지 않는다. 최종 정적 card에 반영할 문장은 다음의 모두를
만족해야 한다.

1. `data/항목표.json` 또는 DACON의 공식 대회 페이지/운영진 답변에서 직접 지지된다.
2. dev ID·dev label·임의 keyword 또는 길이 cutoff를 포함하지 않는다.
3. 제공 법령 package의 스냅샷과 모순되지 않는다.
4. 법령 원문·웹 원문을 prompt context에 추가하지 않고, 짧은 card 문장으로만 표현한다.

현재 명시적 후보는 v9, v13, v24이며 v2는 현 card의 방향과 대체로 일치하는지
source audit만 한다. 이 계획은 다른 20개 card를 추측으로 수정하지 않는다.

## P0 — offline 정합성 audit

1. card v6, 항목표, official interpretation registry의 문장별 차이를 표로 남긴다.
2. candidate card는 `v6`에서 바뀐 v만 수정하고, 나머지 21개 `prompt_text`의
SHA-256이 불변임을 검증한다.
3. candidate card가 token admission에서 control보다 불리하지 않은지 exact tokenizer
admission/mock으로 확인한다.
4. `v9`/`v13` positive 전체와 고정 fast-panel을 합친 진단 cohort manifest를 생성한다.
labels는 이 **진단 cohort의 구성과 score 계산**에만 사용하며 card 문구·source
interpretation·추론 규칙에는 사용하지 않는다. 따라서 이 cohort의 결과만으로는
승격하지 않으며, 독립 cohort 재현을 요구한다.

P1으로 갈 조건은 candidate card가 source-provenance와 diff 검사를 모두 통과하는
것이다. P0에서 source가 모호하면 해당 v는 수정하지 않는다.

## P1 — paired Gemma pilot

동일 notice, 동일 Gemma 설정, 동일 V/E schema에서 아래 두 arm만 실행한다.

- Control: EXP120-equivalent card v6
- Treatment: official-interpretation card candidate

변경 가능한 config key는 `prompt.decision_cards_path` 하나뿐이다. retrieval, full
context, grouped execution, products context, output serialization, merge, decoding은
변경하지 않는다. request/cost cap은 32 notice × 2 arms 이하다.

평가에는 Macro positive-F1뿐 아니라 v9/v13/v24별 TP/FP/FN/P/R/F1, changed cell,
각 changed cell의 source evidence/metadata와 card difference를 남긴다. JSON parse와
evidence substring validity도 양 arm에서 비교한다.

## 승격/중단 조건

- target-item recall이 줄거나 새 hard-negative FP가 늘면 즉시 폐기한다.
- 작은 cohort에서 개선되어도 독립 cohort에서 같은 방향을 재현한 뒤에만 dev200을
실행한다.
- v9/v13/v24의 결과가 섞이면, 전체 card를 더 고치지 않고 원인별로 source-text가
  충분한지부터 다시 audit한다.
- dev200 improvement만으로 제출 정책을 바꾸지 않는다. 공개 score가 EXP120/EXP123에서
  보인 shrinkage를 감안해, staged submission과 runtime/evidence 검증을 별도 수행한다.

## 기대와 한계

이 branch는 공식 기준 불일치라는 구조적 오류를 바로잡는 것이지, 그 자체로 0.7을
보장하는 방법은 아니다. 그러나 raw law RAG, global retrieval, full split, generic
casebook처럼 이미 반증된 방향과 달리, evaluation target의 정의 자체를 더 정확히
Gemma에 전달한다는 점에서 작은 비용으로 우선 검증할 가치가 있다.
