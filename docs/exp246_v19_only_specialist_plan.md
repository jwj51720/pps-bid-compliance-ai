# EXP246 — v19-only supply-assurance timing specialist

작성: 2026-09-14, dev / mac

## 진단과 가설

EXP208 dev200의 v19는 6개 양성을 모두 찾았지만 false positive 9건이 남아 TP/FP/FN
`6/9/0`, F1 `.571429`다. v19 truth condition은 물품공급·기술지원 확약서를 계약 후가 아니라
입찰서/제안서 제출 단계의 참가자격 또는 필수 제출서류로 요구하는지다. all-item relation
checklist에도 시점 확인은 있으므로 새 schema나 card 없이 표현 가능하다.

가설은 v19 하나만 card, 필요한 metadata와 모든 original source와 함께 판단하게 하면 Gemma가
`입찰 시 제출`과 `낙찰·계약 후 제출`을 더 정확히 구분해 recall 1.0을 유지하면서 FP를 줄인다는
것이다. model이 v19/e19를 모두 소유하고 Python은 source substring validation과 frozen-base
field replacement만 수행한다.

## 통제 정책과 gate

- base: `configs/config.exp205-relation-checklist-after-source-fast-panel-c4.yaml`.
- allowed changes: `prompt.active_items`, `prompt.profile`, `prompt.mode`.
- 기존 v19 card, V/E schema, human-readable metadata, organizer semantics, all admitted original
  source, tokenizer budget, provider/model parameters와 postprocess를 유지한다.
- preflight, exact dev200 admission, short/attachment/overflow rendered review, active-v19 semantic
  contract, exact mock, evidence/49-column merge validation과 tests를 paid call 전에 완료한다.

fast20에서 EXP205 v19 TP/FP/FN `0/2/1`보다 F1이 개선되고 evidence가 유효해야 holdout으로
간다. holdout도 같은 방향일 때만 dev200으로 확장한다. 실패하면 v19 문구나 schema를 같은
실험에서 조정하지 않는다.

## Fast20 결과와 중단 결정

- preflight는 선언된 세 subset serialization change만 확인했다.
- exact dev200 admission은 200×1 calls, 374/374 documents, omission/over-budget 0이었다.
- 대표 rendered review, mock 49-column validation과 217 tests가 통과했다.
- provider call은 20 calls, 21.4초, parse error 0이었다.
- v19 TP/FP/FN은 EXP205 `0/2/1`에서 EXP246 `0/3/1`로 악화됐고 merged macro는
  `.325000`으로 동일했다. specialist의 세 positive evidence는 source substring으로는 모두
  유효했지만 `확약서 <서식 2>`, `확약서 서식 6`, 일반 `물품 공급 및 기술지원 확약서`
  목록처럼 입찰참가 단계의 해당 확약서임을 완결하지 못한 문구였다.

따라서 v19 손실도 V/E 출력량이나 all-item attention만의 문제가 아니다. 카드에 이미
확약서 종류와 제출시점 조건이 있으나 Gemma가 단어 존재를 관계 충족으로 잘못 올린다.
holdout/dev200으로 승격하지 않으며 단순 item-only specialist를 다른 항목에 기계적으로
반복하지 않는다.
