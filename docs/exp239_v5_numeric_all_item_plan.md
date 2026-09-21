# EXP239 — v5 numeric card in the all-item relation policy

작성: 2026-09-14, dev / mac

## 문제와 가설

EXP231은 v5-only attention과 v5 숫자 operand 완결을 함께 사용해 dev200 v5를
TP/FP/FN `1/1/6 -> 7/4/0`, F1 `0.222222 -> 0.777778`로 개선했다. 그러나 현재
최고 composition은 EXP208 219 calls + v4 specialist 200 calls + v5 specialist 200
calls로 총 619 calls라 evaluator runtime에 적합하지 않다.

EXP239는 v5 개선 중 숫자 operand 완결 효과가 all-item relation-checklist generation
안에서도 유지되는지 분리한다. 유지된다면 v5 specialist 200 calls를 없애고, EXP208과
같은 one-stage topology에서 v5를 개선할 수 있다.

## 통제 정책

- base: `configs/config.exp205-relation-checklist-after-source-fast-panel-c4.yaml`.
- candidate: `configs/config.exp239-v5-numeric-all-item-fast-panel-c4.yaml`.
- 유일한 허용 policy change: `prompt.decision_cards_path`.
- v12 card artifact는 v10 대비 v5 prompt text만 다르고 v1-v4/v6-v24는 동일하다.
- all 24 active items, `relation_checklist_after_source_v1`, V/E output, corrected
  human-readable metadata, conditional exact-code product facts, organizer semantics,
  all admitted original source, overflow merge, frozen postprocess와 provider parameters는
  고정한다.
- Python 수치 비교, label override, specialist merge 또는 추가 호출은 사용하지 않는다.

## 사전 검증

유료 실행 전에 다음을 모두 완료한다.

1. card structural diff가 v5 하나만 변경했음을 확인한다.
2. preflight가 선언된 card path 차이 하나만 보고하는지 확인한다.
3. exact tokenizer dev200 admission에서 374/374 source documents, metadata/cards,
   organizer semantics, product configuration과 budget을 감사한다.
4. short `PPS-DEV-062`, attachment `PPS-DEV-194`, overflow `PPS-DEV-169`의 actual
   rendered messages를 읽고 24/24 semantic-input contract를 확인한다.
5. exact fast20 mock에서 49 columns, IDs, parse와 evidence validation을 확인한다.

## 승격 및 중단 조건

- fast20은 `configs/dev_fast_panel_v1.json`만 사용한다.
- EXP205 대비 v5 F1/TP와 전체 macro/TP가 개선되어야 independent holdout으로 간다.
- 동일 정책의 holdout 방향이 일치할 때만 dev200으로 확장한다.
- 실패하면 all-item v5 card wording을 dev 사례에 맞춰 반복 수정하지 않는다. 이 경우
  v5-only attention isolation이 필요한 것으로 기록하고 v4+v5 최소 specialist 통합으로
  이동한다.
- 성공하더라도 EXP231 specialist 결과와 동일하다고 주장하지 않고, 실제 fast/holdout/dev200
  TP/FP/FN으로 별도 평가한다.

## 사전 검증 및 fast20 결과

- v12와 v10의 structural diff는 v5 prompt text 하나뿐이었다.
- preflight는 선언된 `prompt.decision_cards_path` 하나만 보고했다.
- exact tokenizer dev200 admission은 200 records, 374/374 source documents,
  source/metadata/card/organizer-semantics omission 0, over-budget 0이었다. topology는
  `183x1 + 14x2 + 3x3 = 220` source-pack messages다.
- short `PPS-DEV-062`, attachment `PPS-DEV-194`, overflow `PPS-DEV-169`의 actual
  rendered messages를 읽었고 세 fixture 모두 24/24 semantic-input contract를 통과했다.
- exact fast20 mock은 20/20, 49 columns/ID/evidence validation을 통과했고 전체 tests는
  214 passed였다.
- 실제 fast20은 24 calls, 62.0 seconds, prompt/completion `380,611/14,106`, parse
  error 0, finish reason 전부 stop이었다.
- EXP205 `0.325000` -> EXP239 `0.304167`, delta `-0.020833`.
- 목표 v5는 양쪽 모두 TP/FP/FN `0/0/1`로 changed 0이다. 숫자 card가 all-item
  generation 안에서는 목표 판정을 전혀 움직이지 못했다.
- 비표적 항목은 6개가 변해 corrected 3 / regressed 3이었고 macro는 하락했다.

결정: fast gate 실패로 holdout/dev200을 실행하지 않는다. v5 숫자 operand만 all-item
base에 흡수해 v5 specialist를 제거하는 경로는 기각한다. EXP231의 개선에는 v5-only
attention isolation이 필요하다는 증거이며, 다음은 v4+v5 최소 specialist 통합에서 V/E와
V-only를 통제 비교한다.
