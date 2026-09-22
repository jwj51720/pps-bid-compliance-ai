# Native source-window coverage probe

작성일: 2026-09-22

가설: 24개 긴 카드와 원문 전체를 한 호출에 넣는 것은 137/200건에서
admission 실패했지만, **모든 제공 문서를 실제로 스캔한 exact source
windows**에서 제한된 양의 원문을 고르면 많은 항목의 양성 근거를
보존할 수 있다. 이는 label 판정이나 최종 prompt 전략이 아니라
source-view의 coverage/손실을 재는 0-call probe다.

- 모든 문서는 950자 window, 450자 stride로 색인한다. overlap ≥500자라
  e 근거 최대길이 500자를 단일 window에 담을 수 있다.
- 선택 점수는 organizer 카드의 주제어를 설명하는 사전 선언한 한국어
  lexeme의 다양한 등장 수다. dev label·오답 ID·골드 증거를 선택에 쓰지 않는다.
- 각 제공 문서에서 최소 한 window를 먼저 고른 후 나머지를 점수순으로
  고른다. 선택된 span은 원문 byte/character offset과 doc SHA로 검증한다.
- `char_cap=18,000`은 고정된 audit용 제한이다. 이후 exact tokenizer로
  실제 선택 pack token을 측정하며, prompt budget 적합성을 추정하지 않는다.
- dev200의 원문과 gold nonempty evidence 54개를 **선택 후에만** 대조해
  exact 근거 보존율, 항목/문서 유형별 miss를 보고한다. 검증용 gold로
  lexeme나 cap을 fit하지 않는다.

gate: 전체 window index에서 374/374 문서와 54/54 exact gold evidence를
복원해야 한다. bounded view는 별도 수치로 공개하고, 100%가 아니면
그 자체로 full semantic input이라고 주장하지 않는다. 이 probe를 paid
quality result 또는 canonical policy로 승격하지 않는다.
