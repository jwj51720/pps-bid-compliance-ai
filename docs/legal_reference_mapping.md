# 항목표 기반 법령 참조 매핑 및 그룹 초안

## 목적과 범위

이 문서는 `data/raw/open/data/항목표.json`의 v1~v24 법령 참조를 대회 제공
`data/raw/open/data/법령패키지/법령/`의 실제 파일 및 **완결된 법령 단위**에 연결하는
사전 검증 문서다. 현재 pipeline은 이 문서를 읽거나 항목 group별로 호출하지 않는다.
따라서 여기의 group은 구현 완료 상태가 아니라, 이후 파생 index와 RAG 실험의 명세다.

원칙은 다음과 같다.

- 약칭을 파일명과 문자열 유사도로 런타임 추정하지 않는다. 이 문서의 canonical ID만 쓴다.
- 법률·시행령·시행규칙은 선택한 **조문 전체**를 넣는다. 특정 항이 중요해도 조문을 문자 수로
  자르지 않는다.
- 예규·지침은 선택한 **장/절 전체**, 별표는 **별표 전체**를 넣는다.
- `전체 법령 txt`는 selector가 아니다. 단, 항목표가 조문/장/절을 전혀 지정하지 않은 경우는
  `검증 필요`로 남기며 전문을 임의로 prompt에 넣지 않는다.
- 공식 법령 chunk는 고정 문맥이다. 매 document pass에 원문 그대로 넣고 그 토큰까지 admission
  한다. 고정 문맥이 예산을 넘으면 공고문을 자르거나 법령을 생략하지 않고 upstream routing을
  실패시킨다.

## 검증한 별칭과 실제 파일

| Canonical ID | 항목표의 표기/약칭 | 법령패키지 실제 파일 | 검증 |
|---|---|---|---|
| `national_decree` | 국가계약법 시행령 | `국가를 당사자로 하는 계약에 관한 법률 시행령.txt` | 파일·제12/21/43조 확인 |
| `national_rule` | 국가계약법 시행규칙 | `국가를 당사자로 하는 계약에 관한 법률 시행규칙.txt` | 파일·제17/25조 확인 |
| `local_decree` | 지방계약법시행령 | `지방자치단체를 당사자로 하는 계약에 관한 법률 시행령.txt` | 파일·제13/20/35/43조 확인 |
| `local_rule` | 지방계약법 시행규칙 | `지방자치단체를 당사자로 하는 계약에 관한 법률 시행규칙.txt` | 파일·제17/24/25조 확인 |
| `government_guide` | 정부 입찰·계약 집행기준 | `(계약예규) 정부 입찰·계약 집행기준.txt` | 제2장·제5조 heading 확인 |
| `local_guide` | 지방자치단체 입찰 및 계약 집행기준 | `지방자치단체 입찰 및 계약 집행기준.txt` | 제1/5/6장 heading 확인 |
| `local_award` | 지방자치단체 입찰시 낙찰자 결정기준 | `지방자치단체 입찰시 낙찰자 결정기준.txt` | 제7장·제3절 heading 확인 |
| `sme_law` | 중소기업제품 구매촉진 및 판로지원법 | `중소기업제품 구매촉진 및 판로지원에 관한 법률.txt` | 제7/9조 확인 |
| `sme_decree` | 같은 법 시행령 | `중소기업제품 구매촉진 및 판로지원에 관한 법률 시행령.txt` | 제2조·제2조의2/제2조의3 추가 확인 필요 |
| `competition_list` | 경쟁제품·직접구매 대상 품목 지정 내역 | `중소기업자간 경쟁제품 및 공사용자재 직접구매 대상 품목 지정 내역.txt` | 파일 확인 |
| `price_notice` | 고시금액 | `국가를 당사자로 하는 계약에 관한 법률 등의 재정경제부장관이 정하는 고시금액.txt` | 파일 확인 |
| `sw_law` | 소프트웨어진흥법 | `소프트웨어 진흥법.txt` | 파일 확인, 조문 selector는 미확정 |
| `sw_guideline` | 중소 SW사업자 참여지원 지침 | `중소 소프트웨어사업자의 사업 참여 지원에 관한 지침.txt` | 제2조·별표 1 heading 확인 |
| `joint_guide` | 공동계약운용요령 | `(계약예규) 공동계약운용요령.txt` | 파일 확인, selector 미확정 |

