# Native document product-code fact contract

작성일: 2026-09-22

문제: `meta.세부품명번호목록`이 비어 있어도 실제 공고 원문에 10자리
세부품명번호가 나타날 수 있다. 메타데이터 조회 불가를 `비경쟁제품`으로
해석하면 v10–v18의 적용 전제를 잃는다. C005D v17 FP의 한 공고에서도
이 상황이 관찰됐지만, 새 extractor는 ID/label 예외가 아니다.

가설: 모든 제공 문서에서 독립적인 10자리 숫자 token을 스캔하고
doc ID/type/offset/hash에 연결하면 organizer CSV exact-code 후보를
추가로 발견한다. 다음을 절대 하지 않는다.

- 문서에 코드가 있다고 그것을 실제 구매대상으로 확정하지 않는다.
- CSV에 일치 행이 있다고 특이사항의 조건을 Python에서 평가하지 않는다.
- 문서 코드 미발견·CSV 불일치를 비경쟁제품 판정으로 바꾸지 않는다.
- 일치 행 이름으로 fuzzy matching하거나 dev 라벨에 맞춘 코드 규칙을
  추가하지 않는다.

출력은 source span, 주변의 변경 없는 짧은 원문 문맥, CSV 세부품명,
CSV 특이사항 원문이다. 반복 코드도 최초 등장 위치와 문서별 출처를
보존한다. prompt에는 JSON/status/code 배열이 아닌 코드별 한국어
사실 문장을 쓴다.

0-call dev200 감사에서 모든 374개 문서 scan, metadata에 없는 문서 코드,
exact CSV match, `특이사항` 보존, token count를 기록한다. 실제 구매대상·
직접생산 참가요건·예외의 의미 관계를 Gemma 또는 독립 owner가 판단하기
전까지는 품질 점수나 final label 변화를 주장하지 않는다.
