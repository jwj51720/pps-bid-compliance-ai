# N008H v2 독립 holdout20 결과

작성일: 2026-09-22

## 결과

`configs/dev_prompt_holdout_v1.json` 20건에서
TP/FP/FN/TN=1/0/0/19, precision=recall=F1=1.0이었다.
양성 `PPS-DEV-053`의 원문 evidence는 선택 span `[P002]`에
정확히 포함돼 positive evidence validity 1/1이다. 하지만
invalid 출력 1/20이 있으므로 안정성 PASS라고 부르지 않는다.
fast20 3/0/0 F1=1.0과 독립 holdout20 1/0/0 F1=1.0의 방향은
일치하나, holdout 양성 1건이라 dev200 검증이 필요하다.

## 재현과 실행 비용

- manifest: `experiments/manifests/clean_exp_n008h_v2_participation_holdout_v1.json`.
  N008 fast에서 cohort/panel만 변경, preflight PASS.
- 실제 입력 review: `docs/clean_exp_n008h_v2_holdout_preflight.md`.
- output: `outputs/clean-exp-n008h-v2-participation-holdout-v1/holdout20/`.
- 20 logical/new calls, OpenRouter wall 139.226초. usage prompt
  103,476, completion 9,330 tokens, response cost 필드 합계 USD
  0.01192496. 이 시간은 evaluator vLLM runtime 근거가 아니다.
- `pytest -q` 158 passed (실험 직전).

## invalid 원인과 다음 gate

`PPS-DEV-089`는 gold=0, final=0이지만 raw completion의
`finish_reason=length`, usage completion 8,192 tokens, content 길이
12,351자였다. 앞부분에는 `performance_participation=N`과 나머지
축이 있었으나 뒤에 공백 줄이 대량 반복돼 `quote` 및 완결 JSON 없이
종료됐다. parser는 이를 `transport_or_length`로 invalid→0 처리했다.
request payload의 `max_completion_tokens`는 1,024였으므로 저장된
provider usage 8,192와 불일치한다. 원격 provider가 왜 그렇게
동작했는지는 이 한 응답만으로 단정하지 않는다. 재호출해서
무효를 지우거나 parser를 바꿔 같은 정책의 결과로 섞지 않는다.

정책 자체의 양성 재현은 유지됐다. 다음 dev200은 **promotion gate이자
malformed/runtime 진단**으로 실행한다. 불량 출력이 반복되면 최종
owner 채택 전에 별도 serialization/transport 실험을 선언해야 한다.
dev200에서 TP/FP/FN과 invalid 위치·근거·토큰·시간을 모두 기록하고,
frozen v2 F1=1.0을 넘었다고 주장하지 않는다.
