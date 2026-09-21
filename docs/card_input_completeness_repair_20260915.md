# 카드·입력 의미 완결성 보수

2026-09-15, dev / mac. 사용자 재지시: 새로운 성능 전략보다 판정에 필요한 정보의 온전한 전달을 우선한다.

> 2026-09-18 정정: 이 문서는 단계별 보수 이력이다. 최신 전수 source 감사, v30 통합 보수,
> exact-tokenizer overflow 재감사 결과는 `docs/decision_card_source_concordance_audit_20260918.md`와
> `docs/v30_full_source_concordance_card_plan.md`를 우선한다.

## 범위와 변경 통제

이 작업은 성능 gain 가설 검증이 아니라 organizer source에 있는 판정 조건의 누락 보수다.
낮은 성능 또는 holdout 양성 부재를 이유로 필요한 기준을 카드에서 계속 생략하지 않는다.
다만 완결성 보수 결과를 성능 개선으로 부르거나 검증 없이 제출 정책으로 승격하지 않는다.

- base: EXP208 / `configs/config.exp208-relation-checklist-after-source-dev200-c4.yaml`의 v10 카드.
- 첫 책임 단위: v11 예외 및 확인 순서만 수정.
- allowed_policy_changes: `prompt.decision_cards_path`만. 다른 v, 출력 schema, merge,
  provider, source coverage, metadata/product renderer는 변경하지 않는다.
- 제품 CSV-only 후보 검색은 사용자 허용을 받았지만 이번 보수에는 구현/선택하지 않는다.
- 기존 asset, config, canonical/submission policy를 보존한다.

## v11 보수 source contract

organizer 판로지원법 원문 56–57행(제7조 제1항)의 경쟁제품 계약방법과 같은 시행령
118–124행(제7조 제1·2항)의 네 특별사유 및 공고/시스템 사유기재가 기준이다.
파일은 `data/raw/open/data/법령패키지/법령/` 아래 판로지원법 및 동명 시행령 TXT이며
mac NFD 파일명은 NFC로 식별한다. exact anchors:

- 법: `중소기업자만을 대상으로 하는 제한경쟁 또는 중소기업자 중에서 지명경쟁`.
- 시행령: `우선구매 대상으로 규정한`, `조합이 추천한`,
  `적격자가 없는 등의 사유로 유찰`, `특정한 기술ㆍ용역이 필요한 경우`.
- 공급 경로: `그 사유를 입찰공고문에 기재하거나` 전자조달 시스템 입력.

카드에는 이 기준을 압축해 넣는다. 원문 법령은 prompt에 별도 주입하지 않는다.
metadata에 상세 예외사유가 없으면 공급되지 않은 사실로 기록하며, 조항명이나 계약방식만으로
예외를 확정하지 않는다. 공고문 및 제공된 모든 첨부가 source scope다.
직접생산 요건과 기업범위/계약방법은 따로 확인하되, 직접생산이 중소기업과 무관하다고 쓰지 않는다.

## 구현 및 검증 산출물

- builder version: `v25_v11_exceptions`.
- asset: `data/derived/decision_cards_v25_v11_exceptions.json`.
- 출력 검토: `outputs/card-input-completeness-v11-20260915/`.
- 24개 item/table 일치, v11 외 변경0, source 조건 렌더링 보존 회귀테스트.
- 이 책임 단위에서는 유료 실행 및 성능 claim을 하지 않는다.

## 전수 보수 완료 조건

24개 v 각각에 적용 전제/1 조건/핵심0·예외/수치·기간/필요 metadata·CSV 사실/원문 범위를
source 및 final rendered span과 연결한다. 상태는 `전달 확인`, `기준 보수 필요`,
`organizer 사실 미공급`, `정의 미해결`로 분리한다. 모델이 틀렸다는 이유로 전달 미확인이라고
쓰지 않으며, 반대로 문자열 전달 PASS를 법적 의미 완결성 PASS로 쓰지도 않는다.

v11만 구현했다고 전수 보수가 완료됐다고 하지 않는다. 이후 v13, v15–v18의 예외·기업범위,
나머지 item의 수치·적용조건을 책임 단위별로 보수하고 마지막에 통합 카드/실제 final 입력을 검증한다.

