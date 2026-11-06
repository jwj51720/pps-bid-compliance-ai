# Clean reference L41 semantic-input contract

작성일: 2026-09-21

이 문서는 frozen L41 baseline의 각 최종 V가 실제로 읽는 입력과 owner를 명시한다. 개선된
정답 계약이 아니라, `dist/reference/submit.zip`의 0.7+ 참고 구조를 변경 없이 측정하기 위한
실행 계약이다. 모든 공고는 strict JSONL ingest와 document hash ledger를 통과하며, 모든
Gemma message는 exact tokenizer로 admission된다.

## 공통 입력 경로

- `record`: organizer가 제공한 ordered documents, `meta`, completeness 필드
- `F1–F6`: frozen FactBuilder가 record/meta/organizer CSV에서 만든 구조화 사실
- `S1–S11,SX`: 모든 제공 문서를 스캔한 뒤 exact source span으로 만든 bounded semantic view
- `R`: organizer 경쟁제품 CSV에 대한 label-blind BGE-M3 top-10
- `r10`: F + S + v3/v4/v9/v15/v19/v20/v21/v22/v23/v24 계약
- `B`: F + S에서 v19 whole-proposition만 판정
- `C24`: exact meta + S11에서 네 대응 필드의 명백한 불일치만 판정

`S`는 전 문서를 스캔하지만 quota/탐지어 기반 view이므로 모든 원문을 보존한다는 뜻은 아니다.
실제 rendered prompt에는 각 span의 source ID, 문서 type/id, heading/offset, 변경 없는 원문이
들어간다. 결정론 owner는 rendered prompt가 아니라 동일 record/F/S/R의 명시 predicate를 읽는다.

## 항목별 owner와 semantic input

| item | final owner | 판정 입력/조건 경로 |
| --- | --- | --- |
| v1 | deterministic.v1 | record 공고문; 기관 한정·선보유 능력·제조사등록 표현 |
| v2 | deterministic.v2 | record 공고문 + F1 계약법/계약방식; 참가효과와 소액수의 예외 |
| v3 | hybrid.r10 | r10의 참가자격 실적 `q`, 규모초과 `x`, source role + Python conjunction |
| v4 | hybrid.r10 | r10의 참가자격 `q`, 특정실적 `r`, 예외 `e`; frozen final은 `q∧r`만 사용 |
| v5 | deterministic.v5 | F1 업무/계약법 + F2 금액 + record 지역 제한 표현 |
| v6 | deterministic.v6 | F1/F2 + record의 기초단위 소재지 제한 + 소액수의 예외 |
| v7 | deterministic.v7 | F1/F2 + record의 복수 광역지역 제한 + 소액수의 예외 |
| v8 | deterministic.v8 | 같은 공고문 참가조항의 실적 gate와 지역 gate + F1 예외 |
| v9 | llm.r10 | r10 S7 중심의 브랜드·모델 강제와 동등품/호환·안전 예외 |
| v10 | deterministic.v10 | F3 exact code + R + record 직접생산 요구/예외 |
| v11 | deterministic.v11 | F3/F6 + R + record 기업범위/예외 부재 |
| v12 | deterministic.v12 | F3 + record 직접생산 참가요건 + CSV 특이사항/금액 적용성 |
| v13 | deterministic.v13 | record 공고문 exact 제품코드·기업 gate + 계약 특례 |
| v14 | deterministic.v14 | F1/F2/F3 + R + record 기업범위/명시 예외 |
| v15 | hybrid.r10 | F2 1억–2.3억 gate + r10 기업범위 판단 |
| v16 | deterministic.v16 | F2/F3/F6 + record 기업범위/예외 완전관측 부재 |
| v17 | deterministic.v17 | F2/F3 + record 중소기업 범위(소기업 한정 아님) |
| v18 | deterministic.v18 | F2/F3/F6 + record 기업범위 요구 완전관측 부재 |
| v19 | llm.B | B whole-proposition: 외부사·이행보장·낙찰 전 의무 + valid source ID |
| v20 | deterministic.r10 | F1 SW 신호 + record 대기업 참여제한 exact phrase 부재 |
| v21 | hybrid.r10 | r10 공동계약 판단 + F1 분담이행 veto/국가 5% force-positive |
| v22 | hybrid.r10 | r10 제출 요구 판단 + record mandatory phrase/발표평가 문맥 |
| v23 | hybrid.r10 | r10 일정 역할·날짜 + F1 계약/낙찰방식 + Python 기간 계산 |
| v24 | llm.C24 | C24 exact meta와 S11의 금액·계약방법·지역·업종 same-field 대조 |

## 확인된 불완전성

- v4는 `e`를 출력받지만 frozen final reducer가 사용하지 않는다.
- 다수 deterministic predicate는 전체 문서가 아니라 공고문만 검색한다.
- r10/B/C24 arm parse failure는 해당 arm 소유 판단을 0으로 만들 수 있다.
- dev200 5건에서 제공 첨부 중 1개가 semantic candidate를 만들지 못했다. 원본 document는
  source ledger와 FactBuilder 입력에는 존재하지만 그 첨부 span은 Gemma view에 없다.

이 네 사항은 이번 baseline의 숨은 오류로 수정하지 않는다. 결과를 얻은 뒤 각 correction을
독립 manifest와 owner 변경으로만 실험한다.
