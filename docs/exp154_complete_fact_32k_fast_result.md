# EXP154 — 32k complete-fact fast-20 결과

작성일: 2026-09-09 (dev / mac)

## 가설과 단일 변경

EXP152는 decision card v6, human-readable organizer metadata, friendly exact
competition-product fact, 모든 제공 공고 source를 사용했지만 `max_model_len: 16384`였다.
EXP154는 이 정책에서 **exact model admission만 16,384 → 32,768**로 변경했다. 따라서
4,000-character document cap은 쓰지 않으며, card·CSV·metadata·V/E schema·merge·frozen
v2/v3/v21 rule·Gemma/decoder는 EXP152와 같다.

## admission 검증

- `scripts/preflight_experiment.py`: declared one-field diff PASS.
- `scripts/audit_candidate_semantic_contract.py`: short `PPS-DEV-01`, attachment
  `PPS-DEV-03`, long/overflow `PPS-DEV-143`에서 24/24 PASS. label/prediction/provider를
  읽지 않았다.
- exact rendered input은
  `outputs/exp154-semantic-contract-audit-v1/rendered_inputs/`에 저장했다. card,
  readable metadata, friendly product fact, document header와 supplied source가 실제
  message에 있는지 사람이 확인했다.
- mock fast20 및 pipeline/config/card regression 62개 PASS.

Exact Gemma chat-template tokenizer로 dev-200을 profile한 결과 prompt budget은
31,232 tokens이고 193건 one-pass, 7건 overflow(2회 6건, 3회 1건), 총 208 calls다.
EXP152 16k의 123 one-pass/77 overflow/384 calls보다 source fragmentation이 크게 줄었다.

## fast-20 결과

| 정책 | macro positive-F1 | 실제 calls | runtime | total tokens |
| --- | ---: | ---: | ---: | ---: |
| EXP147 input-truthful 4k single | 0.291071 | 20 | 기록 참조 | 기록 참조 |
| EXP152 complete-fact 16k | 0.224306 | 34 | 80.614초 | 527,116 |
| **EXP154 complete-fact 32k** | **0.241667** | **22** | **40.5초** | **기록 참조** |

EXP154은 EXP152보다 +0.017361 개선됐고 calls/runtime을 크게 낮췄다. 그러나 EXP147보다
-0.049405이므로 holdout/dev200/submission으로 확대하지 않는다. parse error는 없었다.
evidence validity는 23건 중 0.8261, span F1은 0.5833이었다.

## 해석

fast20에서 20건 중 18건은 full source를 one pass에 담았고 나머지 2건도 2 pack으로 모든
source를 보존했다. 그런데 v4/v6–v11/v14/v16–v18/v20/v24 positive FN이 여전히 넓게
분포했고, v13/v15/v19/v23에는 FP도 생겼다. 즉 이 결과의 주된 실패는 4k 앞부분에
문서가 빠져서가 아니라, complete source를 카드와 함께 읽은 Gemma가 24개 legal
conditions를 한 번에 안정적으로 적용하지 못한 데 있다.

따라서 다음 단계에서 4k front-cut을 complete-input policy로 되돌리지 않는다. 모든
사실을 접근 가능하게 만든 EXP154를 source-complete control로 유지하고, 그 위에서
final legal judgment의 항목 부담을 어떻게 분리할지 탐색한다. 단, EXP153처럼 한 pack에서
24개 item-specific excerpt를 요구해 source coverage가 15.8%로 떨어진 형태는 재시도하지
않는다.
