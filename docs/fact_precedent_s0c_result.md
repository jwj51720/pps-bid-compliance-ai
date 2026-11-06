# S0C — source-fact precedent retrieval audit 결과

계획: [fact_precedent_s0c_plan.md](fact_precedent_s0c_plan.md)  
raw artifact: ignored `outputs/fact-precedent-s0c/report.json`, `report.md`

## 실행 범위

Gemma/Luna 생성 호출은 없었다. WSL repro archive 안의 `INC-108` Luna-high casebook을
archive 내부에서 직접 읽고, BGE-M3만으로 evaluation-only audit을 수행했다.

- casebook 64건 중 stage-A teacher positive이고 stage-B source quote가 `exact`로 해소된
  24개 fact를 candidate로 썼다.
- candidate coverage는 `v2,v3,v4,v6,v7,v9,v10,v13,v15,v17,v19,v22,v24`의 13/24 항목뿐이다.
- dev 200개 실제 문서를 paragraph/900자 overlap fragment로 나누어 4,668개 source fragment를
  만들었다. ranking에는 dev label/evidence를 쓰지 않았다.
- rank 이후에만 positive evidence가 선택 fragment 안에 들어갔는지, document type이 맞는지,
  positive와 negative의 score가 분리되는지를 평가했다.
- BGE usage는 총 2,284,245 tokens, reported cost `$0.02284279`였다. OpenRouter audit wall time은
  약 13분 25초였다. 이는 생성 비용이 아니라 retrieval admission/runtime 위험을 알리는 관측이다.

## 결과

| 측정 | 값 | 해석 |
| --- | ---: | --- |
| same-v gold-positive evidence query | 42 | covered v만의 평가 가능 표본 |
| oracle fact affinity mean score | 0.6432 | quote 자체도 아주 강한 semantic match는 아님 |
| inference-shaped evidence localization | **0.2857** (12/42) | 모든 source fragment 중 실제 근거 위치를 거의 찾지 못함 |
| selected source document type 일치 | 0.8810 (37/42) | 문서 종류·형식은 맞추지만 문서 내부 사실을 못 찾음 |
| positive-vs-negative max-score AUC | **0.5211** | score로 positive를 가를 신호가 사실상 없음 |

항목별 evidence localization은 v2 `1/7`, v3 `4/8`, v4 `2/5`, v7 `2/7`, v9 `1/3`,
v15 `0/2`, v22 `0/5`였다. v13과 v17의 `1/1`은 표본 하나이고, v6/v19/v24는 `0/1`이다.
또한 11개 항목은 source-validated positive candidate 자체가 없었다. 24개 record 중 8개 항목은
candidate가 단 하나뿐이어서, corpus를 늘려도 같은 사실 subtype을 찾는다는 보장은 없다.

## 왜 실패했는가

이 결과는 이전 generic case-RAG 실패보다 더 강한 반증이다.

1. **문서 유형 착시:** BGE는 같은 항목에서 공고문·규격서·제안요청서라는 큰 형식은 잘 맞췄다.
   하지만 그 안의 실적 비율, 필수 제출물, 모델명, 참가제한, metadata 불일치처럼 판정에 필요한
   구체적 문장을 찾지 못했다.
2. **positive와 negative가 섞임:** max similarity가 positive에서 더 크지 않다(AUC 0.521).
   따라서 score cutoff, top-1 example, positive vote를 추가하면 정확한 근거가 아니라
   보일러플레이트를 Gemma에 더 주입하게 된다.
3. **coverage 부족은 단순 수량 문제가 아니다:** 64건의 24 exact-positive facts 중 이미
   same-v matching이 실패했다. 이 상태에서 Luna로 32/256/20k건을 더 라벨링하는 것은
   retrieval key가 없는 corpus 확장일 뿐이다.

## 결정

**source-fact precedent bank 및 self-label expansion을 중단한다.**

- Luna high로 32건을 추가 self-label하지 않는다.
- 같은 record를 Gemma prompt에 넣는 paired fast-panel도 하지 않는다.
- score threshold, label transfer, positive OR merge, dev 기반 candidate 보정은 만들지 않는다.

다음 큰 방향은 20k 사례를 더 주입하는 것이 아니라, public에서 관측된 vanilla 단일-call
성능과 우리 pipeline의 차이를 **실행 계약 수준에서 역추적**하는 것이다. 구체적으로 staged
submission의 chat template, metadata renderer, tokenizer admission, JSON/schema/evidence
postprocess, decoding/runtime config가 organizer baseline 및 확보 가능한 제출 zip과 같거나
다른지를 source-to-zip까지 감사한다. 이는 새 규칙이나 model call 없이 수행 가능하며, 차이가
확정된 뒤에만 독립 fast panel → dev200 순서의 생성 실험을 설계한다.
