# Native product-fact contract N1: label-blind audit

작성일: 2026-09-21

`src/pps_ai/facts/product_codes.py`는 organizer metadata의 대괄호 안 10자리
세부품명번호를 organizer 경쟁제품 CSV index에 **exact code**로만 결합한다.
`특이사항`을 그대로 보존하고 적용 여부는 계산하지 않는다. frozen L41/legacy
import, 이름 유사도, 모델 호출은 없다. 아직 어떤 final owner에도 연결하지 않았다.

| 입력 | 공고 | 제공 문서 | 코드 있는 공고 | 코드 없는 공고 | exact CSV 행 | 불일치 행 | 특이사항 있는 exact 행 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dev | 200 | 374 | 78 | 122 | 18 | 78 | 9 |
| organizer test sample | 10 | 23 | 5 | 5 | 1 | 4 | 0 |

dev 문서 구성은 공고문 201, 규격서 63, 과업지시서 53, 제안요청서 57이다.
모든 비어 있지 않은 코드 입력이 strict parser를 통과했다. supplied 품명과
exact CSV 세부품명이 다른 행은 0건이었다. `코드 없음`과 `CSV 불일치`는
제품 적용 불가 판정이 아니며, 렌더러도 그 결론을 출력하지 않는다.

재현:

```bash
.venv/bin/python scripts/audit_native_product_facts.py --input data/raw/open/dev.jsonl.gz --products data/derived/competition_products_v1.json --output outputs/clean-native-product-facts-n1-v1/dev200/audit.json
.venv/bin/python scripts/audit_native_product_facts.py --input data/raw/open/data/test.jsonl.gz --products data/derived/competition_products_v1.json --output outputs/clean-native-product-facts-n1-v1/test/audit.json
```

품질 우선순위는 frozen C005D dev200의 **오류 분석용** 수치와 분리한다.
제품 관련 가능 항목의 이상적인 단일-item Macro 개선 상한
`(1 - F1_item) / 24`는 v17 `0.015351`, v11/v12 각각 `0.013889`,
v18 `0.009259`, v16 `0.008333` 순이다. 이는 모든 FP/FN을 한 번에
고친다는 비현실적 상한이지 새 코드의 예상 성능이 아니다. 특히 v11/v12는
각각 FN 3건이고 v17은 FP 7건이므로, 이후 item owner 실험에서 정확한
제품 조건 및 판정 경로를 우선 확인할 근거가 된다. 단, 전체 24개 owner의
독립 구현·재측정이 최우선이며 item 보정만으로 새 기준선을 주장하지 않는다.

다음 gate는 이 사실을 v10–v18의 organizer truth condition과 연결하는
item별 semantic-input map이다. 필요성이 확인된 항목에만 렌더링하고,
short/attachment/overflow의 실제 prompt에서 특이사항과 code provenance를
검사한 뒤 유료 실험 여부를 결정한다.
