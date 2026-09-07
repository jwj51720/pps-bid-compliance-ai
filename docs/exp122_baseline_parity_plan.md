# EXP122 — organizer baseline prompt parity 계획

## 발견

root `config.yaml`은 `profile: official_baseline_v1`이라고 적혀 있었지만
`metadata_style`을 명시하지 않았다. shared pipeline의 default는 `full_json`이므로,
organizer baseline의 `- 필드: 값` metadata 목록이 아니라 JSON block이 실제 input으로
들어갔다. submission entrypoint도 이 필드를 pipeline으로 넘기지 않았다.

이는 EXP109을 소급 수정해 재측정하는 문제가 아니다. historical EXP109 config/output은
그대로 보존하고, 새 EXP122A만 exact baseline control로 취급한다.

## 가설

organizer가 배포한 prompt와 byte-level로 같은 system/user message를 쓰면, JSON metadata
renderer가 추가한 구조·토큰·attention 차이를 제거한다. 이 실험은 card, RAG, document
범위, output schema, decoding, evidence handling을 변경하지 않는다.

## 설계

- base: historical EXP109 config.
- policy change: `prompt.metadata_style: full_json → official_lines` 하나.
- cohort: frozen `dev_fast_panel_v1` 20건. fast-panel 결과는 후보 선별용이고 승격 근거가
  아니다.
- provider: existing OpenRouter Gemma, temperature 0, seed 20260826, V/E schema.
- preflight, exact prompt parity assertion, mock runner를 통과한 뒤에만 20 calls를 한다.

## 판정

이 probe는 구조 수정의 유효성 확인용이다. fast-20 F1이 historical EXP109과 다르더라도
remote-provider variation을 포함하므로 즉시 dev200이나 제출로 승격하지 않는다.
다음은 prompt byte parity가 유지된 상태로 독립 fast cohort 또는 dev200 control을 설계한다.
반대로 malformed output, evidence validity 하락, 또는 semantic regression이 확인되면
canonical exact-baseline 설정 자체는 유지하되, 이를 성능 개선이라고 부르지 않는다.
