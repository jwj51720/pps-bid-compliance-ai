# 공식 조건 요약 실험 계획

> **Superseded by the card-only knowledge policy (2026-09-04).** This document preserves EXP098/099 as historical diagnostics only. Future work must not inject this artifact, any raw law text, or any standalone law-summary reference into model prompts. Organizer-law review is instead incorporated into versioned decision cards.

## 문제 정의

최근 dev-200 실패 분석에서 두 종류의 오류를 분리했다.

1. **기준 부재형**: 공고문과 metadata에 사실은 있으나, 고시금액·기간·최소지분·제품 분류·법정 예외처럼 비교할 공식 기준이 prompt에 없어 Gemma가 `불확실하면 0`으로 멈춘다.
2. **해석 실패형**: 비교 기준과 공고 문구는 이미 있는데, Gemma가 문구의 시간·범위·강제성을 잘못 읽는다.

첫 번째는 원문 법령 RAG가 아니라, organizer 제공 법령에서 검증한 **짧은 공식 조건 요약**으로만 보완한다. 법령 전문은 context를 잠식했고 과거 성능도 개선하지 못했으므로 이 실험에서 사용하지 않는다.

## 실험 순서와 변경 통제

| 단계 | 가설 | 바꾸는 것 | 바꾸지 않는 것 | 승격 기준 |
| --- | --- | --- | --- | --- |
| 1. EXP098 | 공식 조건을 읽기 쉬운 짧은 기준으로 주면 기준 부재형 FN이 줄어든다. | `official_conditions_v2` fixed reference만 추가 | 문서 전략, 출력 schema, 카드, 제품 lookup, merge, LLM | mock 후 fast panel에서 기준선보다 개선; 이후 dev-200 |
| 2. 후속 | 제품 분류 사실을 필요한 모든 v10~v18에 제공하면 일반/경쟁제품 판단 결손이 줄어든다. | competition-product friendly context의 적용 범위만 수정 | 단계 1의 나머지 정책 | 단계 1 dev-200 통과 뒤 독립 ablation |
| 3. 후속 | 해석형 카드의 대조 절차가 FP/FN을 줄인다. | v3/v9/v19/v22/v24 카드와 비교 입력만 수정 | 법령 요약·문서 전략·제품 lookup | 항목별 TP/FP/FN 개선 |
| 4. 후속 | 부재탐지의 적용성/문구부재 상태 분리가 FN을 줄인다. | v10/v11/v16/v18/v20 최소 상태 출력과 merge | 다른 v 출력/merge | 단일 항목 probe 후에만 확대 |

한 실험에는 위 단계 중 하나만 넣는다. fast panel은 후보 순위용이며, canonical 또는 submission 정책 승격에는 dev-200 재검증이 필요하다.

## `official_conditions_v2` 계약

- 모델에는 적용 전제·정량 기준·중요 예외만 짧은 한국어로 제공한다.
- source 파일명, selector, routing key, hash는 모델 prompt가 아니라 manifest에만 보존한다.
- 각 문장은 `data/derived/legal_condition_ledger_v1.json`의 organizer-law source chunk에 연결한다.
- 이 요약만으로 1을 결정하지 않는다. 1은 여전히 공고 자료 원문과 metadata의 사실이 해당 조건을 충족할 때만 가능하다.
- 제품의 경쟁제품 여부는 법령 요약으로 추정하지 않는다. organizer CSV exact-code fact를 쓰는 별도 단계에서만 보완한다.
- v24는 법령 요약 대상이 아니며, 이 단계에서 변경하지 않는다.

## 범위

첫 artifact는 실패 분석에서 기준 부재가 확인된 `v2`, `v5`~`v7`, `v10`~`v18`, `v20`, `v21`, `v23`만 포함한다. 해석 실패형 v3/v9/v19/v22/v24의 card 보정이나 제품 context 확장은 의도적으로 포함하지 않는다.

## 검증

1. 생성 script가 모든 rule의 source coverage와 artifact hash를 manifest에 쓴다.
2. exact Gemma tokenizer로 fixed reference 포함 prompt admission을 확인한다.
3. `scripts/preflight_experiment.py`가 EXP051 대비 `prompt.reference_path`만 변경했음을 확인한다.
4. 동일 config mock을 먼저 실행한다.
5. paid fast panel 뒤 항목별 TP/FP/FN과 token/call 수를 기준선과 비교한다.

