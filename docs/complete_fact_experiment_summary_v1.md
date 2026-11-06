# 판정 입력 완결 실험 정리 v1

작성일: 2026-09-10 (dev / mac)

## 이 문서의 기준

이 문서는 단순히 공고 원문을 많이 넣은 실험이 아니라, **모든 v 항목의 판정에
필요한 비원문 입력 사실**이 최종 판단 메시지에 제공된 실험만 정리한다.

다음 네 가지가 모두 있어야 한다.

1. `decision_cards_v6.json`의 항목별 적용 전제, 1 조건, 핵심 0 조건/예외
2. 사람이 읽을 수 있는 organizer metadata 중 해당 항목에 필요한 사실
3. `competition_products_v1.json`의 정확 코드 기반 경쟁제품/일반제품 적용 사실
4. 실제 공고문 원문. 이 문서는 원문이 4,000자로 잘렸는지, 16k/32k exact-token
   pack으로 전체를 보았는지를 별도 축으로 기록한다.

이는 `docs/semantic_input_contract_v1.md`의 24개 항목 계약에 대응한다. 카드만
있고 경쟁제품 CSV 사실이 없거나, 카드가 제공한다고 주장하는 사실이 실제 메시지에
없으면 이 문서의 **입력 완결** 실험으로 분류하지 않는다.

따라서 EXP123/147/148/149/150/151은 제외한다. 이들은 card/metadata의 일부는
있지만 exact competition-product applicability 또는 complete-fact profile을 제공하지
않은 4k diagnostic control이다. 점수가 높더라도 이 표의 가설을 검증한 결과가 아니다.

## 실험군과 결과

모든 점수는 dev positive-class macro F1이다. `fast20`과 `holdout20`은 후보 선별
전용이고, dev-200만 전체 로컬 평가이다.

| 계열 | 실험 | 호출 구조 | 원문 범위/최종 메시지 | 결과 |
| --- | --- | --- | --- | --- |
| Complete fact direct | EXP152 | direct V/E | 16k exact-token adaptive pack. 각 pack에서 완결 입력으로 V/E | fast20 0.224306 |
| Inventory then 4k final | EXP153 | 전체 원문 v별 inventory → V/E | 1차는 complete source, 최종은 complete-fact 입력 + 4k anchor + v별 발췌 | fast20 0.280556 |
| Complete fact direct 32k | EXP154 | direct V/E | 32k exact-token adaptive pack. 각 pack에서 완결 입력으로 V/E | fast20 0.241667 |
| Item partition | EXP155 | 2개 disjoint v group V/E | 각 group에 해당 카드·metadata·CSV 사실. 32k source pack | fast20 0.237500 |
| Item partition | EXP156 | 다른 2개 disjoint v group V/E | 각 group에 해당 카드·metadata·CSV 사실. 32k source pack | fast20 0.213889 |
| Fact inventory then 4k final | EXP157 / EXP158 | source category inventory → V/E | 1차 complete source, 최종은 complete-fact 입력 + 4k anchor + 7개 사실 범주 | fast20 0.286111 / holdout20 0.187500 |
| Rendering only | EXP159 | direct V/E | EXP154와 같은 32k complete-fact 입력, Markdown v2 renderer | fast20 0.244444 |
| Source-first/full-final | EXP167 / EXP168 / EXP179 | source category inventory → **full-source V/E** | 1차 complete source; 최종도 카드·metadata·CSV 사실·수집 사실·모든 admitted original source를 다시 제공 | fast20 0.286111, repeat 0.287500 / holdout20 0.229167 |
| Source-first/full-final | EXP171 | 위와 동일 | 위와 동일, dev-200 full evaluation | **dev200 0.307962** |
| Matched direct control | EXP169 / EXP170 / EXP172 | direct V/E | EXP167/171과 카드·metadata·CSV·32k source admission·decoding은 같고 source-first만 없음 | fast20 0.262500 / holdout20 0.211111 / dev200 0.259281 |

