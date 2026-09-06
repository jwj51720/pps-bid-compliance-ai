# INC-122 — compact official-law summary Gemma pilot

## 가설

EXP-120의 card v6와 4,000자 원문 V/E policy에, metadata profile별로 고정한
official-law condition/exception summary를 더하면 Gemma가 법적 적용성·예외를 더 잘
구분해 macro-F1을 높일 수 있다.

## 한 가지 변화

Control은 current EXP-120 candidate source의 `build_system_prompt`와
`build_messages(..., 4000)`을 그대로 사용한다. Treatment은 그 same system prompt 뒤에
profile-specific legal ledger의 24개 `model_summary`만 추가한다. 해당 summaries는 supplied
official-law chunks를 검토해 만든 기존 static artifact이며, raw law 전체·Luna prediction·dev
label·case example은 넣지 않는다.

두 arm은 model, temperature, seed, response schema, V/E output, card v6, metadata와 ordered
4,000-character document input을 모두 고정한다. 최종 evidence는 여전히 공고 원문 substring만
허용하며 법령 summary는 evidence가 아니다.

## Cohort와 실행 상한

이전 Gemma INC-119 transfer cohort와 INC-121 output-contract cohort를 제외한다. Luna INC-118
cohort는 다른 model의 prior evidence이므로 exclusion에 넣지 않는다. 남은 notices에서
metadata-only profile (`national`, `local_general`, `local_small`,
`local_negotiated`)별 SHA-256 rank 첫 8개를 선택해 32 notices를 고정한다. label은 cohort
선정과 prompt에 사용하지 않는다.

64 calls, $0.20, retry 포함 failure rate 2%가 상한이다. preflight는 source hashes, cohort
hash, message hashes, legal-summary char length을 기록하고 mock parse를 통과해야 한다.

## Gate

Compact summary arm이 paired control보다 macro positive-F1 `+0.02` 이상, micro recall 비감소,
absence items(v10/v11/v16/v18/v20) new FP 합계 +1 이하, valid record failure ≤2%일 때만
새로운 disjoint 32-notice holdout으로 간다. 어떤 gate라도 실패하면 full-law prompt를 더하거나
동일 cohort에서 rewording하지 않고 C branch를 종료한다.
