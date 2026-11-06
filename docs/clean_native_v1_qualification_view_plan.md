# Native v1 qualification input: source-only phase A

작성일: 2026-09-22

v1은 C005D에서 TP=7, FP=0, FN=0으로 F1=1.0이지만 final cell은
frozen L41 판정이다. 독립 기준선에는 참가 가능 여부를 실제로
제한하는 원문을 native 코드가 문서 provenance와 함께 제시하고,
Gemma가 적용대상/제한/허용 대안·예외의 관계를 판단하는 경로가
필요하다. 이 단계는 **모델 호출 없는 입력 완결성 검사**이며 점수
또는 새 final owner의 결과가 아니다.

주최측 `항목표.json`의 v1 정의는 참가자격 특정기관 제한이다.
versioned v31 카드는 특정 기관군뿐 아니라 입찰자 자체의 조직,
상시 인력, 보유 시설/서비스망도 살피되 일반 등록·면허·신고,
실적·지역·제품·기술 기준, 평가·계약이행 조건과 혼동하지 말라고
정한다. v1 전용 metadata/제품 CSV fact는 필요하지 않다.

전 문서를 원문 순서로 scan한다. `참가/참여 자격·가능 여부`의
표현과 카드가 지칭하는 기관/조직/인력/시설 표현 주변의 exact
source span을 수집한다. 검색어의 존재·부재를 Python label로
변환하지 않는다. 각 문서 도입부와 발견된 span의 source id,
doc id, offset, hash를 유지한다. 모든 문서에서 찾아도 한도를
넘는다면 임의 top-k로 버리지 않고 별도 overflow 계약을 설계한다.

0-call gate: dev200의 200건/모든 제공 문서를 검사하고 gold 및
C005D의 nonempty e1 substring coverage, tokenizer 14,848
admission, short/attachment/overflow rendered messages를 기록한다.
coverage가 높아도 v1 진리조건이 완결됐다는 증명은 아니므로,
source 역할·허용 대안의 누락을 실제 메시지에서 따로 검토한다.
paid 단계는 별도의 fully resolved manifest와 preflight,
fast20→holdout20→dev200 gate를 통과해야 한다.
