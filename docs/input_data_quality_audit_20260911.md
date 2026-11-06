# Organizer input data-quality audit

작성: 2026-09-11, dev / mac

## 결론

`scripts/audit_input_data_quality.py`로 organizer JSONL의 record grain, ID, schema, 21개 meta
필드, 문서 유형·본문·NFC, document ID, completeness flag와 `dropped_doc_counts`, dev label join과
evidence를 검사했다. dev·local test sample·20k unlabeled 모두 구조적 오류 0건으로 PASS했다.

다만 organizer가 조립 시 이미 제외했다고 명시한 문서는 별도 upstream missingness다. 이것은
우리 pipeline omission이 아니며 복원할 수 없다. 이후 prompt source-coverage 감사의 분모는
“원래 존재했을 모든 문서”가 아니라 “organizer JSONL에 실제 제공된 문서”임을 명시해야 한다.

## 결과

| 데이터 | 공고 | 고유 ID | 제공 문서 | 빈/NFC 오류 | upstream 탈락 공고 | 탈락 문서 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| dev | 200 | 200 | 374 | 0 / 0 | 10 (5.0%) | 제안요청서 10 |
| local test sample | 10 | 10 | 23 | 0 / 0 | 0 | 없음 |
| train unlabeled | 20,000 | 20,000 | 38,862 | 0 / 0 | 853 (4.265%) | 제안요청서 723, 규격서 96, 과업지시서 66 |

모든 레코드는 공고문이 1개 이상 있고 추출 성공 flag가 true다. 문서 내부 `doc_id` 중복은
0건이다. 입력 배열의 유형 순서가 canonical 순서와 다른 공고는 dev 10건, unlabeled 671건이지만,
shared pipeline은 `공고문 → 규격서 → 과업지시서 → 제안요청서 → 예외공표서`로 정렬하여
admission하므로 데이터 오류로 처리하지 않는다.

dev label은 200행·49열이고 input ID와 정확히 join된다. `v1–v24` invalid cell, 유효한 nonblank
evidence의 원문 substring/NFC/500자 위반, 부재항목 evidence 위반은 모두 0이다. 비부재 positive
중 evidence가 비어 있는 cell은 68개이며, organizer가 제공한 gold의 알려진 불완전성으로
계측하되 입력 schema 오류로 처리하지 않는다.

## 재현

```bash
.venv/bin/python scripts/audit_input_data_quality.py \
  --input data/raw/open/dev.jsonl.gz \
  --labels data/raw/open/dev_labels.csv \
  --output outputs/input_data_quality_20260911/dev.json

.venv/bin/python scripts/audit_input_data_quality.py \
  --input data/raw/open/data/test.jsonl.gz \
  --output outputs/input_data_quality_20260911/test_sample.json

.venv/bin/python scripts/audit_input_data_quality.py \
  --input data/raw/open/train_unlabeled.jsonl.gz \
  --output outputs/input_data_quality_20260911/train_unlabeled.json
```

이 audit의 PASS는 raw ingestion 무결성을 뜻한다. 카드 논리 정확성, 제품 조건 delivery,
tokenizer-admitted prompt coverage, Gemma 판단 정확성은 각각 별도 gate로 검증해야 한다.

후속 rendered-input 감사에서는 raw ingestion과 별개로, 기존 `official_lines`가 coded metadata를
그대로 노출하는 문제를 발견했다. 이는 EXP197 `official_lines_human_v2`에서 수정했으며 결과는
`docs/exp197_human_readable_metadata_result.md`에 기록했다. 따라서 "raw 파일이 정상"과
"모델에게 전달되는 의미 입력이 정상"을 동일한 PASS로 취급하지 않는다.