## EXP098 fast-panel 결과 (2026-09-04)

> **정정 (2026-09-04):** EXP098/099는 decision card를 의도적으로 넣지 않은 EXP051 vanilla baseline에 official-condition reference만 추가한 진단이다. 따라서 이 결과는 **카드 + 공식 조건** 전략의 성능이 아니며 canonical 후보 또는 그 직접 비교로 해석하면 안 된다. 판단 카드는 법령 해석을 모델에 전달하는 핵심 정책이므로, 후속 검증은 반드시 동일 card-only baseline과 `card + official conditions`를 대조해야 한다.

`configs/config.exp098-official-conditions-v2-fast-panel.yaml`은 EXP051의 4,000자 단일 호출·Markdown v2·VE 출력과 decoding 값을 유지하고, `prompt.reference_path`만 `official_conditions_v2.txt`로 바꿨다. `scripts/preflight_experiment.py`는 이 한 정책 차이만 보고했다.

| 조건 | Macro positive F1 | 비고 |
| --- | ---: | --- |
| EXP051 기준선의 동일 fast panel 재평가 | 0.125926 | 기존 dev-200 prediction에서 고정 panel만 재채점 |
| EXP098 official conditions v2 | 0.155556 | 20 calls, 51.3초 |

모델 입력용 요약은 16개 항목, 1,943자다. 같은 config mock에서 dump한 실제 최종 메시지를 Gemma tokenizer chat template으로 다시 세어 20건의 최대 입력은 6,994 tokens였고 30,268-token prompt budget을 넘지 않았다.

항목별 즉시 변화는 v2 `0→0.400` (TP 1), v12 `0→1.000` (TP 1), v19 `0→0.667` (TP 1), v21 `0.333→0.500` (TP 1)이다. 반면 v13은 TP 1·FP 7에서 TP 0·FP 3으로, v17은 FP 1, v23은 FP 2가 생겼고 v1·v22도 악화됐다. 따라서 이는 **후보 방향 신호일 뿐**이며 dev-200 또는 canonical/submission 정책으로 승격하지 않는다.

다음 판단은 v별 positive/negative 원문을 확인해 v2 rules 중 실제로 도움이 된 조건과 v13/v17/v23의 새 FP를 분리한 뒤 내린다. 제품 CSV 적용 범위 확대, 카드 수정, 부재탐지 merge 변경은 이 EXP098에 포함하지 않았다.

### EXP098 공고별 변화 감사

EXP051과 EXP098의 동일 20개 prediction을 직접 대조했다. 이 감사는 rule의 개별 인과효과를 확정하지는 못하지만, 다음 실험에서 유지·삭제·보완해야 할 문장을 식별한다.

| 항목·공고 | 변화 | 원문 대조 결론 |
| --- | --- | --- |
| v2 / PPS-DEV-062 | FN→TP | 지방 협상계약, 추정가격 약 2.27억원, ‘단일 건 3억원 이상’ 수행실적 요구를 새로 잡았다. 실적제한과 금액·계약법을 연결한 방향 신호다. |
| v2 / PPS-DEV-051 | TN→FP | 약 2.45억원 물품 공고의 ‘대학병원 납품실적 3억원’ 문구를 1로 냈다. 현재 요약은 **고시금액의 실제 수치**를 주지 않아 ‘실적 문구=위반’ 오독을 막지 못한다. |
| v12 / PPS-DEV-049 | FN→TP | ‘직접생산확인증명서 보유’라는 실제 참가자격 문구를 잡았다. 다만 이 공고에는 세부품명 코드가 없어, product-context 변경의 효과로 귀속하면 안 된다. |
| v13 / PPS-DEV-069 | TP→FN | 기존의 소기업·소상공인 제한 TP를 잃었다. 동시에 기존 FP 4개도 0으로 바뀌었다. v13 공식 조건은 정밀도는 높였으나 code fact 없이 recall을 잃었고, 이 단계에서 승격할 수 없다. |
| v21 / PPS-DEV-072, PPS-DEV-141 | FP→TN 2건 | ‘공동계약 불허’와 지방 공동이행의 ‘최소참여지분 5%’를 위반으로 오인하던 기존 FP를 제거했다. 최소지분 기준 보충은 유효한 방향 신호다. |
| v17 / PPS-DEV-26 | TN→FP | 1,818만원 용역의 적법한 소기업·소상공인 제한을 1로 냈다. 일반제품 여부·적용예외를 제품 사실 없이 추정한 결과다. |
| v23 / PPS-DEV-039 | TN→FP | 국가계약 공고의 가격입찰 기간을 지방 협상계약의 공고기간처럼 사용했다. 카드가 ‘국가계약이면 0’을 더 강하게 절차적으로 강제해야 한다. |
| v23 / PPS-DEV-191 | TN→FP | 지방 협상계약이지만, 모델은 가격입찰 일정만 보고 위반으로 냈다. v23은 공고일·제안서 마감일·설명회일의 법적 관계를 따져야 하며 가격입찰 일정만으로 1이 될 수 없다는 해석 카드가 필요하다. |
| v19 / PPS-DEV-036 | FN→TP | ‘전자입찰서 제출 마감일 전까지 보유, 계약 후 제출’ 문구를 잡았다. 그러나 v19는 이 artifact의 대상이 아니므로 전역 prompt 변화이며 공식 조건 효과로 승격하지 않는다. |
| v1 / PPS-DEV-058, v22 / PPS-DEV-26 | TP→FN | 두 항목도 artifact 대상이 아니다. 고정 reference가 전체 attention 분포를 바꾼 부작용 신호다. |

