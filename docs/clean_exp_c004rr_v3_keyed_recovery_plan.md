# EXP-C004RR — v3 keyed dev200 invalid-response recovery

작성일: 2026-09-21

## 배경과 가설

EXP-C004R dev200은 v3 TP 7 / FP 1 / FN 1 / F1 `0.875000`, Macro
`0.8009804827`로 사전 최소 품질 gate를 통과했다. 그러나 61 specialist responses 중
`PPS-DEV-08`, `PPS-DEV-157` 두 건이 whitespace loop로 `finish_reason=length`가 되어 전체 상태는
INCOMPLETE다.

두 응답은 prompt 1,076/1,136 tokens의 단일-candidate task인데 completion이 각각 8,192 tokens를
소모했다. Runtime request는 이미 `max_completion_tokens=1536`을 전송했으나 upstream response는
이를 지키지 않았다. 의미판정·source view 문제가 아니라 확률적 serialization failure라는 가설로
동일 exact task를 각각 한 번만 재호출한다.

## base와 허용 변경

- base manifest: `experiments/manifests/clean_exp_c004r_v3_keyed_full_fast_v11.json`
- base output: `outputs/clean-exp-c004r-v3-keyed-full-fast-v11/dev200/`
- targets: `PPS-DEV-08`, `PPS-DEV-157`
- allowed changes:
  - invalid response 두 건의 append-only attempt 1회
  - 성공한 attempt를 해당 task response로 선택해 동일 reducer 재생
- 고정:
  - exact task hash, source view, prompt, schema, metadata, reducer
  - provider/generation parameters
  - 나머지 59 specialist responses
  - L41 base 24 cells와 v3 외 모든 final cells

Legacy는 import·실행·복사·생성하지 않는다. Attempt는 별도 output의
`response_attempts/V3/<id>/attempt_001.json`에 저장하고 base response를 덮어쓰지 않는다.

## gate

1. 두 task hash가 base dev200 preflight hash와 exact match.
2. base에서 local-invalid target이 정확히 두 건임을 재확인.
3. new calls <= 2, normal responses replay 0.
4. recovered local valid 2/2, remaining invalid 0.
5. v3 외 changed cells 0; evidence exact-substring validation PASS.
6. 품질은 동일하거나 향상. Recovery 자체를 semantic 개선으로 부르지 않는다.

## 유료 실행 전 검증

- manifest diff: undeclared 0, unused declaration 0, PASS
- reconstructed specialist tasks: 61
- base preflight task hashes: 61/61 exact match
- detected local-invalid targets: 정확히 `PPS-DEV-08`, `PPS-DEV-157`
- normal responses excluded: 59
- new call upper bound: 2
- active tests: 40 passed

따라서 exact-task append-only recovery 2호출을 실행할 수 있다.
