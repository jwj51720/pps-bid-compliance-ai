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
| v20 | `sw_law.article_48`, `sw_guideline.article_2`, `sw_guideline.article_3`, `sw_guideline.appendix_1` |
| v21 | `joint_guide.article_9.paragraph_5`, `local_guide.chapter_6.section_2.item_1.subitem_na_2` |
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

## 2026-09-02: 4 profile × 4 v-group mapping (`profile_group_map`)

EXP036은 위의 기존 profile 완결 bundle을 읽거나 재활용하지 않는다.
`scripts/build_four_profile_group_law_bundles.py`가 organizer 법령 원문에서 조각을 다시
추출해 `data/derived/legal_reference_profile_group_v2/` 아래에 정확히 **16개**의 fixed
context를 생성한다. `mapping.json` 및 `manifest.json`의 `profile_group_map` 필드는
각 bundle에 대해 profile metadata 조건, v 목록, v별 chunk key, 적용 불가 항목 사유,
그리고 제품 고시가 기존 exact-code lookup으로 별도 제공된다는 사실을 보존한다.

| v group | v | 필요한 법령 범위 |
|---|---|---|
| `G01_qualification_threshold` | v1~v5 | 참가자격·실적·고시금액·지역제한 조문 |
| `G02_document_restrictions` | v6~v9, v19 | 소액수의 지역/중복 제한, 특정모델, 확약서 조문 |
| `G03_product_restrictions` | v10~v18 | 경쟁제품·일반제품·중소기업 제한 조문. 품목 지정 사실은 기존 exact-code CSV lookup이 제공 |
| `G04_procedure_and_consistency` | v20~v24 | SW·공동계약·설명회·공고기간. v24는 법령 조문 없이 문서/metadata 대조 |

profile은 organizer metadata의 `적용계약법`, `계약방법`, `낙찰방법`만으로 정한다:
`national`, `local_general`, `local_small`, `local_negotiated`. 지방 소액수의와 협상계약이
동시에 표시된 조합은 dev에는 없고, 이 16-bundle 전략에 포함되지 않는다. 해당 조합은 법령을
조용히 생략하지 않고 별도의 다섯 번째 profile이 검증될 때까지 fail closed한다. 따라서 16개
각 bundle은 자신이 담당하는 profile과 v group에서 가능한 항목에 필요한 조문을 완결로 담고,
profile상 성립 불가한 v23 등의 조문은 넣지 않는다.

## 2026-09-01 원문 재점검: selector 보충과 notice-level bundle 방향

다음은 항목표의 표기와 실제 법령 원문을 다시 대조하여 확정한 보충 사항이다.

- v20: `소프트웨어 진흥법` 제48조가 중소 SW사업자의 참여 제한·예외를 직접 규정한다.
  `중소 소프트웨어사업자의 사업 참여 지원에 관한 지침`은 제2조(하한), 제3조(적용),
  별표 1(금액표)을 함께 넣는다. 법률 전문이나 지침 전문은 넣지 않는다.
- v21: 국가계약 방향은 `(계약예규) 공동계약운용요령` 제9조 제5항(구성원별
  계약참여 최소지분율), 지방계약 방향은 `지방자치단체 입찰 및 계약 집행기준` 제6장
  공동계약 운영요령 제2절 `1. 나. 구성원 수 등`의 `2)`와 바로 뒤의 `3)` 예외다.
  기존의 `joint_guide.?`, `local_guide.chapter_6` 전문 selector를 쓰지 않는다.
- v6~v8: 지방 소액수의의 지역·실적 관계는 `지방자치단체 입찰 및 계약 집행기준`
  제5장 제3절 `1. 금액기준에 따른 2인 이상 견적서 제출 수의계약`의 `나. 수의계약 요령`
  `3)`부터 `7)`까지가 완결 범위다. `3)` 지역 범위, `6)` 실적 등 추가 제한,
  `7)` 중복제한 허용 여부를 한 덩어리로 보존한다.

