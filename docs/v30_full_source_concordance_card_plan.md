# v30 — 24개 카드 통합 source-concordance 보수

작성: 2026-09-18, dev / mac

## 가설이 아니라 완결성 보수

`docs/decision_card_source_concordance_audit_20260918.md`의 동일 체크리스트로 v1–v24를
전수 감사한 결과를 한 artifact에 반영한다. 이 작업은 item별 성능 gain을 합산하거나 prompt
기법을 시험하는 실험이 아니다. organizer source와 충돌하거나 필수 조건이 빠진 카드를 그대로
두지 않기 위한 통합 보수다.

## base와 허용 변경

- base artifact: `decision_cards_v29_v2_threshold_scope.json`
- candidate artifact: `decision_cards_v30_full_source_concordance.json`
- allowed changes: v3, v4, v5, v6, v7, v9, v12, v14, v15의 `prompt_text`
- v3/v4는 organizer item-table과 법령 source의 충돌을 숨기지 않고 양쪽 범위와 불명 처리 원칙을
  명시한다.
- v1/v2/v8/v10/v11/v13/v16–v24, output schema, full-source policy,
  metadata/product renderer, merge, provider, Python labels는 변경하지 않는다.

## 항목별 보수

- v3: 국가 1배 상한, 지방 규모·양 1/3 원칙/필요시 최대 1배, 금액 1배 상한,
  정확히 1배의 항목명-법령 충돌.
- v4: 특정기관/특정명칭 실적 금지와 item-table의 고시금액 이상 gate를 동시에 표시.
- v5–v7: 국가·공기업·지방의 공사/물품/용역 전체 지역제한 금액 selector와 최신 지방
  시행규칙 제24조 분기.
- v9: 지방의 생명·건강·안전·보건위생 예외와 실제 동등품 허용을 source 범위로 한정.
- v12: 경쟁제품 및 법 제9조 적용 계약과 일반제품 직접생산 참가제한을 분리하고 vague
  `별도 허용 사유` 제거.
- v14: 제2조의3 우선조달 생략 예외를 고시금액 이상 SME 제한의 허용사유로 사용하지 않음.
- v15: 상한을 국가계약법 제4조제1항 고시금액 2.3억원으로 고정.

## 완료 gate

1. v29→v30 changed-item set이 선언과 정확히 일치.
2. 카드별 필수 source condition 회귀테스트.
3. exact tokenizer dev200 source omission 0.
4. actual-value delivery 200 notices 전체 PASS.
5. short/attachment/overflow와 각 결함 관련 fixture에서 24-item semantic contract PASS.
6. exact fast20 mock, 49열·evidence validation PASS.
7. 전체 pytest PASS.

유료 실행은 위 완결성 검증 후 별도 성능 회귀실험으로만 수행한다.

## 2026-09-18 완료 결과

- v29→v30 changed-item set은 선언한 `v3,v4,v5,v6,v7,v9,v12,v14,v15`와 정확히 일치했다.
- routed-law bundle의 누락 provenance를 보수하고 organizer 원문의 exact substring/hash를
  재생성했다. 국가/지방 profile별 bundle은 20/21/22/22/23 chunks다.
- Gemma tokenizer exact admission, dev200 전체:
  - 200 notices, organizer가 실제 제공한 374 documents.
  - 168건×1 context, 21건×2, 11건×3 = 243 final contexts.
  - 제공 문서 omission 0.
- actual-value delivery audit:
  - 200 notices와 243 contexts 모두 PASS, failure 0.
  - organizer 원천에서 외부 참조문서가 제공되지 않은 10건/10문서는 별도 upstream limitation으로
    기록했다. 파이프라인이 받은 문서를 누락한 사례는 아니다.
- exact rendered semantic-input audit:
  - short `PPS-DEV-062`, attachment `PPS-DEV-046`/`194`, overflow
    `PPS-DEV-143`, 추가 fixture `PPS-DEV-049`에서 v1–v24 모두 PASS.
  - `PPS-DEV-143`은 실제 tokenizer admission과 동일하게 3개 final context로 렌더링됐고,
    각 context마다 전체 card, 필요한 실제 metadata 값, 제품 적용 사실이 존재했다. 공고문 anchor와
    분할 제안요청서를 합쳐 원천 문서 범위를 전부 덮었다.
  - 검토 경로:
    `outputs/card-input-completeness-v30-20260918/semantic-contract-exact/rendered_inputs/`.
- exact fast20 mock은 20 rows를 생성했고 submission validation을 통과했다.
- 전체 회귀테스트 `277 passed`; `git diff --check` PASS.

## 감사 도구 결함과 정정

기존 `audit_candidate_semantic_contract.py`는 preview pipeline에 exact tokenizer를 연결하지 않아
overflow 공고도 하나의 unbounded message로 표시했다. 이 때문에 예전 문서의 “overflow rendered
review 완료”는 source union을 확인했더라도 **실제 실행 context 경계를 검증한 증거가 아니었다**.
도구를 audit version 2로 고쳐 configured Gemma tokenizer로 admission하고 모든 final context를
각각 렌더링하며, 각 context별 card/metadata/CSV 존재를 검사한다. 정정 후 위 5개 fixture가 다시
PASS했다.

## 남은 한계

- v3의 `1배수 이상` 항목명과 법령의 `1배 이내` 등호 경계는 organizer source 내부 충돌이다.
  v30은 충돌과 불명 처리 원칙을 모델에 제공하지만, 임의 정답을 발명하지 않는다.
- 이 문서 작성 뒤 v4는 organizer 법령·dev label·gold evidence·metadata를 함께 대조해
  `고시금액 이상`이 실제 label taxonomy의 gate가 아님을 확인했고 v31에서 제거했다. 상세는
  `docs/v31_v4_organizer_definition_resolution_plan.md`를 따른다.
- exact-code가 없고 공고도 적용제품을 밝히지 않는 notice, SW 부분금액 등 organizer가 제공하지
  않은 notice별 사실은 카드로 복원할 수 없다.
- 이 완료 결과는 **입력 완결성/출처 일치 검증**이다. Gemma의 실제 label 성능 개선이나 public
  성능을 증명하지 않는다. 유료 fast20은 별도 회귀실험이다.
