# V2 bounded source view: no-call result

작성일: 2026-09-22

## 결과

| audit | v1 unbounded | v2 bounded |
| --- | ---: | ---: |
| 검사 문서 | 374/374 | 374/374 |
| gold e2 exact coverage | 7/7 | 7/7 |
| 후보 source spans | 1,076 | 1,748 |
| 후보 총 문자 | 1,866,962 | 1,273,659 |
| envelope 최대 토큰 | 19,584 | 10,401 |
| task용 1,200-token reserve 충족 | 185/200 | 200/200 |

v2는 문서의 첫 부분과 item 근거 관련 anchor를 모든 제공 문서에서
검사한다. 길게 이어진 조각을 최대 1,600자 atomic window로 나누고,
label-blind relevance 순위로 총 14,000자 이내를 선정한다. selected
조각은 원본 document ID/order/offset/SHA-256을 보존한다. source view는
label이나 frozen/reference response를 읽지 않는다.

`outputs/clean-native-v2-performance-view-v2/dev200/audit.json`에 200건
coverage와 토큰 수, short/attachment/largest 및 fast/holdout 양성의
rendered envelope를 보존했다. 이 수치는 아직 **실제 final task의
tokenizer admission이 아니다**. system/schema가 추가되면 exact
rendered message를 다시 감사해야 한다.

## 유료 실험 전 의미 계약 충돌

v31 v2 card는 적용 범위를 `물품제조·용역`으로 서술한다. 그런데 dev200
gold 양성 `PPS-DEV-02`의 organizer metadata `업무구분`은 `물품(내자)`이고,
원문 참가자격은 `외국 학술지 공급계약을 3천만원 이상 체결한 실적이 있는 자`다.
현재 입력만으로 이 물품 공급을 card의 `물품제조`에 넣어야 하는지,
organizer operational label이 card 문구보다 넓은지 확정할 수 없다.

따라서 N007 계획의 `goods_or_service_scope`를 현재 카드 문장 그대로
구현하면 입력 누락이 없어도 구조적 FN 가능성이 있다. 이 상태의 paid
fast20은 실행하지 않는다. organizer 항목표·관련 제공 법령·운영진 설명
간의 적용범위를 먼저 감사하고, 필요하면 card 정책 변경을 별도 버전으로
선언해야 한다. dev label 하나를 코드 조건이나 prompt 예시로 심지 않는다.