이 mapping은 v별 호출 group(G01~G12)과 별개로, **공고 하나에 한 개의 reference
bundle을 선택하는 profile**에도 사용한다. 첫 RAG 전략의 profile 초안은 아래와 같다.

| Notice profile | 결정 metadata | bundle 구성 |
|---|---|---|
| `national` | `적용계약법=국가계약법` | 국가계약 selector + 국가/지방 공통 SME·SW selector + 공통 고시 |
| `local_general` | `적용계약법=지방계약법`, 일반 계약 | 지방계약 selector + 공통 SME·SW selector + 공통 고시 |
| `local_small_contract` | 지방계약법 + 2인 이상 견적 수의계약 | `local_general` + v6~v8의 제5장 제3절 `1. 나. 3)~7)` |
| `fallback_union` | 계약법 누락·비정형·복수값 | 국가·지방 selector 합집합. 임의의 hard exclusion 대신 안전 fallback으로만 사용 |

각 profile은 v1~v24의 판정에 필요한 조문을 모두 가진다. profile routing은 대회 제공
metadata의 정확한 값만 사용하며, 법령을 추정하거나 공고문 텍스트를 정규식으로 해석해
선택하지 않는다. `competition_list`의 품목 매칭은 bundle 선택이 아니라 기존 공고별
제품문맥 lookup으로 계속 제공한다.

## 2026-09-01 dev-200 기반: 공고별 완결 bundle 유형화 검증

앞선 단일 합집합 시도는 26개 조각, 약 10.7만 글자였고, 법령만 포함한 최종 chat prompt가
32k 입력 예산을 초과했다. 또한 국가계약 방향 v21의 `공동계약운용요령 제9조`가 빠져 있어
완결 bundle도 아니었다. 이 조각을 더하면 예산 초과는 더 커진다. 따라서 완결 단일 bundle은
실험 대상이 아니라 **불가능한 전략**으로 확정한다.
대신 항목표의 법체계 적용조건과 dev의 organizer metadata를 교차 확인했다. 결과는 다음
네 가지 완결 bundle profile이다. 각 profile은 그 공고에서 성립할 수 있는 v1~v24에 필요한
법령 조각을 모두 포함한다. 즉 dev에서는 한 공고에 profile 하나만 선택하면 되며, profile을
두 개 이어 붙이는 호출은 필요하지 않았다.

| Profile | 결정 기준 (organizer metadata) | dev 200건 | 법령 범위 |
|---|---|---:|---|
| `national_complete` | `적용계약법=국가계약법` | 84 | 국가 시행령·시행규칙·정부 집행기준·공동계약운용요령 제9조 + 공통 SME/SW/고시 |
| `local_small_complete` | `적용계약법=지방계약법` 및 (`계약방법=수의계약` 또는 `낙찰방법=소액수의견적`) | 29 | 지방 기본 범위 + 지방 수의계약 제5장 제3절 `1. 나. 3)~7)` + 공통 범위 |
| `local_negotiated_complete` | 지방계약법 및 `낙찰방법=협상에의한계약` | 41 | 지방 기본 범위 + 지방 낙찰자 결정기준 제7장 제3절 + 공통 범위 |
| `local_general_complete` | 나머지 지방계약법 | 46 | 지방 시행령·시행규칙·제1장 주의사항·제6장 공동계약 + 공통 범위 |

`local_small_complete`와 `local_negotiated_complete`가 동시에 필요한 조합은 dev에 없다.
향후 test router에서 이 조합이 실제로 나오면, 두 overlay를 합친 `local_small_negotiated_complete`
profile을 선택한다. 이 0건 fallback bundle도 미리 생성했다. 이것은 임의의 텍스트 추정이 아니라
두 metadata 조건의 AND다. 공동계약
참조(v21)는 공고문 안의 지분 문구가 있는지와 무관하게 국가/지방 기본 bundle에 각각 넣는다.
따라서 `공동도급구성방식`을 보고 법령을 빼는 위험한 hard gate를 두지 않는다.

### 완결성 및 정확 tokenizer admission 측정