## v11 책임 단위 검증 결과

`v25_v11_exceptions` asset을 생성했다. 회귀테스트상 v10 base에서 바뀐 항목은 v11 하나뿐이고,
시행령 제7조의 네 특별사유, 실제 사유 확인 경로, 핵심0, 모든 원문 scope와 e11 blank 계약이
rendered card에 남는다.

- preflight: 선언된 `prompt.decision_cards_path` 차이 하나만 존재.
- dev200 exact tokenizer profile: 200 records, 374 supplied documents, omission 0,
  184 one-pass + 16 overflow records, final contexts 219.
- prompt budget: 30,268 tokens; overflow distribution 13×2-pass, 3×3-pass.
- semantic audit fixtures: short complete 062, attachments 194, actual 3-pass overflow 143.
- 세 fixture의 모든 final pass에서 v11 카드와 human-readable product context 존재.
- exact mock: 3 records / 5 final contexts, validation PASS. mock Macro-F1은 품질 결과가 아니다.
- 전체 test suite: 269 passed.

검토 산출물은 `outputs/card-input-completeness-v11-20260915/`의 admission/semantic-contract과
`outputs/exp-321-v11-completeness-card-fast-panel-c4-mock/inputs.jsonl`,
`input_examples.md`, `validation.json`에 있다. semantic audit의 24-item PASS는 기존 contract에
기재된 문자열·metadata·CSV·source delivery 확인이다. v11 이외 카드의 법적 의미가 모두
완결됐다는 뜻이 아니므로, 전수 보수 상태와 혼동하지 않는다.

EXP321은 이 책임 단위의 완결성 diagnostic이다. 유료 성능을 실행하지 않았고 root/submission
정책을 바꾸지 않았다.

## 통합 의미 완결성 후보 v26

과거 item-local 성능 카드가 서로 다른 artifact에 흩어져 있던 문제를 제거하기 위해
`decision_cards_v26_semantic_complete.json`을 만들었다. base v10 위에 organizer source로
이미 감사한 다음 책임 단위를 한 곳에 합쳤다.

- v1 참가자 조직·시설·인력 제한과 법정/이행 조건 구분.
- v2 계약법·기관·업무별 고시금액 숫자와 입찰추정가격 operand.
- v4 특정기관 발주실적·특정유형 실적 제한을 금액 조건과 분리.
- v5/v6/v7 적용 금액, 비교 operand, 지역 역할과 계약방식별 허용 조건.
- v8 실제 참가자격 AND 관계와 평가용 실적, 소액수의/특수기술 허용 결합 구분.
- v11 시행령 제7조 특별사유.
- v12 실제 구매대상↔고시 후보↔특이사항↔직접생산 참가요건 관계.
- v13 별도 지정 경쟁제품과 3개 이상 소기업·소상공인 공동사업 예외.
- v14–v18 금액구간, 정상 기업범위, 제2조의2/제2조의3 주요 예외와 absence 범위.
- v20 실질 SW gate, 사업금액 산정 역할, 20/40/80억원 구간과 상호출자제한기업집단.
- v21 공동계약 방식별 국가 10%/5%, 지방 5%, 분담이행 적용 제외와 허용 조정.

나머지 항목은 base v10의 이미 감사된 문구를 유지한다. 이는 여러 정책을 섞은 성능 ablation이
아니라 **실험에 들어갈 정보를 한 artifact에서 확인하기 위한 candidate**다. 이전 specialist의
성능을 합산한 점수로 보지 않으며, v26 자체의 F1은 아직 없다.

확인된 정보 한계도 숨기지 않는다. 특히 v13의 제7조의2 별도 지정 목록/공동사업 적용 사실은
일반 경쟁제품 CSV 등재만으로 성립하지 않는다. 해당 사실이 organizer 입력이나 실제 공고에
없으면 카드는 불명으로0을 요구한다. 따라서 ‘기준은 카드에 온전히 있음’과 ‘모든 공고에서
외부 적용사실까지 organizer가 공급함’은 별개다. CSV-only BGE 후보 검색도 이 별도 지정·
공동사업 사실을 자동 생성하지 못한다.

