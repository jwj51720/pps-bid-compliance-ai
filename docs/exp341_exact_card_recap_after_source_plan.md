# EXP341 — exact decision-card recap after full source

작성: 2026-09-18, dev / mac

## 진단 근거

v30/v31에서 모든 기준과 실제 입력은 전달되지만 all-24 generation은 대부분의 positive item을
0으로 만든다. v31의 sole v4 card 변경은 fast에서 v4를 회복시켰지만 unrelated v2/v3/v22도
움직였고, holdout에서는 v4 회복이 사라졌다. 반면 동일한 금액 비의존 v4 기준을 단독으로 묻는
EXP219/220/221은 fast/holdout/dev200에서 v4 positive를 모두 회복했다. 이는 card/source 부재보다
24-item attention과 긴 source 뒤의 card recency가 병목이라는 직접 증거다.

기존 EXP205/211은 원문 뒤에 generic relation checklist/decision protocol을 붙였고 holdout에서
일반화되지 않았다. EXP341은 새로운 법률 요약이나 generic 절차가 아니라, system에 이미 있는
**v1–v24 exact card catalog 자체**를 원문 뒤에 byte-identical하게 한 번 재제시한다. 각 v의
적용범위·1 조건·0 조건·예외를 판정 직전에 다시 보게 하되, 정보나 label owner는 바꾸지 않는다.

## 변경 통제

- base: EXP339 / v31 one-stage V/E.
- sole allowed change: `prompt.mode: baseline -> exact_card_recap_after_source_v1`.
- system의 기존 전체 card catalog를 유지한다. user message의 모든 admitted 원문 뒤에 같은 catalog를
  `[판정 직전 exact 카드 재대조]`로 한 번 추가한다.
- v31 cards, metadata/product facts, organizer semantics, source order/coverage, V/E schema,
  source-pack merge, evidence validator, provider parameters, Python labels는 고정한다.
- 새 호출, stage, item grouping, RAG, 법령 원문, Python rule은 없다.

## 위험과 gate

카드 반복은 source당 fixed tokens를 늘려 overflow context 수를 증가시킬 수 있다. 유료 전
dev200 exact tokenizer profile로 call count와 374-document coverage를 기록한다. source omission,
over-budget, context별 card/metadata/product 누락이 하나라도 있으면 실행하지 않는다.

1. preflight가 `prompt.mode`만 검출.
2. short/attachment/overflow 실제 rendered message에서 original card catalog → metadata/product →
   source → exact card recap → output 순서를 사람이 확인.
3. 모든 final context의 v1–v24 semantic contract PASS.
4. mock 20 rows, 49 columns, evidence validation PASS.
5. fast20에서 EXP339 `.122917`보다 macro/TP가 개선되고 zero-TP item 수가 줄어야 holdout으로 간다.
6. independent holdout에서 EXP340 `.166667`보다 같은 방향일 때만 dev200.
7. call 증가가 submission 120분 위험을 키우므로 quality가 커도 runtime 후보 여부를 별도로 판정.

generic checklist wording, 카드 순서, 반복 횟수는 같은 panel에서 추가 튜닝하지 않는다.

## 결과

### 사전 검증

- preflight는 `prompt.mode` 하나만 검출했다.
- dev200 exact admission은 EXP339의 243 contexts에서 **357 contexts**로 증가했다:
  `130×1 + 13×2 + 32×3 + 20×4 + 5×5`. supplied documents 374, omission 0.
- fast20은 39 contexts(`12×1 + 2×2 + 2×3 + 3×4 + 1×5`)로 증가했다.
- actual-value delivery 200/200 및 357/357 PASS. exact semantic audit는 062/194/143/049/046
  모두 24/24 PASS했고, overflow 143은 4 contexts 각각에서 source 뒤 exact recap이 확인됐다.
- mock 20 rows, validation PASS.

### Fast20 EXP341

- macro `.083333`, EXP339 `.122917` 대비 `-.039583`.
- v4는 EXP339와 같은 `TP/FP/FN=2/0/1`, F1 `.8`로 추가 이득이 없다.
- v1은 `1.0→0`, v2 `.4→.4`, v3 `.75→.8`; 나머지 positive family의 all-zero 문제를
  해소하지 못했다.
- runtime **387.4s**, prompt/completion `1,102,866/25,441`. EXP339 93.2s보다 약 4.2배
  느리고 prompt tokens도 약 2.1배다. 긴 overflow 한 건은 228.9s가 걸렸다.
- parse/validation warning은 0, evidence validity 1.0이므로 실패 원인은 malformed나 evidence
  gate가 아니라 label recall과 context multiplication이다.

## 결정

fast 품질과 runtime gate를 모두 크게 실패했다. holdout/dev200을 실행하지 않는다. exact card를
반복하거나 위치·반복 횟수를 튜닝하지 않는다. 모든 기준을 마지막에 재제시해도 all-item recall은
회복되지 않았으므로 단순 recency가 핵심 원인이 아니다. fixed-context 증가로 source가 더 많은
pack으로 나뉘는 비용이 오히려 submission runtime을 악화한다.
