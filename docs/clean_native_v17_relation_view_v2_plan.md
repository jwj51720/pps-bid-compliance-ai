# Native v17 relation-view v2: exception-source completeness

작성일: 2026-09-22

v1 view는 106/106 Gemma input을 14,848 tokens에 admit했지만,
organizer 카드 v31이 열거한 다른 법률의 우선구매·수의·지명계약 및
특정 성능·기술·품질 예외 표현이 source 탐색 lexeme에 없었다. 기존
gold 근거 1개와 C005D positive 근거 13개를 모두 보존한 사실은
**예외의 부재 증명**이 아니다.

v2는 exception source 탐색어에 카드의 위 범주만 추가한다. overview,
enterprise/product windows, context margin, schema, metadata/CSV facts,
token budget 및 Python label 정책은 v1과 동일하다. 이는 dev 오답 ID를
겨냥한 문구가 아니다. v1 audit/task를 덮어쓰지 않고 별도 output에서
106개 notice의 exact admission, source spans, short/attachment/largest
rendered messages, 예외 hit 증가량을 비교한다.

v2가 fit해도 문서에 없는 사실을 입증할 수 없으므로 유료 호출 gate는
여전히 24-item semantic-input review 및 v17 owner contract의 별도
검토가 필요하다. `NOT_FOUND`를 최종 음성/양성 label rule로 바꾸지 않는다.