`docs/semantic_input_contract_v1.md`도 v4/v7/v11/v13–v18의 오래된 축약·충돌을 같은 source
기준으로 교정했고 v2/v21의 수치·방식별 예외도 보완했다. AGENTS.md의 전체 source scope, 카드 중심 법령 압축, 불명 사실 비추정,
human-readable metadata/CSV 원칙과 충돌하는 새 규칙은 없어 guide 문구는 변경하지 않았다.

anti-omission ledger에도 실제 provenance 누락이 있었다. v11은 판로지원법 제7조만 연결되어
시행령 제7조의 특별사유 source가 없었고, v13은 제7조의2 대신 제7조를 연결했다.
`build_routed_law_bundles.py`의 source map을 고쳐 `sme_decree_7`과
`sme_law_7조의2`의 원문 chunk/hash를 ledger에 보존했다. 이 ledger는 감사용이며 법령 원문을
model prompt에 넣는 변경이 아니다.

### v26 전달 검증

EXP322 config는 EXP202에서 card path만 바꾸며 preflight가 그 한 차이만 확인했다.
`audit_candidate_semantic_contract.py`로 062/194/143을 검사한 결과 24개 item의 카드,
contract상 필요한 human-readable metadata/CSV heading, 제공 source scope가 모두 PASS다.

최종 v2/v21 보수까지 반영한 exact tokenizer 재측정에서 dev200의 organizer 제공 문서는
374개이고 omission은 0이다. 170건은 one-pass, 30건은 overflow이며 최종 context는 237개다.
pass 분포는 170×1, 23×2, 7×3이다. v10보다 상세 카드가 길어져 runtime 비용이 커지는
방향이므로, 이 결과를 성능·제출 정책으로 자동 승격하지 않는다.

최신 exact shared-pipeline mock은 short062 11,577 tokens, attachment194 19,325 tokens,
overflow143의 15,803/30,268/18,675 tokens 3-pass로 실행됐다. 모든 pass에 v2의 계약법·기관별
2.3억/7.1억/5억원 selector와 v21의 공동계약 방식별 10%/5%·조정·적용제외를 포함한 통합
카드가 그대로 존재한다. v4 특정기관 실적, v13 제7조의2, 검체검사 예외, v20 GATE A도
보존됐고 49열 validation이 통과했다. 최종 semantic audit은 062/194/143의 모든 pass와
24개 item에서 PASS다. 전체 회귀테스트는 271 passed다. 최신 산출물은
`outputs/card-input-completeness-v26-20260915/admission_latest.json`,
`outputs/card-input-completeness-v26-20260915/semantic-contract-fixtures-latest/` 및
`outputs/exp-322-semantic-complete-render-recheck-mock/`에 있다.

`audit_semantic_input_matrix.py`는 official-baseline 전용 도구라 EXP322 profile을 거부했다.
후보 final rendered 검사는 목적에 맞는 `audit_candidate_semantic_contract.py` 결과를 사용한다.

### 아직 해결되지 않은 의미

- v3: organizer 항목명은 `1배수 이상`, 국가 시행규칙은 `1배 이내`, 정부 집행기준은 일반적으로
  1/3배 이내·필요시 최대1배라고 한다. 정확히1배인 요구의 label 경계가 source끼리 명확하지 않아
  card는 현재 `1배를 넘는`을 유지한다. 이는 전달 누락이 아니라 정의 미해결이다.
- v13: 별도 지정 목록·공동사업 적용 사실은 일반 경쟁제품 CSV에서 얻을 수 없다. 공고/organizer
  입력에 없으면 적용불명이다.
- 공고가 언급하지만 실제 데이터에 포함되지 않은 외부 첨부의 내용은 pipeline이 복원할 수 없다.

따라서 v26은 지금까지 확인된 기준을 한곳에 모은 **의미 완결성 후보**이지, 모든 공고의 모든
외부 적용사실이 존재한다고 보증하는 artifact가 아니다.

24개 항목별 카드 기준과 notice별 입력 사실을 분리한 최종 상태표는
`docs/v26_card_completeness_matrix_20260915.md`에 둔다. 결론은 카드 기준의 알려진 누락은
v26에 합쳤지만, v3 정의 경계와 organizer가 주지 않은 제품 적용사실은 카드 문구로 만들 수
없다는 것이다.
