# S016R — v19 repeat JSON fence 0-call replay 계획

작성일: 2026-09-23

상태: **계획 고정 — raw response 확인 후 구현**

## 원인

S016의 새 8개 task는 transport 관점에서 전부 `finish_reason=stop`이고 길이 절단이 없었다.
그러나 6개 task는 provider가 schema-valid JSON을 단일 Markdown `json` code fence로 감쌌다.
strict parser는 이를 `invalid_json`으로 거부했고, 같은 verbose task를 두 번 더 생성해도 같은
serialization이 반복됐다.

읽기 전용 probe로 바깥 fence만 제거했을 때 8/8이 기존 semantic parser를 통과했다. 이는 prompt,
schema, 관측값, evidence, reducer의 문제가 아니라 transport serialization 표면 문제다.

## 통제

- base config:
  `experiments/manifests/clean_exp_s016_v19_positive_repeat_diagnostic_v1.json`
- allowed change: `json_fence_serialization_recovery`
- LLM calls: 0
- embedding calls: 0
- raw source:
  `outputs/clean-exp-s016-v19-positive-repeat-diagnostic-v1/responses/`
- 허용 adapter:
  1. 전체 content가 정확히 하나의 ` ```json ... ``` ` 또는 ` ``` ... ``` ` fence인 경우만 인식
  2. 내부가 JSON object로 parse되는 경우에만 fence 제거
  3. 내부 JSON의 key/value/string/whitespace는 수정하지 않음
  4. fence 밖 문자가 있거나 내부 JSON이 invalid이면 복구하지 않음
- 기존 parser, quote resolver, reducer, consensus gate, selected IDs: 변경 없음
- 다른 23개 V/E: S001 stored rows 그대로

## 검증

1. raw response SHA와 adapted response를 task별로 기록한다.
2. adapted JSON object가 raw fence 내부 object와 구조적으로 exact equal인지 확인한다.
3. recovered task 수는 사전 관측한 6개와 같아야 한다.
4. 모든 10개 repeat가 semantic-valid여야 한다.
5. S016에 사전 고정한 gate를 그대로 적용한다.
6. 새 호출이 0인지 report와 response provenance로 확인한다.

이 replay는 JSON 포장을 복구할 뿐 판정 정책을 추가하지 않는다. 따라서 S016의 repeat 가설을
평가할 수 있지만, 결과는 여전히 adaptive dev diagnostic이며 독립 일반화 증거가 아니다.

## 사전 기대값(승격 기준이 아님)

read-only probe에서 fence 제거 후 새 8개 결과는 양성 7, 음성 1이었다. 기존 repeat 두 건을
합치면 TP 6/6, FP 2/4가 남아 예상 v19 F1은

```text
2*6 / (2*6 + 2 + 0) = 0.8571428571
```

이다. S016R 정식 결과가 이 값과 다르면 adapter/provenance 구현 오류로 간주한다.
