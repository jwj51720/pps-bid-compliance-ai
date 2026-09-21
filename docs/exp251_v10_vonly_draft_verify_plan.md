# EXP251 — v10 structured V-only draft and independent V-only final owner

작성: 2026-09-15, dev / mac

## 가설

EXP247/248/249는 full organizer catalog와 v10 관계형 review로 기존 zero recall을 회복했지만,
dev200에서 `TP 4 / FP 66 / FN 3`이었다. fast에서도 다섯 FP 중 일부는 후보 제품을 null로
쓰면서 경쟁제품 적용을 `적용`으로 쓰는 내부 모순이었다. EXP250에서 catalog를 제거하면
fast positives가 모두 사라졌으므로 정보 축소는 해법이 아니다.

가장 작은 다음 가설은 동일한 complete input을 읽은 첫 구조화 V-only 판정을 명시적으로
untrusted draft로 제공하고, 두 번째 Gemma가 같은 card, full catalog, metadata와 모든 admitted
원문을 다시 읽어 구조화 review와 final v10을 독립적으로 다시 소유하면, recall을 유지하면서
과잉 positive를 줄일 수 있다는 것이다.

이는 EXP187의 24-item 다중 draft/consensus를 반복하지 않는다. dev200에서 실제 실패가 확인된
v10 하나만 대상으로 하며, majority/OR/AND나 Python label inference가 없다. v10은 e10이 항상
blank인 absence item이므로 두 단계 모두 V-only여도 평가 출력 의미가 손실되지 않는다.

## Base와 허용 변경

- base: `configs/config.exp247-v10-product-presence-review-fast-panel-c4.yaml`.
- sole allowed change: `staged_run` section과 `staged_run.mode`.
- stage A: EXP247과 byte-equivalent한 v10 structured V-only input/output.
- stage B: 같은 complete input에 stage A의 v10 label만 “공고 자료가 아닌 임시 판단”으로
  덧붙인다. A의 label을 따르지 말고 full source와 structured review를 다시 수행한다.
- final label은 전적으로 stage B가 소유한다. B malformed 때 A 전체 결과를 transport recovery로
  쓰는 기존 shared-pipeline contract 외에는 label merge가 없다.
- cards, full catalog, exact-code fact, metadata, organizer semantics, source admission,
  `v10_product_presence_review_v1` schema, provider parameters와 postprocess는 고정한다.

## Paid-run 전 gate

1. preflight가 staged-run 추가만 검출해야 한다.
2. exact tokenizer admission으로 stage A/B 모두 source omission 0, fixed-input completeness,
   pass topology와 token budget을 기록한다.
3. short `PPS-DEV-062`, attachment `PPS-DEV-194`, overflow/long `PPS-DEV-169`의 실제 A/B
   rendered messages를 읽고 B에도 full source와 catalog가 남는지 확인한다.
4. active v10 semantic-input contract를 A/B final rendered input에서 확인한다.
5. exact mock에서 stage provenance, malformed recovery, 49 columns/unique IDs/evidence validation을
   확인한다.

## 승격·중단 기준

- fast20에서 EXP247 `TP 2 / FP 5 / FN 0`, F1 `.444444`보다 precision 또는 F1이 개선되고
  두 TP를 모두 유지해야 independent holdout으로 간다.
- 단순 재표본 변동으로 positive 수만 줄고 TP도 잃으면 실패다.
- holdout에서 EXP248 `TP 1 / FP 5 / FN 0`, F1 `.285714`보다 방향이 개선되거나 최소한 recall을
  유지하며 FP가 감소해야 dev200으로 간다.
- dev200까지 통과해도 약 2× full-catalog calls이므로 local quality 증거와 submission runtime
  승격은 별도로 판단한다.

## Pre-provider gate — 2026-09-15