예를 들어 v23의 `지방계약법시행령 제35조`는 `local_decree.article_35`이다. 실제 원문은
`제35조(입찰공고의 시기)`이며, 제5·6항에 협상계약의 제안서 제출 마감 전 공고기간이 있다.
이 연결은 이전 코드에 존재한 것이 아니라, 이번 원문 파일과 조문 제목을 대조해 확인한
mapping이다.

## v별 canonical reference 명세

`article_*`는 조문 전체, `chapter_*`/`section_*`는 해당 heading의 완결 범위를 뜻한다.
`?`는 실제 원문 selector를 추가 검증한 뒤에만 derived index에 넣을 항목이다.

| v | Canonical reference IDs |
|---|---|
| v1 | `national_decree.article_12`, `national_decree.article_21`, `local_decree.article_13`, `local_decree.article_20` |
| v2 | `national_decree.article_21`, `national_rule.article_25`, `local_decree.article_20`, `local_rule.article_25`, `local_guide.chapter_1.section_1.item_7` |
| v3 | `national_decree.article_21`, `national_rule.article_25`, `government_guide.chapter_2.article_5`, `local_decree.article_20`, `local_rule.article_25` |
| v4 | `government_guide.chapter_2.article_5`, `local_guide.chapter_1` |
| v5 | `national_decree.article_21`, `price_notice.document`, `local_decree.article_20`, `local_rule.article_24` |
| v6 | `national_rule.article_25`, `local_rule.article_25`, `local_guide.chapter_5.section_3.item_1.subitem_na` |
| v7 | `national_rule.article_25`, `local_rule.article_25`, `local_guide.chapter_5.section_3.item_1.subitem_na` |
| v8 | `national_rule.article_25`, `local_rule.article_25`, `local_guide.chapter_5.section_3.item_1.subitem_na` |
| v9 | `government_guide.chapter_2.article_5`, `local_guide.chapter_1.section_1.item_7` |
| v10 | `sme_law.article_9`, `competition_list.document` |
| v11 | `national_decree.article_21`, `local_decree.article_20`, `sme_law.article_7`, `competition_list.document` |
| v12 | `national_decree.article_21`, `local_decree.article_20`, `competition_list.document` (비고 기반 적용성 확인) |
| v13 | `national_decree.article_21`, `local_decree.article_20`, `sme_law.article_7` |
| v14 | `national_decree.article_21`, `local_decree.article_20`, `sme_decree.article_2_2`, `sme_decree.article_2_3` |
| v15 | `national_decree.article_21`, `local_decree.article_20`, `sme_decree.article_2_2`, `sme_decree.article_2_3` |
| v16 | `national_decree.article_21`, `local_decree.article_20`, `sme_decree.article_2_2`, `sme_decree.article_2_3` |
| v17 | `national_decree.article_21`, `local_decree.article_20`, `sme_decree.article_2_2`, `sme_decree.article_2_3` |
| v18 | `national_decree.article_21`, `local_decree.article_20`, `sme_decree.article_2_2`, `sme_decree.article_2_3` |
| v19 | `national_decree.article_12`, `national_rule.article_17`, `government_guide.chapter_2.article_5_3`, `local_decree.article_13`, `local_rule.article_17`, `local_guide.chapter_1.section_1.item_7` |
| v20 | `sw_law.?`, `sw_guideline.article_2`, `sw_guideline.appendix_1` |
| v21 | `joint_guide.?`, `local_guide.chapter_6` |
| v22 | `national_decree.article_43`, `local_decree.article_43` |
| v23 | `local_decree.article_35`, `local_award.chapter_7.section_3` |
| v24 | 없음: 문서와 나라장터 metadata의 대조형 항목 |

