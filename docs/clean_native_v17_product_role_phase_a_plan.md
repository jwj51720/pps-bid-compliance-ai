# Native v17 product-role phase A: full-source admission

작성일: 2026-09-22

수학적 우선순위: frozen C005D dev200의 v17은 TP 6 / FP 7 / FN 0,
F1 `0.631579`다. 그 항목만 완벽해질 때 Macro 개선의 비현실적 상한은
`(1 - 0.631579)/24 = 0.015351`이다. 더 큰 상한의 v24/v9/v4는
각각 기존 native schema 실패, 규격서 근거 누락, holdout 일반화 실패가
확인돼 있다. 따라서 이번에는 v17의 **제품코드 역할**이라는 입증된
입력 손실을 먼저 다룬다. 이는 전체 독립 baseline 재구축의 첫 owner
실험이지 v17 ID별 규칙 보정이 아니다.

v17 truth condition은 ① 입찰추정가격 1억원 미만인 일반 물품·용역,
② 실제 구매대상이 적용 경쟁제품이 아님, ③ 중기업도 참가할 수 있는
중소기업 범위의 참가제한, ④ 그 범위를 허용하는 적용 예외 없음의
AND 관계다. metadata 코드가 없거나 CSV가 불일치해도 ②는 증명되지
않는다. 문서 코드 48개 공고-코드쌍에는 실제 구매대상뿐 아니라
직접생산 참가요건도 섞일 수 있으므로 Gemma가 역할·`특이사항`을
원문과 함께 관측해야 한다.

Phase A는 모델 호출 없이, 가격/업무유형의 확정적 적용 가능성 gate를
통과한 공고에 v17 카드 v31, item-scoped metadata, metadata+문서
exact-code facts, **모든 제공 원문**을 넣은 rendered task의 token을 잰다.
gate는 후보 호출 절감에만 쓰며 gate 밖은 v17=0이 카드의 명시 조건이다.
문서가 한도에 안 들어가면 이 task를 자르거나 source selector로 대체하지
않고 admission 실패를 기록한다. 그 경우 paid fast20을 시작하지 않고
v17에 필요한 source relation을 보존하는 별도 context 설계로 넘어간다.

미래 유료 gate: fully resolved manifest와 allowed changes, short/attachment/
overflow 실제 message, v17 semantic contract와 다른 23개 owner contract,
exact tokenizer, 0-call mock, source/evidence validity, isolated output,
fast20→independent holdout20→dev200. Phase A 수치를 점수로 부르지 않는다.
