# Native full-input prompt feasibility probe

작성일: 2026-09-21

목적: 독립 native core가 24개 카드 v31 + 항목별 human-readable metadata +
exact-code 제품 사실 + 공고의 **모든 원문 문서**를 한 Gemma 메시지에 넣을 수
있는지 exact tokenizer로 측정한다. 이는 품질 실험이 아니라 0-call 입력·
runtime 설계 probe다. 단일 호출에서 24개 V/E를 바로 예측하는 정책을
승격하거나 과거 complete-fact one-stage의 낮은 성능을 무시하지 않는다.

- code: `src/pps_ai/views/native_full_prompt.py`만 사용한다. frozen L41,
  legacy, reference loader를 import하지 않는다.
- 원문은 정해진 문서 유형 순서로 모두 넣고 doc ID/type을 붙인다.
  본문 문자를 줄이거나 제목만 추출하지 않는다.
- 법령 원문·case RAG·raw metadata JSON·내부 status/code 배열은 넣지 않는다.
- 카드 v31의 `prompt_text`는 그대로 렌더하고 source asset hash를 남긴다.
- 원문 미입력이나 초과 예산은 조용히 잘라내지 않고 보고한다.
- 정확한 chat-template token 수, 문서 유형별 수·길이, short/attachment/
  largest/overflow 실제 system/user message 경로를 저장한다.

판정 gate: 200/200 공고, 374/374 문서, source hash 일치, 24/24 카드,
metadata/product 사실 누락 0. Budget 초과가 있으면 core 1-call 가능하다고
주장하지 않는다. 문서 분할 topology는 별도 설계와 absence-v merge를
검증하기 전까지 구현하지 않는다. v4 카드 금액 scope 충돌과 v20/v24
원문 관계 검증 gap은 여전히 semantic-input 미완으로 표시한다.
