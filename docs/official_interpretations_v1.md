# 공식 판정기준 registry v1

이 registry는 대회 공개 페이지와 배포 항목표의 판정 해석을 추적하기 위한 연구
provenance다. 웹 원문·외부 법령을 runtime prompt나 제출 asset에 넣지 않는다. 카드에
반영하는 경우에도 아래 내용을 사람이 읽을 수 있는 짧은 판단 문장으로만 옮긴다.

## Source hierarchy

1. 배포 `data/항목표.json`과 법령 package
2. DACON 대회 페이지 및 DACON 운영진의 공개 답변
3. 설명회 영상은 대회 페이지/배포 자료와 충돌하면 우선하지 않음

운영진은 dev가 실제 업무 이력 기반의 참조용 표본이며 일부 노이즈가 있을 수 있고,
평가셋은 별도 다층 검증으로 관리된다고 설명했다. 그러므로 이 registry는 dev 사례를
규칙의 출처로 사용하지 않는다.

## v2 — 고시금액 미만 실적제한

- Source: [DACON 운영진 답변, 2026-08-31](https://dacon.io/competitions/official/236754/talkboard/417262)
- Official interpretation: 고시금액 미만 제조·용역에서 실적제한을 실제 참가자격으로
  두면 위반이며, 지방계약법의 소액수의 견적입찰 특례만 별도로 확인한다.
- Card v6 alignment: 방향은 일치한다. 이번 branch에서는 문구를 자동 변경하지 않고
  적용 계약방식/특례가 card에서 충분히 명확한지만 audit한다.

## v9 — 과업지시서 특정 모델명 명시

- Source: [DACON 운영진 답변, 2026-09-01](https://dacon.io/competitions/official/236754/talkboard/417272)
- Official interpretation: 규격서 등을 포함한 공고 자료에 특정 모델명 또는 제조사명이
  명시되면 v9가 성립한다. 규격·가격 동시입찰 여부와 감점형 평가 방식은 배제 요건이
  아니다.
- Card v6 divergence to audit: card v6는 동등품 허용·특수 사유를 일반적인 0 조건으로
  서술한다. 공식 답변이 이 예외들을 배제 요건으로 인정하지 않았으므로, candidate는
  명시적 모델·제조사 요구 자체를 우선하는 문장으로 바꾼다. 단순한 기존 장비 설명이나
  실제 요구가 아닌 언급까지 자동 위반으로 넓히지는 않는다.

## v13 — 중기간 경쟁제품 소기업·소상공인 제한

- Source: [DACON 운영진 답변, 2026-09-01](https://dacon.io/competitions/official/236754/talkboard/417272)
- Official interpretation: 경쟁제품 경쟁입찰에서 소기업·소상공인으로 참가자격을 한정해
  중기업을 배제하면 성립한다. 금액 구간은 일반 성립 요건이 아니다. 소액수의 견적입찰은
  별도 예외이며, 일반제품의 1억원 미만 특례를 경쟁제품으로 옮기면 안 된다.
- Card v6 alignment: 경쟁제품 + 실제 참가자격 한정이라는 핵심은 일치한다. candidate는
  금액을 조건으로 오해하지 않도록 0/1 조건을 명시하되, product applicability가
  불명확한 경우 1로 추정하지 않는 원칙은 유지한다.

## v24 — 공고서와 나라장터 입력값 상이

- Source: [DACON 운영진 답변, 2026-09-01](https://dacon.io/competitions/official/236754/talkboard/417272)
- Official interpretation: 대조 축은 항목표 비고에 적힌 예산·계약방법·지역제한·업종
  네 가지다. 제한사유/조항호내용의 성격 비교는 v24가 아니라 v2~v4의 쟁점이다.
- Card v6 alignment: 현재 card의 네 축과 일치한다. 이번 branch에서는 코드 변경이나
  card 문구 변경 없이 regression target으로만 둔다.
