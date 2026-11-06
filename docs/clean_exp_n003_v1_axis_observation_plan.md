# N003: v1 restriction-axis observation fast20

작성일: 2026-09-22

N002는 v1 카드에 0 조건이 있어도 final Y/N 단계에서 실적 2건과
지역 2건을 v1로 흡수했다. N003은 source view/card/provider를 고정하고
Gemma의 역할을 다음 두 축의 관측으로 제한한다.

1. `target`: 실제 참가자격에 특정 기관 종류·법인 형태 또는 입찰자
   자체의 조직·상시 인력·보유 시설·서비스망 제한이 있는가(Y/N/U).
   실적, 지역, 법정 등록·면허·신고, 제품·기술 조건은 target=N이다.
2. `allowed`: target=Y인 바로 그 제한에 카드의 허용 근거가 있는가
   (Y/N/U). target=N이면 U다.

quote는 target=Y일 때 그 제한을 직접 보여주는 exact substring이고,
target=N/U이면 null이다. reducer는 `target=Y and allowed=N`일 때만
v1=1, target=N일 때 v1=0, 나머지는 U로 유지한다. 이는 새 Python
문구 rule이 아니라 typed state의 명시적 진리표다.

base N002 대비 허용 변경은 prompt task/schema와 typed reducer뿐이다.
동일 fast20 20건으로 invalid 0, TP>=2, FP<=2, U<=4를 요구한다.
통과해도 independent holdout 전에는 승격하지 않는다.
