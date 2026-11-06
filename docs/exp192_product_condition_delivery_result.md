# EXP192: 경쟁제품 조건·출처 전달 결과

작성: 2026-09-11, dev / mac

## 결론

`competition_products_v1.json`의 `특이사항`이 final rendered message까지
전달되지 않던 입력 결함은 수정했다. exact tokenizer로 dev200 조건부
매칭 35건, final pack 42개를 전수 검사했고 모든 `특이사항`이 모든 해당
final pack에 존재했다. 당시 감사 범위인 `competition_product_context` 안에서는 제품 코드,
internal status, doc-id가 노출되지 않았다.

2026-09-11 후속 전수 감사에서 별도 `[나라장터 입력 메타]`의
`세부품명번호목록` 원시 값이 10자리 코드를 노출한다는 사실을 확인했다. 따라서 당시의
"prompt 코드 노출 없음" 결론은 검사 범위가 불완전해 무효다. 조건 전달 자체의 성공은
유효하지만, 전체 rendered input 완결 판정은 EXP197의 human-readable metadata 정책과
확대 감사로 대체한다.

다만 fast20 macro positive-F1은 EXP169 `.262500`에서 EXP192 `.255556`으로
`.006944` 하락했다. fast20의 조건부 매칭은 2건이고 둘 다 조건을 충족해
조건 경계 효과를 판별하기에 부족하다. 따라서 입력 결함 수정은 유지하되,
canonical 성능 정책으로는 승격하지 않는다.

## 실행·검증

- config: `configs/config.exp192-product-condition-delivery-fast-panel-c4.yaml`
- output: `outputs/exp-192-product-condition-delivery-fast-panel-c4/`
- cohort: `configs/dev_fast_panel_v1.json`, 20건
- call: 23 (18건 1 pack, 1건 2 packs, 1건 3 packs)
- runtime: 51.351초
- parse error: 0
- submission validation: PASS, evidence warning 3건
- semantic-input contract: 24/24 PASS
- 최초 dev200 delivery audit: 조건부 매칭 35건, 42 pack, product-context 범위 PASS;
  전체 prompt code-leak 판정에는 사용 불가

제품 군에서 v12는 F1 `.6667 → 1.0`으로 개선됐고 v17 오탐 1건이
사라졌지만, 다른 항목의 호출 변동이 함께 발생했다. 전체 9 cell이 바뀌었고
제품 정책과 무관한 v4·v19·v23·v24 변경도 있었다. 이 변경을 제품 문맥의
인과 효과로 해석하지 않는다.

## 판정

- 의미 입력 완결성: 개선 확정
- fast20 성능 승격: 미충족
- holdout/dev200 유료 확장: 보류
- 후속: gold를 사용해 조건 패널을 맞추지 말고, organizer fact만으로
  조건 충족·미충족·복수품목 사례를 분류한 진단에서 적용 관계를 먼저 검사한다.
