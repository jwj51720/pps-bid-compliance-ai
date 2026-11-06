# EXP240/241 — joint v4+v5 specialist, V/E versus V-only

작성: 2026-09-14, dev / mac

## 진단과 목적

EXP221 v4-only와 EXP231 v5-only는 각자 fast, independent holdout, dev200에서 같은
개선 방향을 보였지만, 현재 최고 composition은 EXP208 219 + v4 200 + v5 200 = 619
calls다. 실제 evaluator에서 120분을 초과했으므로 제출 topology가 될 수 없다.

EXP239는 v5 숫자 card만 all-item 판정에 넣어도 v5가 전혀 움직이지 않음을 보였다.
따라서 v5 attention isolation은 유지해야 한다. 가장 작은 압축 후보는 이미 검증된 v4와
v5만 하나의 specialist로 결합하는 것이다.

사용자는 label 성능이 우선이며 V-only 반복도 허용했다. 그래서 같은 `[v4, v5]` 입력과
cards에서 output contract만 달리한 두 팔을 비교한다.

- EXP240: v4+v5 V/E.
- EXP241: v4+v5 V-only.

이는 과거 24개 전체 V-only 또는 full v-grouping을 반복하는 것이 아니다. 두 항목 모두
독립 specialist로 이미 일반화가 확인됐고, 이번 실험은 두 200-call request sets를 하나로
압축할 때의 간섭과 output 부담만 측정한다.

## 결합 card artifact

새 version은 v10을 기준으로 v4에는 검증된 v11 scope correction, v5에는 검증된 v12
numeric operand를 적용한다. v1-v3/v6-v24 text는 v10과 byte-equivalent여야 한다. raw law는
prompt에 넣지 않으며 새 threshold나 dev phrase를 추가하지 않는다.

## EXP240 V/E 통제 정책

- base config: `configs/config.exp219-v4-only-scope-fast-panel-c4.yaml`.
- allowed changes: `prompt.active_items`, `prompt.decision_cards_path`.
- active items: exactly `[v4, v5]`.
- profile `complete_fact_subset_v1`, mode `baseline`, V/E output, cards/metadata/product
  facts/organizer semantics, all admitted original source, tokenizer admission, merge,
  postprocess와 provider parameters는 고정한다.
- EXP205 frozen base에서 v4/e4와 v5/e5만 field replacement한다. OR/majority/Python
  label inference를 사용하지 않는다.

## EXP241 V-only 통제 정책

- base config: EXP240.
- sole allowed change: `prompt.output_mode: labels_and_evidence -> labels_only`.
- messages, active items, cards, source admission, provider/model/seed와 merge ownership은
  같다.
- label 비교 단계에서는 e4/e5가 blank인 것을 예상 limitation으로 기록한다. V-only label이
  이기지 못하면 별도 evidence 알고리즘을 만들지 않는다.
- V-only가 의미 있게 이길 때만 source-grounded evidence 복원 전략을 별도 실험으로 설계한다.
  Python은 label이나 법률 조건을 계산할 수 없으며, 허용되는 역할은 모델이 지목한 anchor의
  exact substring 검증 또는 source span 연결뿐이다. 양성인데 anchor가 없는 상태를 임의의
  키워드 법률 판단으로 메우지 않는다.

## 사전 검증

각 arm에 대해 다음을 유료 실행 전에 완료한다.

1. 결합 card structural diff와 preflight allowed changes.
2. exact dev200 source coverage/provenance, prompt budget, call topology.
3. short, attachment, overflow actual rendered message human review.
4. active v4/v5 semantic-input contract.
5. exact fast20 mock, parse/malformed recovery, 49-column output과 merge audit.
6. V/E와 V-only 간 input/system 차이가 의도한 output contract에만 한정되는지 확인한다.

## 평가와 승격

- 고정 fast20에서 EXP219 v4와 EXP229 v5의 separate specialist 결과를 target 기준으로 삼는다.
- joint arm은 두 item의 TP를 모두 유지하고, v4/v5 합성 macro가 유의하게 무너지지 않아야 한다.
- V-only와 V/E 중 label macro와 두 item TP/FP/FN이 우선이며 runtime/tokens를 함께 기록한다.
- 가장 좋은 arm만 policy-identical independent holdout으로 보낸다. 양 arm이 서로 다른
  precision/recall 장점을 보이면 두 arm을 post-hoc OR/majority하지 않는다.
- holdout 방향이 separate specialists 대비 유지될 때만 dev200으로 확장한다.
- joint specialist가 성공하면 예상 dev200 topology는 EXP208 219 + joint 200 = 419 calls다.
  이는 619보다 낫지만 438-call 제출도 timeout이었으므로 최종 제출 전 추가 압축이 필요하다.

## 사전 검증 결과

- 결합 v15 artifact는 v10 대비 v4와 v5 prompt text만 변경한다.
- EXP240 preflight는 EXP219 대비 active items와 card path만, EXP241은 EXP240 대비
  output mode만 보고했다.
- 두 arm 모두 exact dev200 admission에서 200/200 single-pass, 374/374 source
  documents, source/metadata/card/organizer-semantics omission 0, over-budget 0이었다.
- short `PPS-DEV-062`, attachment `PPS-DEV-194`, overflow `PPS-DEV-169` actual
  rendered messages를 읽었고 v4/v5 semantic contract 2/2가 모두 통과했다.
- V/E와 V-only의 user messages는 byte-identical했다. system diff는 evidence 지시와
  output JSON shape 제거뿐이었다.
- 양 arm exact fast20 mock과 v4/v5-only field replacement는 49-column validation과
  changed non-specialist cells 0을 통과했다. 전체 tests는 214 passed였다.

## Fast20 결과와 결정

| arm | calls | wall | completion tokens | v4 TP/FP/FN, F1 | v5 TP/FP/FN, F1 | merged macro |
|---|---:|---:|---:|---:|---:|---:|
| EXP240 joint V/E | 20 | 22.0s | 1,752 | `3/4/0`, `.600` | `0/0/1`, `0` | `.350000` |
| EXP241 joint V-only | 20 | 20.3s | 300 | `3/4/0`, `.600` | `0/1/1`, `0` | `.350000` |

- separate fast specialists EXP219(v4)와 EXP229(v5)는 각각 target F1 `.666667`이고,
  둘을 함께 합성하면 base `.325000`에서 약 `.380556`이다.
- 두 joint arm은 v4 recall은 유지했지만 v5 true positive를 모두 잃었다. V-only는 v5
  false positive까지 하나 추가했다.
- V-only는 completion을 82.9% 줄였지만 label macro를 개선하지 않았고, positive
  evidence를 전부 잃었다.
- 두 arm 모두 parse error 0이므로 실패 원인은 serialization이 아니라 두 항목 사이의
  attention interference다.

결정: 사전 gate인 v4와 v5 TP 동시 보존을 실패했으므로 EXP240/241 모두 holdout/dev200으로
확장하지 않는다. v4+v5 묶음으로 619 calls를 419 calls로 압축하는 경로는 기각한다.
V-only evidence 복원 알고리즘도 label gain이 없으므로 이 결과에서 만들지 않는다.
