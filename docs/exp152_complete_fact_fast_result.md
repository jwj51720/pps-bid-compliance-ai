# EXP152 — complete-fact adaptive context fast-20 결과

작성일: 2026-09-09 (dev / mac)

## 가설

법령 원문은 넣지 않고 card v6로만 판단 기준을 제공하되, 실제 판정에 필요한
organizer metadata, exact competition-product CSV의 friendly fact, 그리고 record에
실제로 제공된 모든 notice document를 누락 없이 보여주면 4k single보다 정확해질
것이라는 가설이다.

`single` context는 exact Gemma tokenizer admission을 사용한다. full notice가
14,848 prompt-token budget에 맞으면 한 call이고, 넘을 때만 source order를 유지하는
ordered packs를 만든다. non-absence는 OR, absence v10/v11/v16/v18/v20은 모든 pack이
absence일 때만 1인 AND다. EXP123의 source-complete v2/v3/v21 frozen replacement는
그대로 마지막에 적용한다.

## 사전 admission 증거

- controlled diff: 4k cap 제거, exact-token overflow, human-readable metadata,
  product CSV friendly fact, absence AND, complete-fact prompt profile.
- `scripts/preflight_experiment.py`: declared diff만 확인.
- mock 20건, parser/evidence validation, 59 regression tests 통과.
- `scripts/audit_candidate_semantic_contract.py`: short/attachment/long fixture에서
  active v 24/24의 card, required metadata, product fact, actual supplied document
  coverage가 final message에 있음을 확인. 결과:
  `outputs/exp152-semantic-contract-audit-v1/semantic_contract_audit.md`.
- full dev-200 exact tokenizer profile: one-pass 123, overflow 77, total 384 calls,
  1.92 calls/notice, maximum 6 packs. 결과:
  `outputs/exp152-token-admission-dev200-v1.json`.

## fast-20 결과

| 정책 | Macro positive-F1 | Δ vs EXP147 |
| --- | ---: | ---: |
| EXP147 input-truthful 4k single V/E | 0.291071 | — |
| **EXP152 complete-fact adaptive** | **0.224306** | **-0.066766** |

- runtime: 80.614 seconds
- remote token usage: prompt 498,451 / completion 28,665 / total 527,116
- pass-count distribution: 1 pass 12 notices, 2 pass 2, 3 pass 2, 5 pass 3,
  6 pass 1
- parse errors: 0
- submission validation: passed; evidence warnings 3

## 해석

이 결과는 “필요 사실을 생략해도 된다”는 결론이 아니다. 오히려 complete input
contract를 실제로 충족한 뒤에도 Gemma가 긴 pack·다수 card·제품 분류를 동시에
처리할 때 explicit positive를 더 보수적으로 0으로 낸다는 관측이다.

대표 변화는 v4 recall `0.333 → 0`, v15 recall `1.0 → 0`이며, v1/v2/v3/v21은
같은 fast panel에서 유지됐다. v12는 F1 `0.4 → 0.667`으로 개선됐지만 전체 하락을
상쇄하지 못했다. parser failure나 Python merge exception은 없었으므로 현 결과를
format failure로 설명할 수 없다.

EXP152는 fast-20에서 control보다 낮으므로 holdout/dev-200/submission으로 확대하지
않는다. 그러나 complete-fact input coverage와 exact token/call distribution은 이후
two-stage candidate가 반드시 재사용할 admission basis로 보존한다. 다음 탐색은 이
정보를 다시 버리는 것이 아니라, full source reading과 final 24-item decision burden을
한 call에 과적재하지 않는 information-preserving two-stage structure여야 한다.