## 참고자료 중첩 기준의 group 초안

다음 group은 항목 의미가 아니라 **동일 canonical reference의 중첩**을 먼저 최대화했다.
group 내 fixed-reference bundle은 해당 행의 reference ID 합집합이다. `local/national`은
공고 metadata로 명확히 하나가 선택되는 경우에만 그 법체계의 selector만 넣는다. 불명확한
경우에 한 법체계를 추측해 생략하지 않는다.

| Group | v | 강한 공유 reference | 비고 |
|---|---|---|---|
| G01 `qualification` | v1, v19 | `national_decree.article_12`, `local_decree.article_13` | v19의 추가 시행규칙·예규는 bundle에 합침 |
| G02 `performance` | v2, v3 | `national_decree.article_21`, `national_rule.article_25`, `local_decree.article_20`, `local_rule.article_25` | v3만 `government_guide` 추가 |
| G03 `specific_requirement` | v4, v9 | `government_guide.chapter_2.article_5`; 지방에서는 `local_guide` | v4의 지방 참조가 제1장 전체라 토큰 측정 필수 |
| G04 `regional_small_contract` | v6, v7, v8 | 세 reference가 모두 동일 | 가장 강한 완전 중첩 group |
| G05 `threshold_region` | v5 | 공유가 약해 단독 | 고시금액 문서가 고정 bundle에 포함 |
| G06 `competition_product` | v10, v11, v12, v13 | `competition_list.document`, v11/v13의 `sme_law.article_7`, v11~v13의 시행령 조문 | 제품 적용성 lookup도 여기서 제공 |
| G07 `general_product` | v14, v15, v16, v17, v18 | 네 reference가 모두 동일 | 가장 강한 완전 중첩 group |
| G08 `software` | v20 | 공유 없음 | `sw_law.?`와 `joint_guide.?`처럼 미확정 selector 해소 전 실행 불가 |
| G09 `joint_contract` | v21 | 공유 없음 | `local_guide.chapter_6` 전체 길이 측정 필요 |
| G10 `site_briefing_qualification` | v22 | 공유 없음 | 양 법체계 시행령 제43조 |
| G11 `site_briefing_period` | v23 | 공유 없음 | 지방·협상 metadata일 때만 후보; `local_decree.article_35`와 `local_award.chapter_7.section_3` |
| G12 `notice_metadata_consistency` | v24 | 법령 reference 없음 | 별도 문서-메타 대조 call/규칙 |

G01~G12는 최종 호출 수가 아니다. 다음 단계에서 각 group의 **완성된 원문 bundle**을 정확한
Gemma chat tokenizer로 세고, 예산을 넘는 group만 더 쪼갠다. 특히 `local_guide.chapter_1`,
`local_guide.chapter_6`, `local_award.chapter_7.section_3`은 긴 예규이므로 selector가
완결 범위를 정확히 가리키는지와 토큰 길이를 확인하기 전에는 prompt에 넣지 않는다.

## 다음 구현 순서

1. 위 표를 machine-readable `data/derived/legal_reference_map_v1.json`으로 옮긴다.
2. 모든 `?` selector와 예규의 heading boundary를 원문에서 검증한다.
3. 추출기와 manifest를 만들어 각 chunk의 원본 SHA-256, 시작/끝 heading, chunk SHA-256,
   Gemma token 수를 저장한다.
4. group별 bundle 토큰을 재고, 초과 group만 분할한다.
5. 그 뒤에만 shared pipeline에 `active_items`와 group별 결과 병합을 추가하고 first-20
   ablation을 한다. 법령 RAG를 적용하지 않는 현재 canonical submission policy는 이 문서만으로
   바꾸지 않는다.