- 기존 shared staged runner는 `vonly_draft_full_final_v1`의 final을 V/E로만 제한했다. v10은
  e10이 규칙상 항상 blank이고 EXP247 schema가 V-only이므로, 이 mode에서 labels-only final
  owner도 허용하도록 config validation을 최소 확장했다. pipeline의 draft/final execution이나
  merge는 바꾸지 않았고 V-only final-owner regression test를 추가했다.
- preflight는 EXP247 대비 선언된 `staged_run` section과
  `staged_run.mode=vonly_draft_full_final_v1`만 검출했다.
- exact Gemma tokenizer dev200 projection은 stage A 252 calls, stage B 255 calls, 합계 507
  calls다. A/B source-document omission은 각각 0이고, B pass 분포는 163×1 + 19×2 + 18×3다.
  batch 128은 각각 2 batch rounds이나 call 수를 줄이지 않는다.
- short `PPS-DEV-062`, attachment `PPS-DEV-194`, long/overflow `PPS-DEV-169`의 rendered A/B를
  `outputs/exp251-preflight/`에서 읽었다. B에는 full catalog, card, metadata, organizer semantics,
  모든 admitted source, 원문 뒤 structured review와 “초안을 따르지 말고 독립 재심사” 지시가
  모두 남는다. 169는 A/B 각각 3 source packs이며 source omission 0이다.
- active-v10 semantic-input audit는 세 fixture 모두 통과했다.
- exact mock은 20/20, short/attachment A/B 1+1 pass, 169 A/B 3+3 passes, parse error 0,
  final recovery false, 49 columns/unique IDs/evidence validation PASS다.
- targeted config/pipeline tests는 112 passed다.

가설의 두 독립 V-only reads와 model-owned final, complete input, source provenance가 모두
구현·선택됐음을 확인했다. EXP251 fast20 provider run을 승인한다.

## EXP251 fast20 결과

- 20 notices에서 stage A/B 합계 48 source-pack calls, 63.0초, prompt/completion
  `1,143,260/8,240` tokens, parse error 0, final recovery 0이었다.
- EXP247 v10 `TP 2 / FP 5 / FN 0`, F1 `.444444`에서 EXP251은
  `TP 2 / FP 4 / FN 0`, precision `.333333`, recall 1.0, F1 `.500000`으로 개선됐다.
- 두 gold positive를 모두 유지했고, stage A가 positive였던 `PPS-DEV-036`을 stage B가 0으로
  재판정해 FP 하나를 제거했다. Python은 이 변경에 관여하지 않았다.
- fast 승격 gate를 통과했지만 한 FP 차이이므로 일반화 증거는 아니다. policy-identical
  EXP252 independent holdout20에서 TP 유지와 FP 감소가 재현되는지 확인한다.

## EXP252 independent holdout20 결과

- preflight는 EXP251 대비 effective policy difference 0이었다. holdout의 short positive
  `PPS-DEV-068`, 2-pack attachment `PPS-DEV-27`, 3-pack overflow `PPS-DEV-082`의 A/B rendered
  contract와 exact mock 20/20, parse/recovery/evidence/49-column validation이 통과했다.
- provider run은 20 notices, A 25 + B 26 = 51 source-pack calls, 54.1초, prompt/completion
  `1,084,738/7,334` tokens, parse error 0, final recovery 0이었다.
- EXP248 one-stage v10 `TP 1 / FP 5 / FN 0`, F1 `.285714`에서 EXP252는
  `TP 1 / FP 8 / FN 0`, precision `.111111`, recall 1.0, F1 `.200000`으로 악화했다.
- stage B는 FP 하나를 제거했지만 stage A가 0이던 세 notice를 새 positive로 바꾸는 등 전체
  precision을 안정시키지 못했다.

결정: predeclared independent holdout gate를 실패했으므로 dev200으로 확장하지 않는다.
같은 complete input을 반복해서 읽히는 V-only verification은 fast 한 표본에서는 개선됐지만
일반화된 precision lever가 아니다. draft wording, pass 수, majority/AND를 반복 조정하지 않는다.
