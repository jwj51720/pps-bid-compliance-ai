# v11 예외 누락과 참가제한 역할의 분리 감사

작성: 2026-09-15, dev / mac. 오프라인 진단이며 유료 실험 결과가 아니다.

## 대조 대상

- 현재 기준: `data/derived/decision_cards_v10_v6_v7_scope.json`, v11 prompt_text.
- organizer 법령: 판로지원법 시행령 원문 파일 118–124행, 제7조 제1·2항.
- source packet: `outputs/product-item-source-audit-20260915/`의 PPS-DEV-14/060/063.
- 실제 과거 입력/출력: `outputs/exp-208-relation-checklist-after-source-dev200-c4/inputs.jsonl`
  및 `predictions.jsonl`의 동일 ID.

## 입증된 카드 누락

현재 v11 카드는 경쟁제품 적용성, 중소기업자간 경쟁 제한 부재, 전체 문서 absence 결합만
명시한다. 시행령 제7조 제1항의 네 특별사유 및 제2항의 공고/전자시스템 사유 기재 경로는 없다.
네 사유는 법률상 우선구매·수의구매 대상 중소기업제품, 제8조에 따른 조합 추천 수의계약,
중소기업자간 경쟁 유찰 후 다른 경쟁방식 재입찰, 특별한 기술·용역 등 공공기관 특별사정이다.
일반 우선조달의 제2조의3 예외와 혼합해서는 안 된다.

이 누락 교정은 우선 **적용 가능한 예외가 있는 공고의 FP 억제** 가설이다.
현재 v11의 zero recall을 예외 부족 때문이라고 설명할 수는 없다.
단순 협상방식·향후 재입찰 안내·기술 단어를 예외의 실제 적용으로 간주하지 않는다.

## matched 양성의 실제 전달과 출력

gold 양성 6건 중 exact-code matched인 3건을 별도로 대조했다.

| ID | saved prompt의 경쟁제품 사실 | saved tokenizer count | v11 pass / final | parse errors |
| --- | --- | --- | --- | --- |
| PPS-DEV-14 | 통학운송서비스, 별도 적용조건 없음 | 12167 | 0 / 0 | 없음 |
| PPS-DEV-060 | 행사대행 후보 3행 및 10억원 미만 조건 | 7927 | 0 / 0 | 없음 |
| PPS-DEV-063 | 시설물경비서비스 및 기계·특수경비/자회사 수의계약 제외 조건 | 19076 | 0 / 0 | 없음 |

세 건은 모두 saved 입력 한 pass이며 제품 heading·이름·조건이 실제 user message에 존재한다.
Python 후처리 대상 v2/v3/v21과도 다르다. 따라서 **이 세 FN을 제품조건 전달 누락,
여러 pass AND merge, evidence gate 또는 malformed recovery로 설명할 증거는 없다.**
saved token count는 당시 입력의 기록이지 새 tokenizer 재측정 또는 vLLM runtime 증명이 아니다.

## 다음에 검증할 역할 구분 — 아직 원인 확정 아님

원문에는 직접생산확인증명서 참가요건이 있다. 060/063의 metadata 조항호내용에도 기업범위가
표기되어 있지만, 이것을 실제 공고 원문에 있는 중소기업자간 경쟁 참가제한과 같은 사실로
취급하면 부재 판정이 달라질 수 있다. 주최 측 item의 요구가 공고의 명시적 제한인지,
다른 자격요건을 통한 실질 제한도 포함하는지 먼저 source 기준으로 확정해야 한다.

모델은 이유를 출력하지 않았으므로 직접생산 요건 또는 metadata를 보고 0을 냈다고 단정하지 않는다.
그 구분을 강제하는 새 카드나 schema를 gold에 맞춰 만들지도 않는다. 이 truth condition은
현재 카드의 적용성/제한 존재 순서로 표현 가능한 것으로 보이며, 새 multi-item 관계 schema를
도입할 필요가 아직 입증되지 않았다.

## 진행 gate

1. 예외 source-fidelity 교정과 참가제한 역할 교정을 서로 다른 가설로 유지한다.
2. matched 3건과 unknown 3건을 혼합해 exact 입력이 모두 없었다고 보고하지 않는다.
3. 고정 fast에 v11 양성은 1건, 고정 holdout에는 0건이다. 별도 독립 양성 검증 설계 없이
   recall 개선을 확인했다고 주장하거나 dev200 유료 실행으로 확대하지 않는다.
4. CSV 후보 검색은 기존 exact-code 합의를 바꾸는 별도 제안이며 사용자 승인 전 구현하지 않는다.

이번 감사에서 카드 asset, pipeline, merge, canonical/submission policy는 변경하지 않았다.

## 후속: organizer 정의의 해상도 확인

원본 `data/raw/open/data/항목표.json`의 v11은 항목명, absence 여부, 법령 매핑만 제공하며
비고는 비어 있다. 따라서 직접생산 참가요건만 있는 공고를 v11의 명시 제한으로 인정할지에
대한 operational 정의를 이 파일에서 얻을 수 없다.

organizer 판로지원법 원문 56–57행(제7조 제1항)은 중소기업자 대상 제한경쟁/지명경쟁을
규정한다. 같은 원문 108–114행(제9조 제1·3·4항)은 중소기업자의 직접생산 확인과 증명서
발급을 다룬다. 두 제도는 연결되어 있으므로 **직접생산은 중소기업과 무관한 자격이다**라는
카드 수정은 source와 맞지 않는다. 반대로 증명서 요구만으로 제7조의 계약방식·명시 조건이
모두 충족된다고 이 문서가 증명하는 것도 아니다.

이 대조는 현재 3개 FN이 단순 명시적 중소기업 문구 부재로 복구 가능하다는 가설을 약하게 만든다.
gold 3건을 맞추기 위해 `직접생산만 있으면 중소기업 제한 없음`을 카드에 새로 쓰지 않는다.
법적 사실과 organizer operational label의 경계가 확인되기 전에는 이 역할교정 가설의
V/E·V-only paid 비교를 시작하지 않는다. 이는 V-only의 성능 패배 결과가 아니라 source gate의
미충족이다. 예외의 source-correct 보완 가능성은 별개로 남는다.
