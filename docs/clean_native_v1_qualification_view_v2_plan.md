# Native v1 qualification view v2: qualification-linked context

작성일: 2026-09-22

v1 view v1은 카드의 기관·인력·시설 어휘를 모든 문서에서 독립적으로
탐색해 43/200개 prompt가 14,848-token 한도를 넘었다. 특정 기관
표현은 계약이행·제안서 양식·발주기관 설명에도 반복된다. v2는
**실제 참가 가능 여부를 나타내는 원문 anchor**를 중심으로 전후
450자를 취하고, 문서 앞 1,000자 개요를 유지한다. 기관/인력/시설
단어는 anchor 밖에서 단독으로 window를 만들지 않는다.

사전 무호출 진단에서 C005D의 7개 positive e1 quote는 모두
참가자격 anchor 시작점에서 195자 이내였다. 이는 dev quote
coverage만 말해 주며 숨은 v1 조건의 recall을 보장하지 않는다.
v1 view 자체와 결과는 보존하고 v2를 별도 버전으로 audit한다.

0-call gate는 200건/374문서 scan, 모든 exact span 검증,
gold/C005D e1 coverage, exact tokenizer admission, short/attachment/
largest/overflow rendered review다. 한도를 통과하더라도 실제
참가제한의 역할과 허용 대안이 한 조각에 함께 들어가는지 확인하기
전에는 paid run을 열지 않는다. 후보 없음은 0 판정이 아니다.
