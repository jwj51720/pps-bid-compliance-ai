# EXP196: EXP171 입력 의미 완결 통합 결과

작성: 2026-09-11, dev / mac

## 결론

Astra 감사에서 확인된 제품 조건 누락, 익명화 표기 의미 누락, v6·v7 적용범위 오류를
EXP171 source-first/full-final 구조에 함께 반영한 입력 완결 후보를 구현했다. 기술적 입력
감사는 모두 통과했지만 fast20 macro positive-F1은 EXP179 `.287500`에서 `.213889`로
`.073611` 하락했다. 따라서 holdout/dev200 또는 canonical/submission으로 승격하지 않는다.

이 결과는 수정된 정보가 틀렸다는 증거가 아니다. 15개 focus item 중 changed cell은 3개뿐이고,
그중 교정 1·회귀 2였으며, off-target도 5개가 변했다. 한 번의 비결정적 end-to-end 호출에
세 입력 변경이 함께 있으므로 각 변경의 인과효과도 분리할 수 없다. 다만 현 형태의 통합 prompt가
fast gate에서 성능 후보가 아니라는 판단에는 충분하다.

## 기술적 입력 검증

- config: `configs/config.exp196-corrected-input-source-first-fast-panel-c4.yaml`
- base: EXP179
- 선언된 변경만 존재:
  - `prompt.decision_cards_path`
  - `prompt.competition_product_context_mode`
  - `prompt.organizer_input_semantics_mode`
- dev200 direct-final admission:
  - 제공 source documents 374, omission 0
  - metadata omission 0
  - card omission 0
  - organizer semantics omission 0
  - over-budget pack 0
- 조건부 제품 delivery:
  - 35 notices, 43 final packs
  - `특이사항` 누락 0
  - 최초 감사에서는 product-context 내부 제품 코드·doc-id·internal status 노출 0
  - 후속 전체 rendered-prefix 감사에서는 coded metadata 173/173건의 코드 노출을 발견;
    이 항목의 최초 PASS는 무효이며 EXP197에서 수정
- source-first exact-token profile:
  - stage 1: 217 calls, source omission 0
  - empty-navigation final: 218 calls, source omission 0, 총 435 calls
  - saved fast inventory: 24 + 24 = 48 calls
  - schema-upper: dev200 최대 450 calls, over-budget 0
- semantic-input contract: 24/24 PASS
- staged mock: 20 rows, 49 columns/ID/evidence validation PASS
- 실제 rendered review: short `DEV062`, attachment `DEV194`, overflow `DEV169`,
  익명화 지역 `DEV072`, 조건부 제품 `DEV054`

`DEV054`에서는 추정가격 `327,272,727원`과 고시 행 조건 `추정가격 3억원 미만에 한함`이
같은 final message에 들어갔다. 이는 이전 실제 입력 누락의 직접적인 복구 증거다.

## fast20 결과

- calls: 실제 inventory 결과 기준 48
- runtime: 110.044초
- prompt/completion tokens: 653,612 / 33,927
- parse error: 0
- validation: PASS, evidence warning 3건
- macro: `.287500 → .213889` (`-.073611`)
- focus changed: 3 (corrected 1, regressed 2)
- off-target changed: 5 (corrected 2, regressed 3)
- v6: `TP 0 / FP 0 / FN 1`
- v7: `TP 0 / FP 0 / FN 2`
- 제품군 v10–v18: v12만 F1 1.0, 나머지 모두 F1 0

## 해석과 다음 단계

입력 운반 결함은 복구됐지만, 더 많은 올바른 정보를 장문의 공통 prompt에 추가하는 것만으로
Gemma의 낮은 양성 recall이 해결되지 않았다. 다음 단계는 입력 사실을 다시 제거하는 것이 아니라,
필요한 사실이 제공된 뒤 어느 판단 단계에서 FN이 생기는지를 item-local 진단으로 분해하는 것이다.

또 mock의 staged rendered message에서 EXP171 `fact_inventory_full_final_v1`의 1차 system은
`공고 자료 원문만` 읽으라고 하지만 실제 user message에는 human-readable metadata도 포함된다.
이는 raw JSON 누출은 아니고 역사적 EXP171과 동일한 동작이지만, 역할 계약과 실제 입력이
불일치한다. 이 문제는 EXP196에 몰래 섞어 바꾸지 않고 별도 source-only stage ablation으로
다뤄야 한다.
