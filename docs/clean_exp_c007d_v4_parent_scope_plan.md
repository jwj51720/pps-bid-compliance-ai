# Clean EXP-C007D: v4 candidate parent-scope plan

작성일: 2026-09-21

## 문제와 가설

C007CR에서 드러난 유일한 새 FP(049)는 공고문 제출서류 목록의 실적증명서를
Gemma가 입찰참가자격으로 분류한 것이다. 해당 candidate는 발췌문 자체에
`7. 규격 입찰서(제안서) 제출 → 라. 제출서류` 상위 제목이 없었다. 이 제목은
실제 원문 약 1천자 앞에 있으므로 기존 350자 앞보기에서 빠진다.

가설: candidate마다 **원문에 존재하는 상위 절 제목과 위치 provenance**를
별도 source-only 필드로 제공하면 Q/E/F/C 역할 혼동이 감소한다. 키워드로
최종 v4를 override하지 않으며, `r,m,x,a,n`은 여전히 Gemma가 판정한다.
사용하는 제목은 원문 그대로여야 하고 doc ID, 문서유형, 문자 offset, SHA-256과
결합해야 한다. 제목 추출이 불확실하면 UNKNOWN으로 표시하여 Python이 역할을
추정하지 않는다. 모델은 제목과 candidate 전체를 함께 읽는다.

## 수학적 기준과 범위

- 비교 기준 C005D fast20 v4 F1 `0.8`, C007CR `0.857143`(FP 1),
  C007C strict의 `1.0`은 invalid fallback 의존이므로 승격 기준에서 제외.
- 최소 목표: fast20 TP 3 / FP 0 / FN 0, invalid 0; macro `0.736111`.
- 단일 항목 교체의 macro 증가 상한은 v4 F1 변화량 / 24다. C005D 대비
  달성 가능한 fast20 증가량은 `(1 - 0.8)/24 = 0.008333`이다.
- 구조 변화는 v4 source view의 parent-scope 표현과 해당 role prompt만.
  quote resolution은 C007CR로 고정하고 다른 23개 셀·provider·card·reducer는 고정.
- 금액 scope는 여전히 별도 unresolved 문제이므로 relation-only diagnostic이다.

## 필수 gate

1. C007CR을 base_config로 한 fully resolved manifest와 최소
   `allowed_policy_changes` 선언. 049만 보고 제목 규칙을 fit하지 말고 전 200건
   label-blind source audit: 모든 문서 검사, candidate/gold evidence coverage,
   title provenance와 잘못된 절 연결 비율 확인.
2. exact tokenizer admission, overflow policy, 0-call dry-run/mock,
   source/call topology와 per-notice token 변화 기록.
3. short complete / attachment / largest or overflow와 049 실제 rendered
   system/user를 사람 검토; active v4 semantic-input contract 확인.
4. fast20은 `configs/dev_fast_panel_v1.json`만. malformed 0,
   non-v4 changes 0, v4 evidence valid; FP가 남거나 TP가 줄면 중단.
5. independent holdout20을 통과한 뒤에만 dev200. 금액 scope 충돌은
   organizer item/source와 label을 별도 replay로 검토한 후 canonical 판단.

제출 artifact 또는 동료 프롬프트 문구와의 유사도 조정이 목적이 아니다.
source provenance를 갖춘 독립적 의미 구조를 만들고 성능으로 검증하는 것이 목적이다.
