# Native v17 relation-view v3: 0-call result

작성일: 2026-09-22

결론: **v3는 유료 실험 gate를 통과하지 못했다.** 구매대상 heading의
source-only window를 더하자 정확한 원문 근거 14/14개는 보존됐지만,
106개 대상 공고 중 2개가 14,848-token 예산을 초과했다. 이 결과는
모델 품질 또는 v17 F1의 결과가 아니다. v3를 현재 판정 owner나
제출 정책으로 승격하지 않는다.

| dev200 v17 가격·업무 gate 통과 | v2 | v3 |
| --- | ---: | ---: |
| 검사 공고 / 제공 문서 | 106 / 190 | 106 / 190 |
| 1회 tokenizer admission | 106 | 104 |
| 최대 prompt tokens | 9,491 | 15,535 |
| 정확한 source span | 373 | 465 |
| gold nonempty e17 포함 | 1/1 | 1/1 |
| C005D positive e17 포함 | 13/13 | 13/13 |
| 모델 호출 | 0 | 0 |

v3는 99개 공고에서 구매대상 탐색어 625건을 찾았고, 구매대상
범주가 포함된 병합 span은 298개다. v2 대비 총 prompt token 증분은
100,880, 공고당 중앙값은 146.5, 최대는 9,427이다. 초과 공고 두
건은 각각 15,535/15,117 tokens였다. 그 문서들에서는 반복되는
`공고명`, `과업내용`, `사업내용`이 특히 많았다. heading 출현을
구매대상 사실 자체로 해석하지 않았고, 중복되었다는 이유만으로
후속 occurrence를 임의로 버리지 않았다.

렌더링된 system/user 메시지의 앞부분과 source marker, token을
short complete, attachment complete, overflow, 기존 양성/오류
사례에서 확인했다. 다섯 메시지 모두 v17 카드·필요 metadata·CSV
대조·source-grounded 원문 조각을 포함한다. overflow는 tokenizer가
실제로 한도를 넘겼다. 전체 구매대상 역할의 semantic completeness는
이번 0-call audit로 증명되지 않았으므로 paid prompt 실험은 보류한다.

기록: `outputs/clean-native-v17-relation-view-v3/dev200/audit.json` 및
같은 경로의 `rendered_inputs/` (ignored, raw 공고 내용 포함).

다음 후보는 구매대상 heading 반복을 근거 없이 잘라내는 방식이
아니다. 우선 해당 span이 실제 구매대상 역할 관계를 더해 주는지
source-only로 검토하고, 필요하다면 exact tokenizer admission을
보장하는 notice-level overflow 설계를 별도 계획·mock으로 검증한다.

재현:

```bash
.venv/bin/python scripts/audit_v17_relation_view.py --input data/raw/open/dev.jsonl.gz --labels data/raw/open/dev_labels.csv --base-submission outputs/clean-exp-c005d-v19-dev200-promotion-v1/dev200/submission.csv --cards data/derived/decision_cards_v31_v4_organizer_definition_resolution.json --products data/derived/competition_products_v1.json --tokenizer-dir /Users/a60157288/.cache/huggingface/hub/models--google--gemma-4-26B-A4B-it/snapshots/4d7ae4984b7db7de8f8457170b3f1a419ee76d52 --budget 14848 --view-version v3 --review-id PPS-DEV-053 --review-id PPS-DEV-177 --output-dir outputs/clean-native-v17-relation-view-v3/dev200
```
