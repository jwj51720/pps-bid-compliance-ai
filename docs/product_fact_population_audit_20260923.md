# 제품 fact organizer 20,000 모집단 감사

작성일: 2026-09-23

## 결론

dev200에서 통과한 native metadata product parser가 organizer 비라벨 20,000건에서는 18건을
거부했다. 원인은 실제 `세부품명번호목록`에 존재하는 8자리 물품분류번호와 쉼표가 포함된
품명이었다. 이는 dev-only 입력 형식 과적합이다.

`src/pps_ai/facts/product_codes.py`를 다음처럼 보수했다.

- organizer entry의 8자리 또는 10자리 코드를 손실 없이 parse
- 품명 내부 쉼표 보존
- 경쟁제품 CSV exact join은 계속 10자리 index에만 수행
- 8자리 코드는 자동 경쟁/비경쟁으로 판정하지 않고 unmatched source fact로 보존
- malformed 잔여 문자열은 계속 fail-closed

이 변경은 제품 적용 label이나 v10~v18 cell을 만들지 않는다. 이미 제출한 S001은 frozen reference
FactBuilder를 사용하므로 이 parser 수정의 영향을 받지 않는다. 다음 clean native 입력 계약을
모집단 형식에 맞춘 변경이다.

## metadata exact-code coverage

| 항목 | organizer 20,000 |
|---|---:|
| notices with metadata codes | 7,529 |
| notices without metadata codes | 12,471 |
| CSV exact-matched 10-digit rows | 2,123 |
| unmatched 8/10-digit rows | 6,317 |
| exact rows with `특이사항` | 917 |
| applicability labels assigned | 0 |

## 모든 공고문·첨부의 코드 scan

| 항목 | organizer 20,000 |
|---|---:|
| documents scanned | 38,862 |
| 10-digit document mentions | 11,099 |
| CSV exact-matched document mentions | 7,086 |
| exact mentions with `특이사항` | 3,564 |
| distinct metadata exact notice-code pairs | 2,123 |
| distinct document-only exact notice-code pairs | **3,237** |
| all-mention renderer max tokens | **36,521** |

metadata exact match만 사용하면 문서에서만 발견되는 최소 3,237개 notice-code pair를 잃는다.
반대로 모든 mention을 그대로 prompt에 넣으면 일부 공고는 14,848 prompt budget을 크게 넘는다.
따라서 일반화 가능한 제품 입력은 다음 세 층을 분리해야 한다.

1. metadata 8/10자리 code provenance
2. 모든 문서의 exact 10자리 code와 주변 source span
3. CSV `특이사항` 원문 및 실제 구매대상/참가요건/예시 역할의 semantic observation

Python은 1·2의 exact join과 provenance만 소유하고, code 부재·unmatched·특이사항을 제품 적용
label로 바꾸지 않는다. 3은 item별 truth condition과 함께 Gemma가 실제 문서를 보고 판단해야 한다.
token 초과 공고는 code를 임의 삭제하지 말고 실제 조달대상 역할 후보를 source-grounded하게
선택하거나 item별 bounded view를 설계해야 한다.

재현:

```bash
python scripts/audit_native_product_facts.py \
  --input data/raw/open/train_unlabeled.jsonl.gz \
  --products data/derived/competition_products_v1.json \
  --output outputs/clean-native-product-facts-n1-v1/unlabeled20k/audit.json

python scripts/audit_document_product_codes.py \
  --input data/raw/open/train_unlabeled.jsonl.gz \
  --products data/derived/competition_products_v1.json \
  --tokenizer-dir ~/.cache/huggingface/hub/models--google--gemma-4-26B-A4B-it/snapshots/4d7ae4984b7db7de8f8457170b3f1a419ee76d52 \
  --output outputs/clean-native-document-product-codes-v1/unlabeled20k/audit.json
```