EXP164–166의 safe applicability gate는 complete-fact input을 사용했으나, final
Gemma 판단 뒤의 deterministic gate가 섞인 별도 정책이다. fast20 `0.258333`,
holdout20 `0.125000`으로 일반화 근거가 없어 이 비교의 후보군에서는 제외한다.

## 현재 확인된 교훈

1. **입력 사실의 완결성은 성능 개선의 충분조건이 아니다.** EXP152/154는 카드,
   metadata, 제품 적용 사실과 full source를 제공했지만 direct V/E는 fast20에서
   0.224/0.242였다. “더 많은 정보를 넣으면 자동으로 좋아진다”는 해석은 기각한다.

2. **원문을 다시 읽을 수 있는 source-first는 유일하게 일관된 개선 신호가 있다.**
   EXP167/168은 동일 capacity one-stage control EXP169/170보다 fast20에서 `+0.023611`,
   independent holdout20에서 `+0.018056`이었다. dev-200에서도 EXP171 `0.307962`가
   matched EXP172 `0.259281`보다 `+0.048681` 높았다.

3. **최종 단계에 원문 전체를 다시 주지 않은 inventory 방식은 일반화 증거가 없다.**
   EXP153/157은 fast20에서 회복했으나, EXP158 holdout은 0.187500으로 낮았다. inventory의
   null/누락이 음성 판정으로 작동하지 않게 구현했더라도, 4k anchor는 원문 대조를
   대체하지 못한다.

4. **v 분할은 입력 완결성과 별개로 품질/시간 위험이다.** EXP155/156은 하락했고,
   별도 제출 EXP135도 public 0.220069으로 일반화 근거를 잃었다. 현재 이득 증거 없이
   source-first와 v grouping을 곱하는 것은 금지한다.

5. **제품 CSV는 반드시 친화적 적용 사실로 렌더링해야 한다.** raw code/status key를
   prompt에 넣지 않는다. 경쟁제품 여부는 v10–v18의 적용 사실이지 evidence가 아니다.

## 현재 방향과 다음 후보

현재 quality incumbent는 `fact_inventory_full_final_v1` (EXP167/171/179)이다. 다만
submission default로 승격하지 않았다. dev-200에서 435 calls, OpenRouter remote 약
1,502초였고 vLLM의 2시간 runtime/throughput은 별도 검증이 필요하다.

다음 후보 EXP180은 이 complete-fact/full-final 구조를 그대로 유지한다. v23에만
적용계약법=지방계약법·낙찰방법=협상에의한계약이라는 organizer metadata router를
사용해, source stage가 날짜 원문을 `공고일`, `현장설명회일시`, `제안서_접수마감`,
`가격입찰_마감`, `긴급_재공고_표시` 역할로 수집한다. final Gemma는 여전히 모든
원문·카드·metadata를 다시 읽고 V/E를 단독 결정한다. Python은 이 navigation으로
v23을 0/1로 바꾸지 않는다.

실행 전에는 `docs/exp180_v23_timeline_navigation_plan.md`의 config diff, exact tokenizer
admission, mock, short/attachment/overflow rendered-message review, 24-v semantic-input
contract audit를 모두 통과해야 한다.

## 관련 산출물

- 계약/근거: `docs/semantic_input_contract_v1.md`
- EXP152–159 결과: `docs/exp152_complete_fact_fast_result.md`,
  `docs/exp153_inventory_final_fast_result.md`, `docs/exp157_source_fact_inventory_fast_result.md`,
  `docs/exp159_complete_fact_markdown_v2_fast_result.md`
- source-first 비교와 dev-200: `docs/exp167_source_first_full_final_retry_plan.md`
- repeat: `docs/exp179_source_first_repeat_plan.md`
- 다음 실험: `docs/exp180_v23_timeline_navigation_plan.md`
