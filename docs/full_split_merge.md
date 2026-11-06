# Full split-and-merge 입력 모드

## 목적

`prompt.context_strategy: full_split_merge`는 문서 길이가 초과한 공고만
분할하는 `single` 모드와 달리, 공고의 모든 실제 source document를
독립적으로 판정하는 입력 전략이다. 한 호출에서 24개 `v/e`를 모두
생성하고, pass 결과는 항목별 OR로 병합한다.

## 입력 단위와 병합

문서는 `공고문 → 규격서 → 과업지시서 → 제안요청서 → 예외공표서` 순서로,
동일 유형에 여러 파일이 있으면 `doc_id` 순서로 처리한다. 각 pass에는 다음이
들어간다.

- 공통 시스템 프롬프트와 선택된 고정 법령 참고문서
- 해당 공고의 metadata
- 대상 source document 하나
- 대상이 공고문이 아닐 때에는 앞부분 `notice_anchor_chars`만큼의 공고문 앵커

앵커는 추가 판단 근거가 아니라 pass가 같은 공고에 속한다는 최소 문맥이다.
`strict_document_evidence: true`일 때 non-absence positive의 근거문구는 병합 전에
그 pass의 **대상 source document 조각** 안에서 검증한다. 공고문 앵커, metadata,
고정 법령 reference, 다른 문서에서만 발견되는 문구는 positive 근거가 될 수 없으며,
그 경우 해당 pass의 label은 0으로 강등한다. 부재탐지 항목만 evidence 없이 1일 수
있다. 이 항목들은 `absence_detection_strategy: per_pass_and`에서 한 문서라도 필요한
조건을 확인해 0을 내면 최종 0, 모든 문서가 1일 때만 최종 1이 된다.

한 대상 문서가 `max_model_len - output_reserve_tokens`를 넘으면, 시스템 프롬프트,
metadata, 고정 참고문서, 앵커까지 포함한 **최종 Gemma chat template**을 직접
세어 가장 긴 접두 조각을 찾고 `[계속 offset]` 조각으로 이어 보낸다. 법령 참고
문서나 metadata를 잘라서 맞추지 않는다. 이 공통 고정 입력만으로도 예산을 넘으면
명시적으로 실패한다.

병합은 `00 → 0`, `01/10/11 → 1`이다. 둘 이상의 positive가 있으면 고정 문서
순서상 먼저 처리한 pass의 유효 evidence를 유지한다. malformed structured output은
기존 공통 정책대로 개별 pass를 0으로 기록하며, 다른 pass의 positive를 지우지
않는다.

## 설정과 제출 동기화

`config.yaml`에는 허용값이 인라인 `# options:` 주석으로 적혀 있다. 제출 전
`scripts/make_submission.py`는 `context_strategy`를 포함한 prompt 정책이
`submission/runtime_config.json`과 정확히 같지 않으면 zip 생성을 거부한다.
따라서 실험에서 이 모드를 평가해 채택하려면 두 파일의 같은 필드를 함께 바꾼다.
현재 canonical 정책은 EXP-014 결과에 따라 `full_split_merge`, strict document
evidence, absence AND, decision card v2, 경쟁제품 적용성 문맥을 사용한다.
