# D0 결과 — temperature 0.2 decoding 다양성

실행일: 2026-09-07 (mac / dev)

계획: [decoding_diversity_d0_plan.md](decoding_diversity_d0_plan.md)

## 계약 확인

`exp-126a-exact-baseline-ve-fast-panel-temp02`는
`exp-125a-exact-baseline-ve-fast-panel`을 base로 두고 preflight를 통과했다.
effective policy diff는 `llm.temperature: 0.0 -> 0.2`와
`llm.seed: 20260826 -> 20260907`뿐이다. prompt, metadata, 4,000자 document
context, V/E JSON schema, model, max token, parser, evidence 검증, merge는 같았다.

Mock 20건과 config/OpenRouter/experiment-control test 10건을 통과한 뒤 고정
fast panel 20건을 실행했다. 상세 raw response와 error는 ignored
`outputs/exp-126a-exact-baseline-ve-fast-panel-temp02/`에 있다.

## headline 결과

| arm | Macro positive-F1 | predicted positives | evidence validity | completion tokens | wall time |
| --- | ---: | ---: | ---: | ---: | ---: |
| EXP125A, temp 0 | 0.171958 | 37 | 75.68% | 15,173 | 63.2초 |
| EXP126A, temp 0.2 | 0.208532 | 39 | 82.05% | 21,552* | 136.0초 |

`*` PPS-DEV-042의 첫 response가 strict JSON을 지키지 못하고 탭을 반복하며
8,192 completion tokens를 사용했다. pipeline은 retry 뒤에 final row를 만들었지만,
이 malformed attempt는 실행 품질 결함이다.

## 실제 변화 분석

480 V cells 중 26개(5.42%)가 control과 달랐다.

| control → temp0.2 | gold 0 | gold 1 | 의미 |
| --- | ---: | ---: | --- |
| 0 → 1 | 11 | 3 | true positive 3개 회복, false positive 11개 추가 |
| 1 → 0 | 11 | 1 | false positive 11개 제거, true positive 1개 손실 |

따라서 변화 자체는 충분히 있었지만, 3개의 TP 회복은 v2/v4/v24에 집중됐고 v17의
유일한 TP를 잃었다. 항목별 TP/FP/FN/F1 변화는 다음과 같다.

| v | control | temp0.2 | 해석 |
| --- | --- | --- | --- |
| v2 | 0/0/3/0.000 | 1/0/2/0.500 | 실제 양성 1개 회복 |
| v4 | 1/0/2/0.500 | 2/0/1/0.800 | 실제 양성 1개 회복 |
| v5 | 0/3/1/0.000 | 0/2/1/0.000 | FP 하나 제거, TP 없음 |
| v15 | 0/1/1/0.000 | 0/2/1/0.000 | FP 증가 |
| v17 | 1/4/0/0.333 | 0/6/1/0.000 | 유일한 TP 손실 및 FP 증가 |
| v19 | 1/2/0/0.500 | 1/1/0/0.667 | FP 하나 제거 |
| v21 | 0/2/2/0.000 | 0/3/2/0.000 | FP 증가 |
| v24 | 1/6/2/0.200 | 2/4/1/0.444 | TP 회복 1개, FP 감소 2개 |

나머지 16개 항목은 이 arm에서 TP/FP/FN이 동일했다. fast-panel F1 상승은
v2/v4/v24의 소수 회복 효과이지, 24개 항목 전반의 안정된 개선 신호가 아니다.

## Gate 판정 및 다음 방향

D0b gate 중 label 다양성은 통과했지만 `parse error = 0` 조건을 위반했다.
특히 malformed response가 configured `max_tokens=1536`을 넘어 8,192 tokens까지
생성된 것은 OpenRouter upstream structured-output 계약을 신뢰할 수 없다는 직접
증거다. 3-sample submission이라면 이 tail latency가 2시간 runtime에도 위험하다.

**결정: D0b의 추가 seed, vote 구현, holdout/dev-200 확장을 하지 않는다.**
온도/seed ensemble은 현 runtime에서 큰 방향이 아니다. 다음 연구는 decoder가 아니라
source facts의 법적 역할을 손실 없이 관찰ㆍ판정하는 입력/판정 topology로 한정한다.
