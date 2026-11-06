# 다음 대형 가설: 무라벨 20k의 항목별 선례 bank

## 왜 방향을 바꾸는가

현재의 0.15~0.32권 실험은 같은 고정 Gemma에게 더 긴 공고, 법령 원문, 더 긴 card,
문서 split을 주는 변형이었다. 결과는 일관되게 큰 개선을 만들지 못했고, full split은
runtime을 크게 악화시켰다. EXP123도 dev200 0.31780에서 public 0.26045로 줄었다.
따라서 dev 오류 몇 건을 직접 고치는 방식은 중단한다.

대회는 `train_unlabeled.jsonl.gz` 20,000건을 자가 라벨링·RAG 사례집·후처리 튜닝에
쓰도록 명시적으로 허용한다. 이 자료는 공고와 동일한 실제 분포라는 점에서, 지금까지의
법령 원문 RAG와 질적으로 다르다. 다만 기존의 작은 generic casebook/RAG 실패를
반복하지 않는다.

## 검증할 가설

**항목별로 질의한 짧은 자기라벨 선례가, 동일 항목의 card와 현재 공고의 trigger를
연결해 Gemma의 recall/precision을 높인다.**

선례는 외부 LLM이 대회 제공 공고만 읽어 생성한 정적 record다. 최종 제출은 여전히
고정 Gemma를 정상 호출하고, 선례 bank는 검색용 정적 자산일 뿐 학습 가중치나 별도
분류기가 아니다.

이는 다음과 구별된다.

- 법령 RAG: 조문 원문을 더 넣어 법률 추론 부담을 늘렸고 실패했다.
- generic 사례 RAG: 소수의 공고를 공고 전체 유사도로 찾아 항목별 trigger가 맞지
  않았고 실패했다.
- 이번 가설: `v_i` card를 query에 포함해 **항목별**로 찾고, 선례는 label·짧은 원문
  evidence·적용/예외 사실만 가진다. 최종 prompt에는 각 v의 상위 1개 또는 2개만
  매우 짧게 넣는다.

## 선례 record 계약

외부 라벨 생성 prompt에는 공고 원문·meta·항목표·배포 법령패키지의 필요한 부분만
넣는다. 웹 검색·외부 자료는 넣지 않는다. 각 `(unlabeled notice, v)` record는 다음만
저장한다.

```json
{
  "notice_id": "...",
  "v": "v13",
  "label": 0,
  "evidence": "원문 그대로의 500자 이하 부분문자열 또는 빈 문자열",
  "trigger_summary": "소기업 확인서 문구는 있으나 경쟁제품 적용 근거가 확인되지 않음",
  "applicability_facts": {"계약법": "지방계약법", "계약방법": "제한경쟁"},
  "generator": {"model": "...", "prompt_version": "...", "settings": "..."}
}
```

`trigger_summary`는 생성 기록·검색 질의 보조용이며, 최종 prompt에는 사람이 읽는 짧은
“유사 선례의 관찰”로만 렌더링한다. 구현 status, vector id, 내부 score, 긴 추론 전문을
Gemma에 노출하지 않는다. evidence는 원문 substring 검증을 반드시 통과해야 한다.

## 단계와 승격 기준

### S0 — 무비용 적합성 audit

1. 20k의 문서 유형·meta 조합·길이·익명화 token 분포를 집계한다.
2. dev의 각 positive evidence를 query로 하여, BGE와 BM25가 20k의 같은 문서 유형·
   유사 trigger 후보를 상위에 찾는지 측정한다. 여기서는 dev label을 평가에만 쓰고
   index·query policy에 쓰지 않는다.
3. 항목별 top-1/top-3 candidate의 문서 유형, query token overlap, meta compatibility를
   표로 남긴다. 적어도 다수 항목에서 무관한 boilerplate만 반환되면 S1을 시작하지
   않는다.

### S1 — 고품질 self-label pilot

S0에서 고른 **사전 선언된** 200~400개 20k 공고만 외부 LLM으로 라벨링한다. 선택은
`계약법 × 계약방법 × 업무구분 × 문서유형/길이` strata와 retrieval 후보로 고정하며,
dev label·개별 dev error를 기준으로 고르지 않는다. 모든 요청/응답·prompt·model setting을
기록한다.

먼저 외부 LLM의 dev blind annotation을 별도 diagnostic으로 실행해, 해당 teacher가
항목별로 기준선을 실제로 넘는지 확인한다. teacher가 v별 positive recall을 만들지 못하면
20k 확장은 중단한다.

### S2 — paired retrieval pilot

기존 단일-call baseline을 control로 두고, **선례 injection만** 바꾼 treatment를 만든다.
각 v는 card+현재 공고의 query로 상위 1개(필요 시 2개) 선례만 받는다. context 예산,
출력 schema, Gemma decoding, evidence validation은 그대로 둔다.

dev200은 평가 전용이며, 아래를 함께 본다.

- macro positive-F1 및 v별 TP/FP/FN
- retrieved precedent의 같은-v 비율, source doc type 일치율, prompt token 증가량
- evidence substring validity와 실제 submission call 수/runtime

S2에서 dev200에서 명확한 이득과 runtime 안전성을 모두 보일 때만 20k 확장을 검토한다.
작은 fast panel 개선만으로는 확장하지 않는다.

## 금지선

- dev의 특정 ID/label을 card나 retrieval rule에 심지 않는다.
- exact ID 매칭, 임의 score cutoff, 긍정 선례의 OR voting으로 최종 label을 바꾸지 않는다.
- 선례가 없거나 retrieval score가 낮다는 사실을 violation 근거로 삼지 않는다.
- fixed Gemma의 공고별 정상 호출을 대체하지 않는다.
- 법령 원문·인터넷 자료를 새 prompt context에 재주입하지 않는다.

이 전략은 높은 비용이 드는 20k 확장 전에 retrieval 적합성과 teacher quality를 먼저
반증하려는 계획이다. 성공하더라도 최종 판단은 Gemma가 현재 공고의 원문 evidence로
내려야 한다.
