# 실험 변경 통제 및 2026-09-03 감사 기록

## 결론

현재 canonical 제출 정책은 여전히 `config.yaml`의 `labels_and_evidence`다. 카드 v2,
경쟁제품 exact-code 문맥, full-split merge는 canonical에 남아 있으나, 4-v-group은
runtime 위험 ablation이며 canonical이 아니다. 법령 RAG bundle도 실험 artifact이며
canonical input에 선택되지 않는다.

이번 감사에서 config 79개와 그 artifact path를 읽어 검증했다. 실행 가능한 config의
입력·항목표·카드·제품 index·reference path는 존재한다. decision card v1~v4는 모두
24개 v와 item-table SHA를 보존한다. RAG mapping은
`docs/legal_reference_mapping.md`, bundle provenance/coverage는 derived manifest에
분리되어 있고, config의 `reference_bundle_dir`/`reference_routing`으로만 선택된다.

## 발견 및 조치

| 문제 | 영향 | 조치 |
|---|---|---|
| EXP067~070의 sparse serializer가 VE를 anchor 계약으로 바꾸고 부재검토로 라벨을 덮어씀 | “출력만 변경” 비교가 아님 | config를 `lifecycle: invalidated`로 표시하고 loader가 재실행을 거부 |
| `labels_and_sparse_anchor` 명칭이 실제 역할과 다름 | anchor와 evidence 실험 혼동 | 유효 모드를 `labels_and_sparse_evidence`로 명명 |
| EXP044의 4-group 실행 인자가 config 밖 CLI에 있었음 | 같은 config를 재실행해도 호출 구조가 달라질 수 있었음 | `grouped_run`을 EXP044 config에 기록; runner는 config 값을 기본 사용 |
| baseline 대비 변경 범위가 prose에만 있었음 | 의도하지 않은 prompt·merge·RAG 변경을 놓칠 수 있었음 | `scripts/preflight_experiment.py`와 `base_config`/`allowed_policy_changes` 도입 |

EXP071/072는 수정된 sparse-evidence contract로 수행한 fast20 진단이다. 각각 EXP014 및
EXP044의 effective policy에서 `prompt.output_mode`만 바꾸도록 preflight 대상이다.
점수는 EXP071 0.10625, EXP072 0.14792로 기존 VE fast-panel 비교보다 낮았으므로 제출
후보가 아니다. EXP071/072의 output artifact에는 당시 실행된 config/source hash가 남아 있다.

## 앞으로의 필수 절차

1. 가설을 한 문장으로 적고 base config와 허용 policy 차이를 config에 기록한다.
2. `preflight_experiment.py`가 선언하지 않은 차이를 0개로 확인한다.
3. 동일 config의 mock 실행으로 parser, prompt, tokenizer admission, output path를 확인한다.
4. 유료 fast panel 실행 후 macro F1뿐 아니라 label별 precision/recall/F1, malformed count,
   token/call/runtime을 기록한다.
5. canonical 또는 제출 변경은 dev-200과 staged submission mock을 통과한 경우만 한다.

RAG 변경은 reference selector/mapping/bundle manifest/config path의 네 요소가 모두
버전 고정돼야 한다. card 변경은 새 `decision_cards_vN.json`을 만들고 item-table SHA와
공식 출처를 남긴다. prompt 표현, output schema, merge, RAG, card를 하나의 실험에서
동시에 바꾸지 않는다.
