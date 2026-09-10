# EXP171 source-first/full-final 제출 후보

작성일: 2026-09-10 (dev / mac)

## 정책

제출 candidate `submit-exp171-source-first-full-final-v1`은 local EXP171과 같은
`fact_inventory_full_final_v1`이다.

1. 모든 exact-token admitted source pack을 Gemma가 읽고, 7개 source fact category의
   변경 없는 원문 후보만 반환한다. 이 단계는 0/1, 법령 해석, evidence 확정을 하지 않는다.
2. Python은 substring과 doc id만 검증·중복제거한다. navigation 누락·parse failure는
   어떤 v도 0으로 만들지 않는다.
3. final Gemma는 card v6, 필요한 친화적 metadata, competition product fact, 수집된
   navigation 및 every admitted original source pack을 보고 v1–v24/e1–e24를 최종 판정한다.
4. EXP123 frozen v2/v3/v21 postprocess, existing evidence resolver, absence merge는 local
   EXP171과 동일하다.

`submission/script.py`는 두 단계 모두 global pending message list를 `batch_size=64`로
vLLM batch 처리한다. Batch는 call count를 줄이지 않지만 vLLM scheduling/throughput을 위해
필수다. source-first mode는 v-item grouping을 금지한다.

## 패키지 검증

- archive: `dist/pps_20260910_101210.zip`
- 30자 이내 timestamped filename: PASS
- included static assets: `decision_cards_v6.json`, `competition_products_v1.json`,
  `runtime_config.json`, `script.py`, `src/`, `requirements.txt`
- runtime policy parity: `config.yaml` ↔ `submission/runtime_config.json`: PASS
- staged archive mock: organizer-format `PPS_DATA_DIR` 10 records, source-first stage + final
  stage, batch 64: PASS
- output: 10 rows, 49 ordered columns, unique ids, parser retry 0, unrecovered 0

GPU/vLLM smoke and full evaluator throughput measurement are not available in this macOS
environment and remain the explicitly accepted limitation. Local EXP171 used 435 total calls on
dev200 (216 source + 219 final); public runtime must be monitored against the two-hour limit.

## Local evidence

- EXP167 fast20 `.286111`; repeat EXP179 `.287500`
- EXP168 independent holdout20 `.229167`
- EXP171 dev200 `.307962`
- capacity-matched direct controls: EXP169 `.262500`, EXP170 `.211111`, EXP172 dev200 `.259281`

This is the best local complete-fact candidate, not a claim that public quality or vLLM runtime
has already been proven.
