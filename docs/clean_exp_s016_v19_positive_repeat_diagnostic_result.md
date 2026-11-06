# S016 — v19 양성-only 동일 task 반복 진단 결과

실행일: 2026-09-23

상태: **INCOMPLETE — 모델판단이 아니라 JSON fence serialization으로 strict parse 실패**

## 실행 무결성

- predeclared selected tasks: 10
- existing exact-task repeats reused: 2
- new notices called: 8
- invalid-only semantic retries: 최대 2회
- task hash: C005D dev200와 10/10 exact match
- tokenizer: 1,705~5,500 / 14,848 tokens
- source coverage: selected notice의 모든 문서 inspected
- rendered-input/semantic contract: 10/10 PASS
- output:
  `outputs/clean-exp-s016-v19-positive-repeat-diagnostic-v1/`

## 관측 결과

새 8건 중 2건은 raw JSON, 6건은 다음 형태로 반환됐다.

    ```json
    {...schema-valid object...}
    ```

모든 response는 `finish_reason=stop`이었고 completion token 상한 절단이 아니었다. code fence가
있는 6건은 strict parser가 `invalid_json`으로 거부했다. 두 번의 same-task semantic retry도
같은 fence 표면을 반복했으므로 S016의 strict 결과는 semantic-invalid 6건, status
`INCOMPLETE`다.

이 상태에서 invalid를 0으로 취급한 v19 F1 `0.6667`과 macro `0.8117`은 법률판단 성능이 아니다.
serialization failure를 label 0으로 바꾼 인공 결과이므로 승격·기각 근거로 사용하지 않는다.

## 원인 분리

fence 내부만 읽는 일회성 read-only probe에서는 6건 모두 기존 schema, candidate key, enum,
quote shape를 통과했다. 기존 exact/unique-whitespace evidence resolver도 통과했다. 따라서 다음을
구분한다.

- 확인된 원인: 단일 outer Markdown JSON fence
- 기각된 원인: prompt token overflow, finish truncation, candidate omission, schema field omission
- 아직 S016 자체로 미판정: repeat consensus의 TP/FP 효과

raw response를 고쳐 쓰지 않고 별도 zero-call S016R에서 fence-only adapter를 선언해 판정한다.

## 비용 교훈

invalid-only retry는 의미 오류와 serialization wrapper를 구분하지 못해 6개 task에 불필요한 호출을
추가했다. 제출에서는 JSON fence를 deterministic parser recovery로 먼저 처리하고, 내부 JSON도
invalid인 경우에만 재생성해야 한다. 이는 label rule이 아니라 parsing robustness다.
