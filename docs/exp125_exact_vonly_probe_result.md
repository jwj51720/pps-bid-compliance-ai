# EXP125 — Exact baseline V/E와 V-only 출력 계약 probe 결과

계획: [exp125_exact_vonly_probe_plan.md](exp125_exact_vonly_probe_plan.md)  
configs: `configs/config.exp125a-exact-baseline-ve-fast-panel.yaml`,
`configs/config.exp125b-exact-baseline-vonly-fast-panel.yaml`  
raw artifacts: ignored `outputs/exp-125a-exact-baseline-ve-fast-panel/`,
`outputs/exp-125b-exact-baseline-vonly-fast-panel/`

## 사전 검증

- preflight: A는 diff 없음, B는 `prompt.output_mode` 하나뿐.
- mock: 각 20/20 완료, CSV schema validation 통과.
- exact Gemma tokenizer admission: dev-200 전체가 양 arm 모두 1 pass다. 최대
  prompt token은 V/E 4,206, V-only 4,122로 14,848 budget 이하다.
- 같은 `PPS-DEV-01` request 비교에서 user message와 model/temperature/max token/
  seed/provider 값은 같았다. system output instruction 및 JSON schema만 달라졌다.
- preview artifact를 처음 같은 디렉터리에 병렬 기록해 한 파일이 덮어써졌으나, provider
  실행 전에 arm별 경로로 다시 생성해 대조했다. 실험 결과 artifact에는 충돌이 없었다.

## 실행

| Arm | calls | runtime | prompt / completion tokens | cost | Macro positive-F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| A — exact V/E | 20/20 | 63.164초 | 75,381 / 15,173 | $0.0129241 | **0.171958** |
| B — exact V-only | 20/20 | 22.750초 | 73,701 / 3,633 | $0.0082105 | **0.137500** |

V-only는 completion token을 76.1%, wall time을 64.0%, observed API cost를 36.5%
줄였다. 그러나 Macro-F1은 0.034458 하락했다. parse failure는 양쪽 0건이었다.

## label-level 분석

| 항목 | V/E `(TP, FP, FN, F1)` | V-only `(TP, FP, FN, F1)` | 핵심 변화 |
| --- | --- | --- | --- |
| v3 | (2, 2, 1, .571) | (2, 1, 1, .667) | FP 1개 제거 |
| v4 | (1, 0, 2, .500) | (0, 0, 3, .000) | 유일 TP 소실 |
| v5 | (0, 3, 1, .000) | (0, 0, 1, .000) | FP 3개 제거, F1 이득 없음 |
| v13 | (1, 7, 0, .222) | (0, 5, 1, .000) | 유일 TP 소실 |
| v17 | (1, 4, 0, .333) | (0, 2, 1, .000) | 유일 TP 소실 |
| v19 | (1, 2, 0, .500) | (0, 2, 1, .000) | 유일 TP 소실 |
| v21 | (0, 2, 2, .000) | (1, 1, 1, .500) | TP 1개 회복 |
| v24 | (1, 6, 2, .200) | (1, 2, 2, .333) | FP 4개 제거, TP 유지 |

전체 predicted positive는 37개에서 21개로 감소했다. label cell 480개 중 24개가 바뀌었고,
그 24개만 보면 V/E의 정답 cell은 7개, V-only의 정답 cell은 17개였다. 즉 V-only는
일반적인 negative cell 정확도와 FP를 개선했다. 하지만 gold-positive가 적은 항목에서
각각 하나뿐인 TP 다섯 개를 지웠다. Macro positive-F1은 zero-F1 항목의 FP를 줄여도
보상하지 않기 때문에 이 recall 손실이 더 크게 작용했다.

V/E의 non-absence evidence validity는 37 positive 중 0.757이었다. V-only row의 e는
의도적으로 비어 있어 validation warning이 21개 발생했다. 이는 V-only가 제출 후보가
아니라는 계획상 예상된 결과이며, label metric 계산에는 사용하지 않았다.

## 결정

EXP125B는 사전 통과 조건(+0.02, recall 비감소, parse 0) 중 성능과 recall 조건을
모두 충족하지 못했다. **V-only 문구 재작성, independent holdout, dev-200, evidence
recovery 구현을 진행하지 않는다.**

동료의 0.32734는 단순히 e 생성을 생략한 효과로 설명되지 않는다. 다음 조사 대상은
동료 policy의 실제 chat templateㆍpromptㆍdecoderㆍcontext assembly contract이며, artifact를
받기 전에는 이를 추정해 재구성하지 않는다. 별도로 진행할 수 있는 큰 후보는 generic
case RAG가 아니라, source-grounded precedent retrieval이 label-blind하게 성립하는지의
비용 없는 feasibility audit이다. 해당 audit이 기존 BGE retrieval 실패를 이길 명확한
source/condition alignment를 보이지 않으면 Luna self-label 비용을 사용하지 않는다.
