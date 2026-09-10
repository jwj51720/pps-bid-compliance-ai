# EXP151 — strict locator → final fast-20 결과

작성일: 2026-09-09 (dev / mac)

## 가설과 계약

EXP151은 EXP147 input-truthful single V/E를 base로, 1차 Gemma가 non-absence v의
actual 4k source substring만 찾고, 2차 Gemma가 원래 4k 공고 자료·카드·metadata를
다시 읽어 전 v1–v24의 V/E를 최종 판정하게 했다. locator text는 navigation signal일
뿐이며 `찾지못함`은 final 0이 아니다. final-stage parse failure에는 ordinary final
call recovery가 있다. EXP123 frozen v2/v3/v21 replacement는 final 조립 뒤 동일하게
적용했다.

이는 source coverage가 complete하다는 완결 전략 주장이 아니라, strict location task가
판정 보조가 될 수 있는지를 보는 diagnostic probe였다.

## 결과

| 정책 | fast-20 macro positive-F1 | 비교 |
| --- | ---: | --- |
| EXP147 input-truthful single V/E | 0.291071 | control |
| EXP151 strict locator → final | 0.248016 | -0.043056 |

- locator slots: 380 (20 notices × 19 non-absence items)
- non-empty locator snippets: 14
- gold-positive evidence가 있는 32개 position 중 locator snippet과 겹친 position: 2
- final evidence validity: 0.8571 (21 cases)
- final parse recovery: 0

strict locator는 unrelated source text를 억제했지만, final 판단에 쓸 충분한 후보를
거의 만들지 못했다. 따라서 이 형식의 locator를 v별 키워드로 더 조정하거나
`찾지못함 → 0`으로 쓰지 않는다.

## 후속 결정

넓은 candidate locator는 별도의 설계 가능성으로 보존한다. 그러나 EXP151 candidate
semantic-input audit가 v10–v18 CSV fact, attachment source coverage, exact document
scope, human-readable metadata policy의 결손을 확인했으므로, 그 결손을 해결하기 전에는
C2 API 호출을 하지 않는다. 관련 admission verdict는
`outputs/exp151-semantic-contract-audit-v1/semantic_contract_audit.md`를 참조한다.