측정은 실제 Gemma 4 tokenizer의 `apply_chat_template`로, EXP014의 결정 카드·문서별 엄격
지시와 2,500 output reserve를 포함한 빈 문서 pass에서 수행했다. 예산은 30,268 tokens이다.
공식 경쟁제품 고시 전체는 고정 bundle에 복제하지 않는다. 이미 organizer CSV를 정확 코드로
조회해 공고별 친화 문맥으로 넣고 있으며, 이 조회 결과는 v10·v11·v13에만 쓰인다.

| Profile | 법령 조각 수 | 법령 글자 수 | 고정 prompt tokens | 문서에 남는 tokens |
|---|---:|---:|---:|---:|
| `national_complete` | 16 | 28,464 | 22,424 | 7,844 |
| `local_general_complete` | 18 | 26,427 | 20,868 | 9,400 |
| `local_small_complete` | 19 | 30,009 | 23,044 | 7,224 |
| `local_negotiated_complete` | 19 | 29,097 | 22,463 | 7,805 |
| `local_small_negotiated_complete` (fallback) | 20 | 32,679 | 24,639 | 5,629 |

생성한 다섯 bundle 모두 문서 투입 전 admission을 통과한다. 남는 예산보다 긴 원문 문서는 기존
`full_split_merge`의 exact-token split으로 분할한다. 법령 조각은 고정 문맥이므로 절대
분할하거나 생략하지 않는다. `scripts/build_routed_law_bundles.py`가 실제 bundle과 manifest를
생성하며, manifest에는 source file·selector·원문/조각/bundle SHA-256이 남는다.

중요하게도 이것은 아직 RAG 성능 실험이 아니다. 현재 확인된 것은 (a) organizer metadata로
결정적인 유형화가 가능하고, (b) 한 profile의 완결 법령 범위가 token admission상 가능하며,
(c) dev에서는 공고마다 1개 profile이면 충분하다는 구조적 타당성이다. shared pipeline,
root `config.yaml`, submission은 이 확인만으로 변경하지 않는다.

### EXP018 first-20 검증 결과

`configs/config.exp018-routed-law-first20.yaml`은 EXP014의 full-split·card v2·제품문맥을
그대로 두고 `reference_routing: metadata_v1`만 추가한 실험이다. router는 처음 20건에서 국가
8, 지방 협상 6, 지방 일반 5, 지방 소액수의 1건을 각각 선택했고, 총 62 document pass를 만들었다.
각 pass는 exact Gemma tokenizer admission을 통과했다. 결과는 Macro F1 **0.093254**,
runtime **165.0초**, prompt tokens **1,751,492**였다. 비교 기준인 EXP012/EXP014 계열
first-20 card v2 + 제품문맥은 Macro F1 **0.145833**이므로, 이 완결 bundle의 첫 적용은 성능
개선이 아니었다. 특히 v3는 TP가 1→2로 늘었지만 v5 TP와 v13 TP를 잃어 전체 점수가 하락했다.
이 결과만으로 canonical EXP014 제출 정책을 바꾸지 않는다.

### EXP019 first-20: v별 참고조문 navigation 결과

EXP018의 핵심 결함은 공고→bundle만 라우팅하고, 모델에게 각 v가 bundle의 어느 조각을
읽어야 하는지는 알려주지 않은 점이었다. EXP019는 모든 final system prompt에
`[항목별 공식 참고자료 안내]`을 넣어, 선택된 법체계에서 각 v가 볼 조문·장·절을 정확한
source header 이름으로 연결했다. 법령은 적용기준이고 evidence는 대상 문서에서만 찾는다는
제약도 명시했다. 실제 입력 예시는
`outputs/exp-019-routed-law-navigation-first20/input_examples.md`에 세 pass를 보존했다.

결과는 Macro F1 **0.138889**, runtime **194.2초**, 70 document pass, prompt tokens
**2,018,345**였다. EXP018의 0.093254보다 크게 회복됐고, v5는 0→1.0, v3는
0.571→0.667, v8은 0→0.667이 됐다. 그러나 v1 TP를 잃고 v13은 계속 0이며 v17·v23·v24
false positive가 새로 생겨 EXP012/EXP014 계열 first-20의 0.145833에는 미달한다.
따라서 v별 navigation은 RAG의 필수 구성요소로 확인됐지만, 모든 24개 안내와 모든 법령을
한 호출에 넣는 현 구조는 아직 canonical 정책으로 승격하지 않는다.

