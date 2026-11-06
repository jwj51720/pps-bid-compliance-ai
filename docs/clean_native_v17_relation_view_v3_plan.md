# Native v17 relation-view v3: actual procurement target

작성일: 2026-09-22

v2는 카드의 주요 예외 표현을 회수했지만 실제 구매내역·사업내용이 각
문서 첫 1,300자와 코드/기업/예외 window 밖에 있으면 v17의 제품
적용 전제를 잃는다. v3는 organizer 카드의 `실제 조달대상` 조건을
검증하기 위한 구매대상 설명 범주만 추가한다.

사전 등록 탐색어: 공고명/사업명/입찰건명, 구매내역/구매품목/구매물품/
물품내역, 입찰에 부치는 사항, 사업내용, 과업개요/과업내용/과업목적,
품명/용역명/구매대상/납품내역. 각 hit 전후 450자를 원문 substring으로
보존하고 겹침을 같은 문서 안에서 병합한다. v2의 overview, enterprise,
exception, product-code 범주와 schema·metadata·CSV 사실은 고정한다.

0-call 검증에서 106개 대상 공고의 모든 190개 문서 scan, source span
검증, 14,848-token admission, 기존 gold/C005D e17 quote coverage,
v2 대비 새 purchase hit/selected span/token 증가를 기록한다. 짧은
공고·첨부·최대 prompt의 실제 rendered message를 읽는다. source
heading lexeme의 부재를 구매대상 부재나 비경쟁제품 판정으로 쓰지 않는다.
실패 시 v3로 유료 실행하지 않는다.
