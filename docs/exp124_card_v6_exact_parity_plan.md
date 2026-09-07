# EXP124 — exact organizer-format에서 card v6의 독립 paired probe

## 이유

S0C self-label precedent와 case RAG는 source-fact localization 실패로 닫았다. evidence는
leaderboard Macro F1에 반영되지 않음도 다시 확인했다. 남은 candidate 중 raw law/RAG가 아닌
것은 organizer law를 offline 검토해 압축한 `decision_cards_v6.json`뿐이다.

historical EXP120은 card-v6를 포함해 dev200 `0.248932`, public `0.244317`을 기록했지만,
historical EXP109/EXP120은 shared renderer default `full_json` metadata였으므로 현재 확정한
organizer-compatible `official_lines` runtime과 직접 비교할 수 없다. EXP122A exact no-card의
fast-20만으로는 card 효과를 판단할 수 없다.

## 가설

4,000-char ordered single-call V/E, exact organizer metadata lines, same schema/decoder/admission에서
**card v6만** 추가하면 Gemma가 실제 공고의 조건을 더 정확히 적용한다. 이는 raw law, retrieval,
product fact, grouping, merge, output serialization을 바꾸지 않는다.

## 설계

동일 frozen `dev_fast_panel_v1` 20건을 새로운 paired call로 두 arm 모두 실행한다.

| arm | config | policy |
| --- | --- | --- |
| control | `exp124a` | EXP122A exact organizer-format, cards 없음 |
| treatment | `exp124b` | control + `decision_cards_v6.json` 하나 |

- shared document admission: 4,000 chars, `single`, overflow off
- profile/layout/metadata: `official_baseline_v1` / `plain` / `official_lines`
- output: ordinary 24 V/E schema, evidence resolver/validation unchanged
- LLM: same OpenRouter Gemma, temperature 0, seed 20260826, 1536 output cap,
  concurrency 4
- no new decision-card prose, no item-specific Python rule, no product context

## 실행 전 gate

1. `preflight_experiment.py`가 control→treatment 차이를
   `prompt.decision_cards_path` 하나로만 보고해야 한다.
2. 두 config 모두 `--mock`에서 20/20을 처리해야 한다.
3. actual prompt/token inspection에서 document context mode와 output schema가 동일하고,
   treatment의 추가 token만 card text임을 확인한다.

## 평가와 승격 기준

fast panel은 후보 순위용이다. 각 arm에 대해 Macro-F1뿐 아니라 v별 TP/FP/FN/F1, changed cell의
gold 개선/악화, predicted-positive count, parse/evidence validity, input token을 기록한다.

treatment가 다음을 모두 만족할 때만 **독립 fast cohort**를 설계한다.

1. paired Macro-F1이 control보다 +0.02 이상이고,
2. gain이 단일 v 하나의 우연한 변화가 아니라 최소 3개 v에서 error 개선을 보이며,
3. non-absence evidence validity·schema recovery가 악화하지 않고,
4. max input token이 admission budget 안이며 call count가 여전히 notice당 하나다.

그렇지 않으면 card-v6 exact-format branch를 dev200이나 제출로 승격하지 않는다. 어느 결과든
raw law/RAG, casebook, full split/grouping을 재개하는 근거로 사용하지 않는다.
