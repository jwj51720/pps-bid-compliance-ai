# S008/S009 — v16 full-source verifier 결과

실행일: 2026-09-23

상태: **두 micro 모두 의미 gate 실패, dev200 확장 및 submission 승격 기각**

## 공통 preflight

- S001 대비 v16 positive-only route만 추가
- S001 base v16=1: 9 notices
- dev: 12 documents, 121,058/121,058 source characters, 10 contexts
- micro: 6 notices, 14 documents, 153,004/153,004 characters, 9 contexts
- gap/overlap: 0
- exact token max: S008 micro 14,521, dev 14,848
- raw metadata JSON/raw law/internal status: 없음
- v1~v15/v17~v24 owner: S001 불변
- preflight undeclared differences: 0

micro panel은 label-blind source 유형으로 고정했다.

- 실제 broad 입찰참가 제한 2건
- organizer clause만 있고 source 제한이 불명인 2건
- 계약 후 확인서 제출 1건
- 명시적 판로지원 예외 1건

## S008 V-only 결과

- calls: 9
- schema-valid: 9/9
- invalid/retry: 0
- runtime: 13.44초
- prompt/completion tokens: 100,915 / 81
- recorded cost: 0.0119577

의미 결과:

- 실제 broad 제한: 1/2만 v16=0
- metadata-only/no-source: 2/2 v16=1 보존
- post-award: v16=1 보존
- explicit exception: v16=1로 놓침

단일 bit는 어떤 truth-condition 축을 놓쳤는지 검증할 수 없었고 사전 6/6 gate에 실패했다.
S008은 dev200으로 확장하지 않았다.

## S009 관계 관측 결과

S008의 source·카드·metadata·제품·overflow·merge는 고정하고 출력 schema만 applicability,
qualification role+quote, exception+quote로 교체했다.

- calls: 9
- schema-valid: 9/9
- invalid/retry: 0
- runtime: 98.57초
- prompt/completion tokens: 101,004 / 954
- recorded cost: 0.01252172
- notice result: 6/6 v16=0

구조화 결과에서 세 결함을 확인했다.

1. 모델이 organizer `조항호내용`을 실제 공고 원문 qualification quote로 복사했다.
2. 학술연구용역 업종등록 문장을 `BIDDER_BROAD`로 분류했다.
3. `NOT_APPLIES`를 과도하게 선택해 metadata-only와 post-award 사례까지 모두 0으로 축약했다.

parser도 quote가 user message 전체 substring인지만 검사해 metadata 영역과 실제 원문 영역을
구분하지 못했다. 이는 수정해야 할 입력영역 provenance 계약 결함이다. 그러나 이 micro 결과를
보고 broad marker나 reducer veto를 추가하면 동일 6건에 대한 사후 적응이 되므로 S009를 고치며
계속 호출하지 않는다.

## 결정

- S008/S009를 dev200 또는 submission에 통합하지 않는다.
- 18 calls 뒤 같은 micro에 세 번째 prompt/schema variant를 만들지 않는다.
- full-source positive-only verifier라는 topology 자체가 기각된 것은 아니다. 현재 Gemma가 긴 원문과
  metadata를 한 번에 보고 source role을 안정적으로 분리하지 못했다는 결론이다.
- 향후 다른 verifier가 quote를 요구하면 실제 `[실제 공고 원문]` 영역 안의 substring인지 별도로
  검증해야 한다. metadata/card/product 영역의 substring은 source evidence가 아니다.
- 다음 일반화 후보는 새 prompt를 맞추기보다 S005 v3-only revert처럼 이미 정량화된 adaptive
  component 제거 ablation을 우선한다.

ignored artifacts:

- `outputs/clean-exp-s008-v16-full-source-verifier-v1/`
- `outputs/clean-exp-s009-v16-observation-verifier-v1/`
