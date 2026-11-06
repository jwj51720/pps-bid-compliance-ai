# N004: v1 bidder-owned relation fast20

작성일: 2026-09-22

N003 typed axes는 N002의 실적·지역 FP를 크게 줄였지만, 대학병원이
과거 납품실적의 상대방인 문장을 입찰자 기관유형으로 오판했고,
소기업·소상공인 기업규모 제한도 target=Y로 보았다. N004는
source view, v31 card, axis schema, reducer, provider를 고정하고
target의 관계 주어만 명확히 한다.

- target=Y의 기관·법인·조직·인력·시설은 **현재 입찰자 자신이
  무엇인가 또는 무엇을 보유하는가**를 참가조건으로 요구해야 한다.
- 과거 실적의 발주기관·납품처·고객·사업대상에 기관명이 등장하는
  경우는 target=N이다.
- 중소기업·중기업·소기업·소상공인 등 기업규모 조건은 v1의
  특정기관/임의 조직·시설 제한이 아니므로 target=N이다.
- 법정 등록·허가·면허, 실적, 지역, 제품·기술, 평가·이행의 기존
  target=N 계약은 유지한다.

base는 N003이고 허용 변경은 `prompt.task` 및 새 task hash audit
path뿐이다. final evidence/reducer 완화는 섞지 않는다. fast20 gate는
invalid 0, TP=3, FP=0, FN=0, U=0을 목표로 한다. v1 baseline이
fast20 F1=1.0이므로 이를 못 맞추면 독립 owner 보존 근거가 없다.
통과하더라도 independent holdout20을 먼저 실행한다.
