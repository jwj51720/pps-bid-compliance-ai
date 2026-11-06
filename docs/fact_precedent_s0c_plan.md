# S0C — source-fact precedent retrieval audit 계획

## 출발점

공고 전체 유사도, card lexical 후보군, dev/무라벨 template 전이, 그리고 64건
casebook의 metadata+case-signature BGE retrieval은 모두 중단됐다. 공통 원인은
입찰 보일러플레이트가 similarity를 지배하고, 최종 24개 판단에 필요한 **항목별 실제
제한·부재·동일필드 불일치 사실**을 구분하지 못한 것이다.

한편 WSL archive에는 64개 organizer-unlabeled notice를 Luna high가 직접 읽어 만든
source-preserving casebook가 있다. 63개 성공 record 안에 25개의 teacher-positive가 있고,
24개는 원문 substring으로 해소된 quote를 가진다. 이 record는 새 비용 없이 다음 질문을
반증할 수 있는 유일한 자산이다.

> `v_i`의 positive teacher fact/quote가 있을 때, 현재 공고의 **어느 원문 조각**이 그
> fact와 같은 의미인지 BGE-M3가 찾아낼 수 있는가?

이는 generic case RAG 재실행이 아니다. 현재 공고의 전체 문서를 source fragment로 나누고,
각 `v_i`마다 **동일 `v_i`의 positive, source-validated teacher record만** 비교한다. 최종
label을 transfer하거나 score threshold로 바꾸지 않는다.

## S0C 설계 (비용: BGE embedding만)

### 입력과 provenance

- archive: `dist/archives/pps-dev-wsl-repro-20260907.tar.xz` 내부
  `incubator/runs/inc108_unlabeled_casebook64/records.jsonl`
- 현재 notice: organizer `data/raw/open/dev.jsonl.gz`
- 평가 전용: organizer `dev_labels.csv`의 positive label/evidence
- candidate record: stage-A label이 1이고 stage-B의 quote가 `resolved: exact`인
  `(unlabeled notice, v)`만 사용한다. `basis`, unchanged quote, case signature, 필요한
  metadata를 BGE candidate text로 쓴다.
- query unit: current notice의 실제 source document를 paragraph 우선, 장문은 고정
  overlap fragment로 나눈 뒤, metadata와 함께 BGE로 임베딩한다. 이 segmentation은
  후보 확장 시에도 그대로 재사용 가능해야 한다.

labels/evidence는 **사후 평가에만** 쓰며 candidate 생성, query 생성, ranking, cutoff에는
절대 사용하지 않는다.

### 두 독립 측정

1. **Oracle fact affinity**: gold evidence 자체를 evaluation-only query로 하여 same-v
   teacher fact가 semantically 가까운지 본다. 이는 candidate fact가 범용 보일러플레이트가
   아닌지 확인하는 낙관적 상한이다.
2. **Inference-shaped localization**: label 없이 만든 모든 current source fragment 중,
   same-v teacher fact에 가장 가까운 fragment를 고른다. 그 fragment가 gold evidence를
   포함하는지, source document type이 맞는지, negative notice보다 score가 높은지를 본다.
   이 결과만이 향후 Gemma prompt에 넣을 "현재 공고의 관련 원문" 선택 가능성을 평가한다.

## 사전 승격/중단 기준

S0C는 Gemma/Luna 호출을 하지 않는 audit이며, positive label을 바꾸지 않는다.

- **즉시 중단:** covered item에서 inference-shaped evidence localization이 무작위 수준,
  또는 positive/negative score 분리가 없으면 self-label corpus 확장 및 Gemma injection을
  하지 않는다. candidate quote가 현재 사실을 찾는 열쇠가 아니라는 뜻이다.
- **조건부 진행:** covered item에서 oracle affinity와 inference-shaped localization이 모두
  명확하고, negative activation보다 높은 signal을 보일 때만 다음 단계(S1F)를 설계한다.
  S1F는 *누락 v를 포함하도록 사전 층화한 최대 32개 unlabeled notice*에 Luna high case-record를
  추가하는 작은 pilot이다. 20k 또는 dev200 Gemma 호출로 곧바로 가지 않는다.
- **아직 금지:** label voting/OR merge, dev-ID/label 기반 candidate 선택, raw law context,
  generic whole-notice nearest neighbor, 그리고 evidence가 없다는 이유만의 0/1 보정.

S0C가 성공하더라도 source fragment + teacher fact가 Gemma 판단을 실제로 개선하는지는
별도의 paired fast-panel experiment에서 확인해야 한다. 그 experiment는 candidate bank,
fragment budget, V/E schema, decoder, merge를 고정하고 injection 하나만 바꾼다.
