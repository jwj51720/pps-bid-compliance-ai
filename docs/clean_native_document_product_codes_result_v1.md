# Native document product-code facts: 0-call audit

작성일: 2026-09-22

결론: **metadata 코드 조회만으로는 경쟁제품 후보 입력이 완결되지 않는다.**
dev200에서 `meta.세부품명번호목록`의 CSV exact match는 18개 공고-코드쌍인
반면, metadata에는 없지만 공고 원문/첨부문서에 있는 CSV exact match가
**33개 공고의 48개 공고-코드쌍**이었다. 이는 최종 제품 적용 판정이
아니라 추가 source-grounded 후보 발견이다.

| 0-call audit | dev200 | 주최측 test sample |
| --- | ---: | ---: |
| 공고 / 제공 문서 scan | 200 / 374 | 10 / 23 |
| 원문 10자리 코드 언급 | 171 | 2 |
| CSV exact-match 원문 언급 | 105 | 0 |
| 그중 `특이사항`이 있는 언급 | 63 | 0 |
| metadata에 없는 원문 exact-match 공고-코드쌍 | 48 | 0 |
| 모든 언급의 한국어 렌더 최대 token | 2,021 | 229 |
| Gemma calls / Python 적용 라벨 | 0 / 0 | 0 / 0 |

dev exact-match 원문 언급 105개는 공고문 85, 제안요청서 18,
과업지시서 1, 규격서 1에서 발견됐다. `SourceSpan`은 doc ID/type,
offset, 원문 SHA를 검증한다. 모든 10자리 token을 수집하므로 전화번호나
식별번호 같은 비제품 token도 후보에 남을 수 있으나 CSV exact join과
실제 구매대상 판단을 분리했다. 렌더러는 `구매대상인지 참가자격용인지
별도 확인 필요`라고 명시하고 원문의 짧은 문맥과 CSV 특이사항을 제공한다.

후속 실험에서 필요한 최소 관계는 **코드가 실제 조달대상을 가리키는가,
직접생산/등록 참가요건의 품명만 가리키는가, 단순 예시인가**이다.
이를 Python keyword로 최종 라벨화하지 않고 source-only typed observation
또는 직접 원문을 읽는 owner가 판단해야 한다. 코드 부재·CSV 불일치도
비경쟁제품이라는 음성 증명이 아니다. 따라서 48개 발견을 점수 개선으로
환산하거나 즉시 v10–v18 판정에 병합하지 않는다.

재현:

```bash
.venv/bin/python scripts/audit_document_product_codes.py --input data/raw/open/dev.jsonl.gz --products data/derived/competition_products_v1.json --tokenizer-dir /Users/a60157288/.cache/huggingface/hub/models--google--gemma-4-26B-A4B-it/snapshots/4d7ae4984b7db7de8f8457170b3f1a419ee76d52 --output outputs/clean-native-document-product-codes-v1/dev200/audit.json
.venv/bin/python scripts/audit_document_product_codes.py --input data/raw/open/data/test.jsonl.gz --products data/derived/competition_products_v1.json --tokenizer-dir /Users/a60157288/.cache/huggingface/hub/models--google--gemma-4-26B-A4B-it/snapshots/4d7ae4984b7db7de8f8457170b3f1a419ee76d52 --output outputs/clean-native-document-product-codes-v1/test/audit.json
```

ignored report는 원문/제품 index hash, 유형별 건수, notice별 발견 코드 및
token을 담는다. 제품 조건/예외의 semantic-input audit와 실제 rendered
prompt 검토 전에는 유료 호출하지 않는다.
