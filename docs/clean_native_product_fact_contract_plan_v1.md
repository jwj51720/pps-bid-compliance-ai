# Native organizer product-fact contract (N1)

작성일: 2026-09-21

목표는 L41 FactBuilder 또는 legacy 제품 렌더러 없이, organizer가 제공한
`meta.세부품명번호목록`과 `competition_products_v1.json`을 **exact 10자리
세부품명번호**로만 결합해 사람에게 읽히는 사실을 만든다. 제품명만으로 매칭하거나
CSV 특이사항을 Python에서 적용/비적용 라벨로 바꾸지 않는다.

입력 계약:

- metadata가 비어 있으면 `코드 미제공` 사실만 반환한다. 이는 적용 불가 판정이 아니다.
- 각 metadata 항목의 대괄호 안 10자리 코드만 식별한다. 중복 코드는 최초 순서를
  유지해 한 번만 기록한다. 식별할 수 없는 비어 있지 않은 입력은 조용히 0으로
  넘기지 않고 입력 오류로 처리한다.
- CSV에 exact 코드가 있으면 세부품명과 특이사항 원문을 그대로 보존한다.
  없으면 `일치 행 없음` 사실을 보존한다. 어느 경우도 제품 적용 결론을 내리지 않는다.
- LLM용 문장은 코드별 단일 행과 한국어 사실만 포함하고, 내부 상태 키·코드 배열·
  raw metadata JSON은 포함하지 않는다. 특이사항이 있으면 그 문장을 그대로 제시해
  Gemma가 구매 대상 및 예외 조건과 대조하도록 한다.

검증: 200 dev records의 모든 비어 있지 않은 코드 입력을 parse하고, 입력 원문별
코드 수/CSV exact match/특이사항 수를 출력한다. 기존 프롬프트나 final owner에는
아직 연결하지 않는다. 따라서 이 단계의 품질 점수는 없으며 paid call도 없다.
이 fact contract를 채택할 때에는 별도 fully resolved manifest, 24개 semantic-input
review, rendered short/attachment/overflow, mock, fast20→holdout20→dev200 gate가 필요하다.
