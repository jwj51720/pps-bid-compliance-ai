# S0D — dev source-grounded few-shot precedent feasibility audit

## 질문

대회 제공 dev-200의 label/evidence는 정적 사례집에 쓸 수 있다. 하지만 사례를
그대로 prompt에 넣기 전에, 다른 공고의 동일 v positive evidence가 현재 공고의
실제 source fact를 retrieval할 수 있는지 검증한다.

이는 이미 실패한 무라벨/Luna 64건 casebook과 다르다. 후보가 dev의 검증된 source
substring이므로 각 non-absence v마다 대략 5~8개의 양성 선례가 있다. 반면 과적합을
막기 위해 query notice의 모든 candidate는 제외한다.

## 고정 계약

- 후보: dev label=1이고 e가 실제 source substring으로 해소되는 `(notice, v, e)`만.
- query: dev의 각 notice를 paragraph/900자 overlap source fragment로 분할한다.
- ranking: same-v candidate evidence와 current source fragment만 BGE-M3로 비교한다.
  query embedding/ranking에는 query의 gold label/evidence를 넣지 않는다.
- 평가 후에만 dev gold e 위치 포함 여부, document type, positive-vs-negative score
  AUC를 계산한다.
- 부재탐지 5개는 positive evidence가 구조적으로 없으므로 이 source-grounded audit의
  범위 밖이다. 이 audit은 label transfer, voting, threshold 보정이 아니다.

## 사전 gate

Gemma/Luna를 호출하지 않는다. 다음 모두를 만족해야만 few-shot prompt pilot을 설계한다.

1. aggregate evidence localization hit rate ≥ 0.50
2. aggregate positive-vs-negative score AUC ≥ 0.65
3. 충분한 평가 표본을 가진 항목의 다수가 AUC 0.60 이상

그렇지 않으면 dev label을 선례로 넣는 RAG도 generic case RAG와 동일한 retrieval
문제를 가진 것으로 보고, Gemma injection과 Luna 확장을 하지 않는다.
