# INC-122 — compact official-law summary 결과

**판정: C branch 실패. 법령 summary를 holdout/dev-200으로 승격하지 않는다.**

## 재현 정보

- model `google/gemma-4-26b-a4b-it`, temperature 0, seed 20260906
- EXP-120 candidate source의 card-v6, 4,000-character ordered document V/E prompt
- 32 notices, profile별 8, two paired arms, 64 successful calls
- reported cost: control `$0.02595`, compact-summary `$0.02966`
- cohort IDs SHA `a13c98dd…`; prior Gemma INC-119/INC-121 only excluded. Luna cohorts는
  서로 다른 model이므로 제외하지 않았다.
- compact legal summary는 profile마다 2,115--2,215 characters, supplied official-law
  ledger의 source-reviewed condition/exception summaries만 사용했다.

## 결과

| Arm | Macro positive-F1 | Micro recall | Absence FP | 결론 |
|---|---:|---:|---:|---|
| card v6 control | **0.12500** | **0.25000** | 6 | comparator |
| compact legal summary | 0.08333 | 0.18750 | 1 | reject |
| treatment − control | **-0.04167** | **-0.06250** | -5 | recall loss dominates |

모든 64 calls는 transport/parse failure 없이 완주했다. 따라서 효과 부재는 JSON failure나
partial-row artifact가 아니다. summary는 absence false positives를 줄였지만 v2의 true
positive를 잃었고, v6/v7/v9/v10/v11/v12/v13/v14/v16/v18/v21 등의 positive recall을
회복하지 못했다.

## 해석과 결정

Luna official-law ledger의 반복 이득을 Gemma에 그대로 일반화할 수 없다. INC-119의 16건
`+0.01713`은 이 새 profile-balanced cohort에서 재현되지 않았고, 짧은 legal context는
Gemma를 precision 쪽으로 과도하게 기울였다.

동일 cohort에서 summary wording, length, 혹은 full-law injection을 바꿔 재시도하지 않는다.
현재 C branch를 닫고, 다음은 LLM prompt가 아니라 source-complete가 이미 입증된 v2/v3/v21
결정적 predicate를 EXP-120 전체 prediction에 고정 합성하는 E branch의 offline composition
audit이다.
