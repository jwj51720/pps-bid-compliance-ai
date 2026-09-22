# Clean L41 runtime-hardened submission plan

작성일: 2026-09-22

## 목적과 성능 기준

이번 산출물은 hash-pinned reference L41을 독립 구현했다고 주장하지 않는다. reference
artifact의 24-item 실행 그래프를 그대로 유지하고, 제출 중 batch/structured-output 실패가
전체 실행을 중단하거나 곧바로 arm fallback으로 이어지는 runtime 위험만 좁게 보강한
**L41-derived submission candidate**다.

- 재현된 전체 dev200 기준: Macro positive-F1 `0.7796736645`
- 공고당 기본 Gemma 호출: `r10`, `B`, `C24` 각 1회, 합계 3회
- C005D `0.8151465658`은 저장된 L41 출력 위에 v3/v19 specialist를 추가한 hybrid 품질
  실험이므로 이번 제출 후보의 점수로 부르지 않는다.
- N008D `0.823529`은 v2 한 항목의 F1이며 24-item 제출 점수가 아니다.

## 허용 변경

기준 artifact:

- `dist/reference/submit.zip`
- SHA-256 `a06feff77ffbc4a6f2a47cd0e2d322f341f652ca865d1b9cf53919012c8ca216`

허용하는 변경은 runtime recovery와 보고뿐이다.

1. batch backend exception 발생 시 해당 batch를 이등분하여 격리 실행한다.
2. 단일 request까지 실패하면 invalid placeholder로 보존하고 다음 recovery 단계에 넘긴다.
3. `finish_reason != stop`, empty/invalid 표시, JSON object parse 실패인 arm만 동일
   message/schema로 1회 추가 생성한다.
4. retry 대상·복구·미복구 수와 backend exception을 runtime report에 기록한다.
5. 어떤 notice의 세 arm이 모두 미복구여도 기존 arm fallback으로 조립하여 반드시 답을 낸다.
6. 조립·retrieval 등 run-level 예외가 발생하는 최악의 경우에도 입력 ID 전체를 다시 읽어
   49열 emergency zero-label CSV를 atomic write하고 degraded 상태를 report에 남긴다.

변경하지 않는 것:

- prompt, schema, source view, metadata/fact, retrieval, deterministic predicate
- item owner와 마지막 writer 순서
- evidence validation과 final label
- model, tokenizer/chat template, temperature, seed, max tokens, quantization
- 기본 세 arm 및 batch size 128

따라서 정상 응답만 나온 notice의 판정은 기준과 동일하다. retry가 발동한 notice는 모델을
다시 생성하므로 결과가 달라질 수 있으며 runtime report에서 식별 가능해야 한다.

## 제출 안전 gate

1. ZIP top-level에 `script.py`, `requirements.txt`, `runtime_config.json`만 둔다.
2. server mode는 `PPS_DATA_DIR`, `PPS_OUTPUT_DIR`, `PPS_MODEL_DIR`, `PPS_EMBED_DIR`를 모두
   요구하고 network/Hugging Face online mode를 비활성화한다.
3. staged ZIP 자체를 새 디렉터리에 풀어 organizer test sample 10건 mock을 실행한다.
4. 결과는 10 rows, 정확히 49 ordered columns, input-order unique IDs, binary v,
   NFC/source-substring evidence 계약을 통과해야 한다.
5. mock fault injection으로 batch exception 분할, invalid-only retry, recovered/unresolved,
   all-arm-invalid continuation과 run-level emergency CSV를 검증한다.
6. compressed 2 GB/extracted 8 GB 한도와 파일명 30자 이하를 검사한다.

## 제한

- 현재 환경에는 evaluator GPU/vLLM이 없어 실제 1,853건 120분 완료를 증명할 수 없다.
- invalid retry는 조건부 호출을 늘린다. 정상 structured output이면 추가 호출은 0이다.
- reference의 public `0.7+`는 사용자 제공 관측이며 이 패키지의 public score를 보장하지 않는다.
- 이 candidate는 clean native 독립 baseline 목표를 대체하지 않는다.
