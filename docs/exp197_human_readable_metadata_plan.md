# EXP197: human-readable metadata code-removal plan

작성: 2026-09-11, dev / mac

## 문제와 가설

EXP192/196의 제품 조건 전달 감사는 `competition_product_context`만 검사했다. 실제 final
rendered message에는 별도 `[나라장터 입력 메타]`의 `세부품명번호목록` 값이 원형대로
들어가 `품명[10자리 세부품명번호]`가 노출됐다. `면허업종제한목록`도 같은 방식으로
`업종명(4자리 업종코드)`를 노출한다. 따라서 이전의 "제품 코드 노출 0" 결론은 검사 범위가
불완전했다.

가설은 메타데이터의 판단 의미를 보존하면서 구현 식별자만 제거하면 입력 정책이 실제 rendered
message에서도 일치한다는 것이다. 제품명·업종명·금액·날짜·Y/N·`null`과 `미입력`의 구분은
그대로 유지한다. 실제 공고 자료 원문은 어떤 문자도 변경하지 않는다. exact code는 Python의
organizer CSV lookup에만 사용하고, 조건부 제품의 친화적 이름·특이사항은 기존 v2 renderer로
전달한다.

## 최소 정책 변경

- base config: `configs/config.exp196-corrected-input-source-first-fast-panel-c4.yaml`
- allowed policy changes: `prompt.metadata_style`만
- 새 값: `official_lines_human_v2`
- 기존 `official_lines`와 과거 실험 출력은 변경하지 않는다.
- source selection, tokenizer admission, cards, organizer semantics, product lookup/context,
  staged topology, merge, evidence, model/provider parameter는 변경하지 않는다.

`official_lines_human_v2`는 다음 두 organizer metadata field에만 적용한다.

- `세부품명번호목록`: 대괄호 안 10자리 세부품명번호 제거
- `면허업종제한목록`: 업종명 뒤의 독립 4자리 업종코드 괄호 제거

다른 필드는 원형을 유지한다. source document 안의 동일 코드는 제거하지 않는다.

## 무료 검증 게이트

1. historical renderer byte-equivalence 및 새 renderer 단위 테스트
2. final과 source-first stage 1의 **전체 rendered user message**에서 organizer metadata code
   leak 검사
3. 조건부 제품 특이사항·제품명 보존 검사
4. exact tokenizer admission과 source coverage/provenance
5. short/attachment/overflow/conditional-product rendered review
6. 24개 v semantic-input contract
7. exact staged mock, 49열/ID/evidence validation
8. preflight에서 변경이 `prompt.metadata_style` 하나인지 확인

무료 게이트를 통과하기 전에는 paid fast20을 실행하지 않는다. fast20 이득이 있을 때에만
independent holdout20, 그 뒤 dev200 순서로 확장한다.
