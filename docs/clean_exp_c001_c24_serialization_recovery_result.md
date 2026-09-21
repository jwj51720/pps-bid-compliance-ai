# EXP-C001 C24 serialization recovery result

실행일: 2026-09-21

상태: **INCOMPLETE — canonical baseline에 채택하지 않음**

## 가설과 통제

frozen L41 baseline의 C24 `finish_reason=length` 9건만 동일 task로 한 번 재시도했다. prompt,
schema, source view, owner, reducer, generation 설정은 바꾸지 않았다.

- base: `outputs/clean-reference-l41-openrouter-dev200-v1/`
- experiment: `clean-exp-c001-c24-serialization-recovery-v1`
- 기준 task: 600개 hash exact match
- 선택된 재시도: C24 9개
- 선택되지 않은 정상 응답: 591개
- 다른 v final cell 변경 허용: 0개

## 결과

| 항목 | 결과 |
| --- | ---: |
| 재시도 | 9 |
| 정상 JSON 복구 | 5 |
| 동일 whitespace length 재실패 | 4 |
| 허용된 v24 label 변화 | 0 |
| 금지된 v1-v23/e1-e23 변화 | 0 |
| dev200 Macro positive-F1 | 0.7796736645 |
| fast20 | 0.6791666667 |
| holdout20 | 0.3888888889 |

복구된 5건은 모두 v24=0이었으며 기존 fallback 0과 같아 점수는 변하지 않았다. 남은 실패는
`PPS-DEV-063`, `PPS-DEV-069`, `PPS-DEV-133`, `PPS-DEV-141`이다.

## 발견된 transport 계약 위반

manifest의 completion 제한은 1,536이지만, 실패 응답의 OpenRouter usage는 모두 정확히
`completion_tokens=8192`였다. body가 `max_tokens`를 사용했는데 OpenRouter 공식 API에서는
이 필드가 deprecated이고 `max_completion_tokens` 사용을 권고한다. 따라서 이 실행은
“동일 1,536-token 제한으로 한 번 재시도”라는 가설을 실제 provider에 강제하지 못했다.

이는 v24 semantic policy 문제가 아니라 local remote transport 문제다. evaluator vLLM의
`SamplingParams(max_tokens=1536)`와 혼동하지 않는다.

공식 문서:

- <https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request>
- <https://openrouter.ai/docs/guides/features/structured-outputs>

## 결론

단순 동일 재시도는 5/9만 복구하므로 충분하지 않다. EXP-C001은 incomplete로 고정한다.
다음 transport-only 실험 EXP-C001B는 request field만 `max_completion_tokens=1536`으로 바꾸고,
남은 4건만 새 append-only attempt로 실행한다. prompt/schema/owner/reducer는 그대로 유지한다.

산출물:

- `outputs/clean-exp-c001-c24-serialization-recovery-v1/recovery_preflight.json`
- `outputs/clean-exp-c001-c24-serialization-recovery-v1/response_attempts/`
- `outputs/clean-exp-c001-c24-serialization-recovery-v1/run_report.json`
- `outputs/clean-exp-c001-c24-serialization-recovery-v1/metrics.json`