## 다음 구현 순서

1. 위 표를 machine-readable `data/derived/legal_reference_map_v1.json`으로 옮긴다.
2. 모든 `?` selector와 예규의 heading boundary를 원문에서 검증한다.
3. 추출기와 manifest를 만들어 각 chunk의 원본 SHA-256, 시작/끝 heading, chunk SHA-256,
   Gemma token 수를 저장한다.
4. group별 bundle 토큰을 재고, 초과 group만 분할한다.
5. 그 뒤에만 shared pipeline에 `active_items`와 group별 결과 병합을 추가하고 first-20
   ablation을 한다. 법령 RAG를 적용하지 않는 현재 canonical submission policy는 이 문서만으로
   바꾸지 않는다.

## EXP021 단일 공고 구조 검증 (PPS-DEV-01)

2026-09-01에 EXP019와 같은 full-split/evidence/card/product 조건에서 dev 첫 공고
`PPS-DEV-01` 하나만 12개 reference-overlap group으로 실행했다. 이 공고는
`적용계약법=지방계약법`, `낙찰방법=협상에의한계약`이므로 모든 group은
`local_negotiated_complete`에서 **그 group의 v가 참조하는 조각만** 받았다. 공고문과
과업지시서가 있어 group당 두 document pass, 총 24 Gemma 호출이었다.

공유 pipeline은 이제 `prompt.active_items`로 응답 schema·항목표·카드 범위를 함께 줄일 수
있다. 따라서 예를 들어 G03는 v4/v9 두 키만 응답하고 지방 계약집행기준 제1장 7 조각만 받으며,
G11은 v23 한 키와 지방계약법 시행령 제35조/낙찰자 결정기준 제7장 제3절만 받는다. Python은
문서 pass 병합과 group 결과의 키별 합치만 하며, 문구 해석 규칙을 추가하지 않는다.

실제 결과는 v1=1(정답), v4=1(false positive), v23=1(false positive), 나머지 0이었다.
즉 **분할 호출·최소 법령 bundle·selected-key structured output 자체는 정상 동작**했고,
24개 동시 호출에서 v1을 찾아낸 것처럼 기본 검출력은 유지됐다. 그러나 이 한 공고만으로
성능 향상을 주장할 수 없고, v4/v23의 과잉판정은 group 수가 작아졌다고 자동 해소되지 않음을
보였다. 다음 단계는 group 효율화 전에 이 두 판단의 입력/카드/법령 적용조건을 읽어
과잉판정 원인을 진단하고, 독립된 20건 ablation으로 검증하는 것이다.

재현: `PYTHONPATH=. .venv/bin/python scripts/build_routed_law_bundles.py` 후
`PYTHONPATH=. .venv/bin/python scripts/run_grouped_notice.py --fresh`. 결과는
`outputs/exp-021-grouped-one-notice/`의 `group_predictions.json`, `grouping_audit.json`,
`merged_prediction.json`, 그리고 모든 실제 채팅 입력을 담은 `input_examples.md`에 남긴다.

## 2026-09-02 v23 selector correction

`지방자치단체 입찰시 낙찰자 결정기준.txt`에는 여러 장에 `제3절 입찰과 계약상대자 결정절차`가
반복된다. 기존 전역 `last` selector는 제10장 품질 등 기준의 동명 절을 잘못 선택했다. v23은
반드시 **제7장 협상에 의한 계약 낙찰자 결정기준 제3절**의 본문을 선택한다. 해당 원문에는
제안서 마감일 전날 기준 10억원 이상 40일, 1억원 이상 20일, 1억원 미만 10일 및 긴급·재공고
10일 규정이 있다. `scripts/build_routed_law_bundles.py`의 chapter-anchored selector와
`tests/test_law_source_selectors.py`가 이 회귀를 검증한다.
