# Native v17 relation-view phase B plan

작성일: 2026-09-22

Phase A의 v17 full-source task는 대상 106건 중 25건이 14,848-token
한도를 초과했다. 이 문제는 문서를 자르거나 초과 공고를 제외해 해결하지
않는다. v17 truth condition의 네 관계—실제 조달대상, 경쟁제품 적용성,
중기업 참가범위, 적용 예외—에 필요한 원문을 모든 제공 문서에서
source-grounded하게 모으는 별도 view를 시험한다.

사전 고정할 선택 규칙:

1. 각 문서 첫 1,300자를 overview로 보존한다. 공고 제목/사업개요가
   앞에 없을 가능성은 별도로 기록한다.
2. 기업범위·확인서 표기는 각 hit 전후 500자, 법정 예외·유찰·우선조달
   표기는 전후 600자, 10자리 제품코드 표기는 전후 150자를 보존한다.
3. 겹치는 원문 window는 같은 문서 안에서 병합한다. 후보 수나 char
   quota로 뒤쪽 문서를 버리지 않는다.
4. 각 문서별 네 범주 hit count와 `NOT_FOUND`를 기록한다. `NOT_FOUND`는
   해당 표현을 찾지 못했다는 뜻이지 v17=0이 아니다.
5. 모든 span은 원문 doc ID/type/order/hash/offset으로 역검증한다.

이 lexeme은 organizer v17 카드의 의미 범주에서만 정했고 dev FP/FN
ID에 맞춘 문구를 추가하지 않는다. 정확한 source view와 card/meta/
metadata+문서 product facts를 합친 **실제 최종 메시지**를 106건
전부 exact tokenizer로 검사한다. dev gold의 e17과 C005D v17 근거
span은 선택 완료 후 coverage 진단에만 사용한다. 미포함 근거가 있거나
overflow가 남으면 paid call을 하지 않는다.

통과 시에도 이 view가 예외의 부재, 실제 구매대상 관계, 전체 24개
semantic input을 완전히 증명하는 것은 아니다. v17 fast20의 독립 manifest,
allowed changes, mock, rendered review, 24-item owner 영향 확인 후에만
유료 품질 gate로 진행한다.
