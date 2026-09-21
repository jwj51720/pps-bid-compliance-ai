# EXP-C001B C24 completion-limit result

실행일: 2026-09-21

상태: **INCOMPLETE — transport fix는 채택, 결과는 baseline에 미병합**

## 변경

OpenRouter request의 deprecated `max_tokens`를 `max_completion_tokens`로 바꿨다. 의미 입력,
prompt, JSON schema, owner, reducer, 설정값 1,536은 그대로다. EXP-C001에서 복구된 5건을
재사용하고 남은 C24 실패 4건만 attempt 2로 실행했다.

## 결과

| 항목 | 결과 |
| --- | ---: |
| 대상 | 4 |
| 추가 복구 | 1 |
| whitespace length 재실패 | 3 |
| 실패 completion tokens | 각 1,536 |
| v24 label 변화 | 0 |
| 다른 v/e 변화 | 0 |
| dev200 Macro positive-F1 | 0.7796736645 |

`PPS-DEV-069`만 v24=0으로 복구됐다. `PPS-DEV-063`, `PPS-DEV-133`, `PPS-DEV-141`은
정확히 1,536토큰에서 whitespace loop로 종료했다. 따라서 transport 제한 필드는 수정됐지만
동일 schema 재시도만으로 structured-output failure를 제거할 수 없다는 가설이 확정됐다.

## 결정

- `max_completion_tokens` transport 수정은 이후 active code에 유지한다.
- retry 결과를 canonical baseline CSV에 병합하지 않는다. 점수도 동일하다.
- 같은 prompt/schema의 추가 재시도는 하지 않는다.
- 다음은 계획대로 native v24 atomic-relation schema를 구현한다.

산출물:

- `outputs/clean-exp-c001b-c24-completion-limit-v1/recovery_preflight.json`
- `outputs/clean-exp-c001b-c24-completion-limit-v1/response_attempts/`
- `outputs/clean-exp-c001b-c24-completion-limit-v1/run_report.json`
