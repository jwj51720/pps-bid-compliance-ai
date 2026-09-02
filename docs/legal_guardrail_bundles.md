# 법령 보충 규칙 번들 v1

`data/derived/legal_guardrail_profile_group_v1/`은 원문 법령을 통째로 넣는 RAG의 대조 실험용 파생 자료다. 목적은 판정 카드에 적힌 법적 판단 순서 중, 특히 적용 대상·금액 구간·허용 예외·부재탐지의 전제를 짧고 읽기 쉽게 제공하는 것이다.

이는 법령 원문이 아니다. 따라서 이 번들은 법적 근거를 새로 만들거나 원문을 대체하지 않는다. 각 모델 문장은 대회 제공 법령 조각에 연결되며, 연결 정보는 모델이 아니라 `manifest.json`에 보존한다.

## 구성

- 계약 profile: `national`, `local_general`, `local_small`, `local_negotiated`
- v group: `G01_qualification_threshold`, `G02_document_restrictions`, `G03_product_restrictions`, `G04_procedure_and_consistency`
- 총 16개 파일: profile과 v group마다 하나
- 모델 입력: 사람 친화적 보충 문장만 포함한다. source 파일명, selector, SHA-256, profile 이름, routing key는 포함하지 않는다.
- 감사 manifest: 항목별 요약문, source chunk key, 원문 파일·selector·원문/조각 해시를 보존한다.

## 완결성 계약

각 bundle의 `item_chunk_keys`는 `docs/legal_reference_mapping.md`의 item-to-chunk mapping과 동일한 selector를 사용한다. v24는 법령 없는 문서↔metadata 대조형이므로 source chunk가 없다. 국가 profile의 v23과 지방 일반·소액 profile의 v23은 항목표상 적용 불가이므로 `inactive_reason`으로 기록한다.

경쟁제품 여부는 법령 번들에서 추정하지 않는다. 기존의 대회 제공 CSV exact-code lookup만 사용하며, 그 결과는 v10~v18에 필요한 짧은 친화 문맥으로 별도 주입된다.

`data/derived/legal_condition_ledger_v1.json`은 이 계약의 anti-omission audit이다. 16개
profile/group × 6개 v 행(총 96행)에 대해 모델용 요약, source chunk key, 원문 파일·selector·해시와
**선택된 원문 chunk 전체**를 같이 보존한다. v24는 원문 법령이 없는 대조형이며, profile상 적용 불가한
v23은 이유를 명시한다. 따라서 요약을 고칠 때 source selector가 빠지는 일은 자동 검출한다.

이 ledger가 원문을 모두 보관한다고 해서 요약 자체가 자동으로 완결되는 것은 아니다. 다음 review는 각
요약 문장에 적용 전제·예외·수치가 실제로 남았는지 원문과 대조해 완료 표시를 하는 단계다. 완료 전에는
이 요약 번들을 canonical 또는 submission에 사용하지 않는다.

## 실험 계약

EXP041은 EXP038의 4-group, `full_split_merge`, strict evidence, v2 카드, Markdown prompt를 유지하고 fixed context만 이 보충 번들로 교체한다. 따라서 raw-law EXP037과 직접 비교하지 않고, 법령을 넣지 않은 EXP038과 비교한다. 유료 실행 전 모든 16개 조합의 source coverage, manifest hash, exact tokenizer admission, mock output, staged input example을 확인한다.
