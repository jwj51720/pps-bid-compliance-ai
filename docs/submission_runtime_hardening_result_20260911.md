# Submission runtime hardening result

작성: 2026-09-11, dev / mac

## 결론

제출 실패 원인을 은폐할 수 있던 runtime/schema 차이를 줄이고 단계별 계측을 추가했다.
공식 test runtime에서 필수인 record key는 `id`, `docs`, `meta`로 제한하고, dev 진단용
completeness field는 존재할 때만 타입을 검증한다. vLLM 초기화는 공식 baseline처럼
`PPS_QUANT=none`일 때 quantization 인자를 생략하며, 기본 batch size는 128로 맞췄다.

batch size 증가는 동시 처리량 설정일 뿐 EXP171의 총 model request 수를 줄이지 않는다.
따라서 120분 timeout이 해결됐다는 근거는 아니다.

## 방어 검증

- canonical/runtime prompt·staged·postprocess policy 일치 검사
- seed, temperature, max output token reserve 일치 검사
- batch/retry/GPU utilization/`PPS_QUANT` 기본값 검사
- model load, input, stage-1 prepare/generate, final prepare/generate, postprocess,
  CSV 및 total wall-time 로그
- 최소 공식 schema와 optional diagnostic field의 타입 단위 테스트
- full pytest: `192 passed`
- exact staged 10건 mock: 15 + 15 requests, 49-column validation PASS

## 남은 limitation

현재 환경에는 evaluator와 같은 GPU/vLLM이 없으므로 실제 model load, batch throughput,
KV-cache pressure와 120분 이내 종료는 미검증이다. public timeout의 가장 직접적인 원인은
EXP171이 test 규모에서 두 단계 전체-source request를 다수 생성하는 call topology이며,
batch 64였다는 사실만으로 timeout 원인을 확정할 수 없다.
