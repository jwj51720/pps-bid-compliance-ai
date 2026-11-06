# Native v17 product-role phase A: 0-call admission result

작성일: 2026-09-22

결론: **full-source 단일 v17 observation을 이대로 유료 실행하지 않는다.**
가격·업무유형의 명시적 gate를 통과한 dev200 공고 106건 중 25건이
14,848-token 한도를 넘는다. 나머지 81건만 실행하면 item score를
왜곡하므로 fast20/holdout/dev200 품질 실험은 보류한다.

| dev200 0-call phase A | 결과 |
| --- | ---: |
| 원본 공고 / v17 적용 가능성 gate 통과 | 200 / 106 |
| gate 통과 공고의 제공 문서 | 190 |
| 한 호출 적합 / 초과 | 81 / 25 |
| prompt token 최소 / 최대 / 합계 | 2,882 / 28,277 / 1,138,413 |
| Gemma calls / v17 labels produced | 0 / 0 |

이 prompt는 v17 카드 v31, item-scoped metadata, metadata 코드 사실,
문서 10자리 코드+CSV `특이사항`+원문 문맥, **모든 제공 원문**을 읽게
구성했다. `product=G/C/U`, `enterprise=M/S/N/U`, `exception=Y/N/U`
세 축을 구분하며 최종 라벨은 모델이 출력하지 않는다. Python도 코드의
역할·특이사항 적용성을 label rule로 판단하지 않는다. 메타데이터 코드
부재는 비경쟁제품 증명이 아니라고 prompt에 명시했다.

실제 rendered system/user/schema를 다음에서 검토했다.

- short complete: `outputs/clean-native-v17-product-role-phase-a-v1/dev200/rendered_inputs/short_complete_PPS-DEV-077.json`
- attachment complete: `outputs/clean-native-v17-product-role-phase-a-v1/dev200/rendered_inputs/attachment_complete_PPS-DEV-130.json`
- overflow: `outputs/clean-native-v17-product-role-phase-a-v1/dev200/rendered_inputs/overflow_PPS-DEV-27.json`

review: 카드·금액·방식·제품 행의 역할 경고와 원문이 분리돼 보인다.
attachment 예시의 공고문과 과업지시서가 모두 포함되며, overflow 예시의
공고문·과업지시서·제안요청서도 원문을 자르지 않고 들어가 있다.
token 초과가 감지됐기 때문에 해당 메시지는 모델에 보내지 않는다.
단일-item card로 줄여도 전체 원문 문제가 남는다는 것이 이번 결론이다.

다음 단계는 v17의 실제 구매대상/기업범위/적용 예외 관계를 훼손하지 않는
source context를 별도로 설계해 25건의 overflow까지 수용하는 것이다.
문서별 OR로 제품 적용성을 합치거나 누락 문서를 0으로 처리하지 않는다.
이 단계에서도 다른 23개 item owner와 독립 기준선은 변경되지 않았다.

재현:

```bash
.venv/bin/python scripts/audit_v17_full_source.py --input data/raw/open/dev.jsonl.gz --cards data/derived/decision_cards_v31_v4_organizer_definition_resolution.json --products data/derived/competition_products_v1.json --tokenizer-dir /Users/a60157288/.cache/huggingface/hub/models--google--gemma-4-26B-A4B-it/snapshots/4d7ae4984b7db7de8f8457170b3f1a419ee76d52 --budget 14848 --output-dir outputs/clean-native-v17-product-role-phase-a-v1/dev200
```

ignored audit에는 input/card/product hashes, exact task hashes, token 분포,
렌더 경로, 문서 유형별 개수가 있다.