이 감사로 원래 제안한 v2a 범위를 더 좁힌다. 다음 artifact에는 product-dependent `v10`~`v18`을 넣지 않으며, v23도 카드 보정 단계로 옮긴다. 수치가 아직 빠진 v2는 고시금액 원문에서 실제 비교표를 완결 추출하기 전까지 승격 대상이 아니다. 다음 공식조건 후보는 **v5~v7·v20·v21**이며, v21은 유지 후보지만 나머지는 별도 source completeness 검토가 필요하다.

## EXP099 v2a fast-panel 결과 (2026-09-04)

EXP099는 EXP098을 base config로 두고 `reference_path`만 5개 규칙(`v5`, `v6`, `v7`, `v20`, `v21`)의 761자 artifact로 교체했다. 따라서 제품 의존 규칙, 불완결 고시금액 규칙, v23 날짜 규칙, 그리고 모든 실행·출력 정책은 EXP098과 동일하다. preflight는 reference path 한 항목만을 차이로 확인했고 mock 및 실제 final-message tokenizer admission을 통과했다. 최대 입력은 6,279 tokens였다.

| 조건 | Macro positive F1 | 기준선 대비 |
| --- | ---: | ---: |
| EXP051 기준선 | 0.125926 | — |
| EXP098 16-rule v2 | 0.155556 | +0.029630 |
| EXP099 5-rule v2a | 0.108069 | -0.017857 |

EXP099는 v21에서 TP 1개를 잃고 FP 2개를 남겨 F1 `0.500→0.000`으로 하락했다. v2·v12·v19의 EXP098 개선도 사라졌다. 반대로 EXP098에서 잃었던 v1·v22 TP는 복구됐다. 이처럼 artifact 대상 밖 항목까지 서로 반대로 움직였으므로, temperature 0이라도 remote provider의 생성 경로와 전체 prompt attention 변화가 fast20 한 번의 결과에 크게 섞인다.

**결정:** `official_conditions_v2`/`v2a`를 dev-200·canonical·submission으로 승격하지 않는다. 이 축의 다음 작업은 rule을 더 추가하는 것이 아니라, 동일 config 반복 또는 더 큰 고정 cohort에서 안정성을 먼저 측정해야 한다. 제품 CSV 친화 정보의 v10~v18 확대와 해석형 카드 보정은 여전히 독립 가설로 남지만, 이 법령 요약 결과를 근거로 결합하지 않는다.

## 폐기된 후속 실험 설계

기존의 `card + official conditions` 비교 계획은 폐기한다. 이후에는 법령 review를 decision card의 적용 전제·1 조건·0 조건·주요 예외·수치·기간에만 반영하고, `prompt.reference_path`는 비운다. 카드 version·문서 분할·출력 schema·제품 context·grouping은 계속 독립 ablation으로 관리한다.
