# EXP150 — triage → strict final fast-20 결과

작성일: 2026-09-09 (dev / mac)

## 계약과 비교 대상

EXP150은 `configs/config.exp150-triage-strict-card-v6-fast-panel.yaml`의
`staged_run.mode: triage_then_strict_v1`이다. 같은 4,000자 single context에서
1차 Gemma가 v1–v24를 다음 route state로만 분류하고, 2차 Gemma가 route된 item만
V/E를 최종 판정한다.

- route states: `명시근거`, `부재검토`, `불명확`, `해당없음`
- `v10/v11/v16/v18/v20`은 1차 상태와 무관하게 2차로 보낸다.
- triage JSON이 malformed이면 24개 전부를 2차로 보낸다.
- strict V/E가 malformed이면 ordinary all-item final call로 recovery한다.
- v2/v3/v21 EXP123 frozen replacement는 최종 row 조립 뒤 한 번만 적용한다.
- raw law/CSV/RAG/새 Python item rule은 넣지 않았다.

새 B-stage input에는 실제로 제공하지 않는 경쟁제품 CSV 조회나 omitted attachment를
봤다는 주장을 넣을 수 없으므로, `decision_cards_v6_input_truthful_v1.json`을 사용했다.
따라서 **직접 single-call control은 같은 card의 EXP147**이며, historical card v6
EXP123과의 단일변경 대조라고 주장하지 않는다.

사전 검증:

- `scripts/preflight_experiment.py`에서 declared difference는
  `staged_run.mode` 하나였다.
- mock, staged actual-message export, parser/fallback unit test가 통과했다.
- mock/real stage message는 ignored
  `outputs/exp-150-triage-strict-card-v6-fast-panel[-mock]/staged_input_examples.md`에 있다.

## fast-20 결과

| 정책 | Macro positive-F1 | 비교 |
| --- | ---: | --- |
| EXP147 input-truthful single V/E | 0.291071 | control |
| EXP150 triage → strict | 0.277020 | -0.014051 |

EXP150의 20 notice는 모두 parse했고 strict recovery는 0건이었다. 그러나 이것은
품질 통과를 뜻하지 않는다.

| route 측정 | 결과 |
| --- | ---: |
| triage state 합계 | 해당없음 296, 부재검토 154, 명시근거 28, 불명확 2 |
| strict item 수 | 평균 9.2개/notice, 범위 6–13 |
| strict recovery | 0/20 |
| dev gold positive가 `해당없음`으로 종료 | 19개 |

종료된 gold positive는 v4(3), v24(3), v7(2)를 포함하며 v1/v2/v3/v6/v8/v9/
v13/v14/v15/v17/v21에도 분포했다. 특히 source-visible FN이 이미 확인된 v4·v7의
명시 문구를 triage가 final strict stage로 보내지 않은 것이 이 architecture의 핵심
실패다. 이 구조는 “문구가 없으면 안전하게 0”이라는 coverage 전제를 만족하지 않는다.

항목 변화의 대표 사례:

- v4: F1 `0.500 → 0.000`, TP `1 → 0`, FN `2 → 3`.
- v15: F1 `1.000 → 0.000`, TP `1 → 0`, FP `0 → 4`.
- v20은 유일하게 TP 하나를 회복했으나, 전체 안전성 결론을 바꾸지 못한다.
- v23은 TP가 유지됐지만 FP `5 → 9`로 늘었다.

## 결정

이 v1 B design은 holdout/dev-200/submission으로 확대하지 않는다. 단순히
`해당없음`을 더 엄격하게 또는 v별로 조정해 다시 시도하지 않는다. 그것은 fast panel
label에 맞춘 route rule이 된다.

다음 candidate C는 `찾지못함 → 0`을 쓰지 않는 locator→final 구조로만 검토한다.
locator가 최종 label을 소유하지 않고, non-absence item의 source substring/navigation
signal만 제공하며, final stage는 원래 4k context를 다시 읽어 V/E를 낸다. C도 coverage,
malformed rate, call count를 fast-20에서 먼저 평가한다.
