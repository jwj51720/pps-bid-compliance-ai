# N007 v2 semantic-input contract review (prepaid, in progress)

작성일: 2026-09-22

활성 항목은 v2 하나다. 이는 24항목 전체 판정 실험이 아니다.
실제 task audit: `outputs/clean-native-v2-performance-task-v1/dev200/audit.json`.
short=`PPS-DEV-179`, attachment=`PPS-DEV-196`, longest=`PPS-DEV-140`의
저장된 system/user 메시지를 직접 읽었다. `PPS-DEV-02` 양성도 별도로
읽었다. 전수 200건의 exact tokenizer admission은 통과했으나,
tokenizer 통과와 의미 완결은 다른 검사다.

| v2 필요 요소 | 주최측 원천 → 렌더링 위치/실제 span | 판정 |
| --- | --- | --- |
| 적용 대상·고시금액 | 항목표 v2·제공 고시·관련 시행령/규칙 → v32 card `물품 제조·구매/공급·용역`, `2억 3천만원`, `7억 1천만원`, `입찰추정가격` | 존재 |
| 계약법·업무·가격 | organizer metadata → 모든 sample의 `[v2에 필요한 주최측 입력 사실]`; `PPS-DEV-02`는 국가계약법, 물품(내자), 83,100,000원 | 존재 |
| 과거 실적이 참가자격이라는 1 조건 | 공고문 원문 → `PPS-DEV-02` `[P001 | 공고문/D0 0:1287]`의 `3. 입찰참가자격` 아래 외국 학술지 공급계약 3천만원 이상 실적 | 존재 |
| 실적이 평가·이행 자료일 뿐인 0 조건 | 제안요청서/과업지시서 원문 → `PPS-DEV-140` `[P015 | 제안요청서/D1 6451:6929]`의 `기술능력 평가`, `[P007 | 과업지시서/D2 5238:5680]`의 분기별 실적 보고 | 존재 |
| 문서 유형·출처 연결 | 공고문·규격서·과업지시서·제안요청서·예외공표서 중 제공된 374개 문서를 모두 scan; selected span에 type/doc-id/offset/SHA-256 유지; gold e2 7/7 | 형식·coverage 통과 |
| 기관규칙 및 별도 허용·예외 | v32 card + 공고·metadata의 실제 적용 근거; system `enterprise_rule_applies`, `explicit_allowance` 축 | 문구 존재, source sufficiency 추가 검토 필요 |

`PPS-DEV-140`의 과업지시서에는 `실적`이라는 단어가 반복되지만
대부분 계약이행·평가 관련이다. 이것을 참가자격으로 오인하지 말라는
0 조건과 원문 예시가 실제 메시지에 함께 존재한다. 첨부문서를 제외하지
않았고, `PPS-DEV-196`의 규격서도 source view에 포함됐다.

2026-09-22 fast20 추가 검토: short 양성 `PPS-DEV-062`의 참가자격과
추정가격 227,272,727원이 같은 실제 메시지에 있다. attachment 음성
`PPS-DEV-131`은 추정가격 2,138,181,818원과 공고·제안요청서가 보이고,
longest 음성 `PPS-DEV-165`는 참가자격 부분과 별도의 정량평가 실적
부분이 모두 보인다. fast 양성 `PPS-DEV-042`, `PPS-DEV-069`의 계약법·
업무구분·입찰추정가격 및 gold e2 source span도 렌더링에 존재한다.
따라서 v2의 적용·1/0·예외·문서·metadata semantic-input contract는
현재 후보 메시지에서 검사 가능한 상태다.

선택되지 않은 원문 부분에 예외 근거가 숨어 있을 잔여 위험은 있다.
이는 14,000자 cap 구조의 실험 위험으로 명시하고, fast 결과의 FP/FN과
source span을 확인한다. versioned manifest, allowed-policy-change
preflight, mock, malformed/evidence 검증은
`clean_exp_n007_v2_fast_preflight.md`에 기록했다. 현재 모델 점수는
없다. 이 문서의 법령 요약은 offline audit용이며 prompt에는 넣지 않는다.
