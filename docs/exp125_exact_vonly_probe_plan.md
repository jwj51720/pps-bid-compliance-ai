# EXP125 — Exact baseline V/E와 V-only 출력 계약 probe

## 질문

리더보드는 v 열만 채점한다. 동료의 public 0.32734 관측은 V-only가 유효할
가능성을 남긴다. 그러나 기존 V-only 결과는 복잡한 card/full-split/grouping 정책과
섞여 있어, 현행 exact organizer baseline에서 evidence 생성 부담만 제거했을 때의
효과를 분리하지 못했다.

## Arm과 변경 통제

| Arm | Config | 변경 |
| --- | --- | --- |
| A control | `config.exp125a-exact-baseline-ve-fast-panel.yaml` | 현행 exact organizer V/E 계약 |
| B treatment | `config.exp125b-exact-baseline-vonly-fast-panel.yaml` | `prompt.output_mode: labels_and_evidence → labels_only` 하나뿐 |

고정 요소는 4,000자 ordered context, `official_baseline_v1`, plain item list,
`official_lines` metadata, cards/RAG 없음, 16,384/1,536 token budget, Gemma model,
temperature 0, seed, schema transport, parsingㆍmerge, concurrency다. B는 evidence를
요청하거나 생성/파싱하지 않는다. 이는 label 품질 진단이며 evidence 없는 submission을
정당화하지 않는다.

## 실행 전 gate

1. `preflight_experiment.py`가 A에는 diff 없음, B에는 output mode 한 개만 보고한다.
2. 두 config 모두 mock 20/20, submission schema validation, tokenizer-admission을 통과한다.
3. `inspect_prompt.py`의 same-record request JSON은 messages와 response schema가
   V/E 계약 부분 외에는 동일함을 확인한다.

## 유료 실행과 판정

두 arm을 같은 frozen `dev_fast_panel_v1` 20건에서 새로 실행한다. remote provider
변동을 treatment 효과로 오인하지 않기 위해 historical result를 control로 쓰지 않는다.

통과 조건은 B가 A보다 Macro positive-F1 `+0.02` 이상이고, positive recall이
감소하지 않으며, parse failure가 0인 것이다. 또한 cell-level changed labels의
TP/FP/FN 변화를 기록한다. 하나라도 충족하지 못하면 V-only 문구 재작성, dev200,
evidence-recovery implementation을 진행하지 않는다. 통과 후보만 independent holdout
20건, 그 뒤 dev200으로 간다.
