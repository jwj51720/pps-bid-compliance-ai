# EXP200 — corrected-input source-first dev200 result

작성: 2026-09-11, dev / mac

## 결론

교정 입력을 적용한 최초 dev200 실행은 macro positive-F1 `.334844`였지만, 14개 record의
malformed source-first final이 과거 recovery 코드에 의해 one-stage direct prediction으로
대체됐다. 이 혼합 결과는 정식 EXP200 점수로 사용하지 않는다.

recovery 결함을 수정하고 영향받은 record 20개를 label-blind 고정 panel로 재실행해 overlay한
repaired 결과는 **`.324798`**이다. EXP171 `.307962`보다 `+.016836` 높지만, frozen Python
rule 전 모델 자체 점수는 EXP171 `.250070`에서 `.249542`로 사실상 개선되지 않았다. 따라서
입력 교정은 의미 정합성을 회복했지만 Gemma 판단 성능의 독립적 상승으로 입증되지 않았다.

canonical/submission으로 승격하지 않는다.

## 실행 계약

- config: `configs/config.exp200-corrected-input-source-first-dev200-c4.yaml`
- base: EXP197, policy difference 없음; fast panel만 dev200 전체로 확장
- records/source: 200 / organizer-supplied 374 documents
- cards: `decision_cards_v10_v6_v7_scope.json`
- product: `conditions_and_provenance_v2`
- organizer semantics: `anonymization_v1`
- metadata: `official_lines_human_v2`
- source-first/full-final, model, temperature, seed, merge, evidence, frozen rules: 고정

최초 실행은 1,126.4초, 기록된 prompt/completion은 5,957,180 / 295,667 tokens, 비용은
약 `$0.655`였다. 실패한 initial final의 usage가 과거 serializer에 보존되지 않아 이 token/cost는
실제 총량보다 작을 수 있다. intended topology는 stage 1 217 + final 221 = 438 calls이며,
과거 direct fallback 16 calls가 추가되어 최초 실행의 실제 call estimate는 454다.

## recovery 결함과 복구

과거 `predict_with_fact_inventory_then_full_final()`은 final parse error가 하나라도 있으면
`self.predict(record)`를 호출해 navigation 없는 direct policy로 바꿨다. local inventory는
malformed를 빈 contribution으로 두지만 submission은 동일 message를 재시도하는 차이도 있었다.

수정 후 local도 submission처럼 malformed inventory/final pass만 동일 message로 1회 재시도한다.
direct fallback은 제거했다. 재시도에도 실패한 pass는 parse error와 zero contribution으로
남아 정책을 바꾸지 않는다. `inventory_retry_count`와 `final_retry_count`를 prediction artifact에
기록한다.

- recovery panel: `configs/exp200_recovery_panel_ids.json`, 20 unique IDs
- retry run: `outputs/exp-201-exp200-recovery-panel-c4/`
- retry run: inventory/final malformed 0, retry 발동 0, validation PASS
- repaired overlay: `outputs/exp-200-corrected-input-source-first-dev200-repaired/`
- overlay는 label이 아니라 최초 실행의 parse/recovery 상태로만 ID를 사전 고정
- repaired selected topology: 217 + 221 calls, persisted parse error 0
- repaired CSV: 200 rows / 49 columns / ID/evidence schema PASS, warning 21

## 성능 분해

| 지표 | EXP171 | EXP200 repaired | 변화 |
| --- | ---: | ---: | ---: |
| frozen rule 후 macro | .307962 | .324798 | +.016836 |
| model-owned macro | .250070 | .249542 | -.000528 |
| navigation gold-span hit | 48/54 | 49/54 | +1 |
| navigation hit인데 final FN | 22 | 22 | 0 |

주요 item 변화:

- 개선: v4 `0→.2222`, v12 `.2857→.4444`, v19 `.6667→.9231`,
  v22 `.6667→.8000`, v24 `0→.2222`
- 하락: v1 `.7692→.7143`, v5 `.5000→.3636`, v8 `.4615→.2500`,
  v9 `.5556→.5000`, v23 `.2000→.1053`
- 여전히 F1 0: v6, v7, v10, v11, v13, v14, v16, v17, v18, v20

입력 교정 focus item의 changed cells는 교정 10, 회귀 11이고 off-target은 교정 14, 회귀 30이다.
headline macro 상승은 support가 작은 item에서 발생한 비선형 효과와 provider/run 변동을 포함한다.
특히 v2/v3/v21 frozen rules가 model error를 크게 교정해 최종 점수를 끌어올린다.

## 해석

제품 조건·익명화 의미·공식 card 범위·human-readable metadata를 정확히 넣는 것은 제출 의미
정합성을 위해 유지해야 한다. 그러나 이 dev200은 “입력만 고치면 낮은 recall이 해결된다”는
가설을 지지하지 않는다.

gold evidence가 있는 54개 양성 중 49개(90.7%)는 navigation이 이미 관련 원문을 찾았지만,
그중 22개를 final이 0으로 냈다. 다음 구조 연구는 broad extraction을 더 늘리기보다 v4/v7처럼
찾은 사실을 적용 전제·대상·예외와 연결하지 못한 final judgment 병목을 item-local하게
검증해야 한다. 부재항목과 product unknown/gold 충돌은 별도 official-concordance 대상으로 둔다.

## 검증

- preflight: controlled policy difference 0
- exact-ID/input/label hash comparison: PASS
- repaired submission validation: PASS
- postprocess/model-owned audit: PASS
- navigation/final bottleneck audit: PASS
- merge panel exactness 및 중복/누락 방어 테스트: PASS
- full pytest: `198 passed`
