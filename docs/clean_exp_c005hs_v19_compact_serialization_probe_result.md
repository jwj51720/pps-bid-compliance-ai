# EXP-C005HS v19 compact serialization target probe 결과

작성일: 2026-09-21

상태: PASS — C005 v19 구조의 holdout completeness gate 해소

## 실행 결과

`PPS-DEV-192__p01` 한 건만 compact schema로 새로 호출했다.

- 신규 provider call: 1
- 정상 C005H 응답 재호출: 0/17
- model: `google/gemma-4-26b-a4b-it`
- finish reason: `stop`
- prompt/completion tokens: 1,996 / 127
- latency: 6.289초
- compact parser: valid
- verbose adapter + 기존 relaxed quote parser: valid
- 기존 C005H task hash: MATCH

두 번 연속 verbose 응답에서 1,536 completion token을 소모하며 whitespace loop가 났던 target이
compact 응답에서는 127 token으로 정상 종료했다. 이는 의미 field를 제거하지 않고 key와 enum의
표현만 줄여 pathological serialization trajectory를 해소했다는 진단과 일치한다.

## holdout20 재조립

compact target 응답을 기존 verbose observation으로 1:1 역변환한 뒤 정상 저장 응답 17개와 기존
`reduce_v19_with_quote_resolution`로 합쳤다.

- final status: PASS
- records/columns/unique IDs: 20 / 49 / 20
- invalid responses: 0
- non-v19 changed cells: 0
- v19 positive without evidence: 0
- v19: TP 0, FP 0, FN 0
- Macro positive-F1: 0.4305555555555556

holdout20에는 v19 양성이 없으므로 v19 FP 제거가 positive-F1 숫자를 올리지는 않는다. 그러나
C004S의 holdout v19 FP 1을 C005H/C005HS가 0으로 줄였고, C005R fast20에서는 유일한 v19 양성을
TP로 잡아 TP 1, FP 0, FN 0이었다. 따라서 양성 recall 신호와 독립 음성 precision 신호의 방향이
일치한다.

## 해석과 제한

C005HS가 증명한 것은 compact serialization이 실패 target의 9개 의미 field를 보존하면서 transport
completeness를 회복한다는 점이다. compact serialization을 모든 공고에 적용했을 때도 판정 분포가
동일하다고 증명한 것은 아니다. 따라서 다음 dev200 승격에서는 이미 fast/holdout에서 검증된 verbose
task를 primary로 유지하고, strict semantic parse가 실패한 task에만 compact schema를 최대 한 번
사용하는 fail-closed recovery가 가장 작은 정책 변화다.

C004S dev200 `0.8037378357`은 아직 품질 baseline이다. C005는 dev200을 통과하기 전까지 canonical
baseline으로 승격하지 않는다.

## 재현 경로

- manifest: `experiments/manifests/clean_exp_c005hs_v19_compact_serialization_probe_v1.json`
- raw compact response:
  `outputs/clean-exp-c005hs-v19-compact-serialization-probe-v1/probe_response/PPS-DEV-192__p01.json`
- adapted response:
  `outputs/clean-exp-c005hs-v19-compact-serialization-probe-v1/adapted_response/PPS-DEV-192__p01.json`
- metrics/run report/submission:
  `outputs/clean-exp-c005hs-v19-compact-serialization-probe-v1/`
- tests: 61 passed
