# S024 — direct Python owner의 첨부문서 후보 누락 감사

2026-09-23. S023에서 dev F1 포화로 제거 gate를 dev 점수 상승만으로 고를 수 없음을
확인했다. 이번 S024는 반대 방향인 **source coverage의 구조적 결손**을 20,000건에서
무호출로 측정한다. 정책·최종 라벨·제출물은 바꾸지 않는다.

- base: hash-pinned `dist/reference/submit.zip`, S001 manifest의 정확한 SHA-256.
- allowed policy changes: 없음. 같은 frozen direct-owner predicate를 원본 record와
  `원래 첨부 한 건을 진단용 공고문으로 치환한 record`에 적용한다. 치환은 재실행용
  counterfactual이지 제출 입력이나 실제 공고문 provenance를 바꾸지 않는다.
- 대상: v1/v2/v5/v6/v7/v8의 원본 final 1, 각 첨부에서의 final 1, 원본 0에서
  첨부 중 하나가 1이 되는 notice-item pair. 원래 문서 type/doc-id/순서와 SHA-256을
  따로 기록하고, hit 문구는 ignored output에만 둔다.
- source: `data/raw/open/dev.jsonl.gz` 200건 및
  `data/raw/open/train_unlabeled.jsonl.gz` 20,000건의 모든 제공 문서.
- output: `outputs/clean-exp-s024-direct-attachment-coverage-v1/`에 aggregate report와
  hash 고정 manual-review sample. LLM/BGE calls 0.
- 품질 gate: 전체 원본 문서 count, doc type, exact input hash, 기존 S019 원본 final
  count가 모두 일치해야 한다. 일치하지 않으면 분석 무효.

해석 제한: 실제 첨부의 문구가 같은 detector에 걸려도 그 문구가 해당 item의 법적
위반이라는 뜻은 아니다. 또한 첨부와 공고문 사이의 관계가 필요한 v8은 단일 첨부
counterfactual이 recall 하한에 불과하다. S024는 후보 경계만 계수하고 label 1을
추가하지 않는다. 다음에는 hash 고정 사례를 공고문·첨부 전체 문맥에서 source-role로
검토한 뒤, 문서 범위 확대를 각 owner별 별도 ablation으로 판단한다.
