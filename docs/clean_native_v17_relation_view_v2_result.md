# Native v17 relation-view v2: 0-call result

작성일: 2026-09-22

결론: **source admission과 기존 v17 근거 보존은 통과했지만, v17의
실제 구매대상 관계가 전 공고에서 완결됐다는 증거는 아직 없다.**
유료 품질 실험은 시작하지 않았다.

| dev200에서 v17 가격·업무 gate 통과 | full source phase A | relation v1 | relation v2 |
| --- | ---: | ---: | ---: |
| 공고 / 제공 문서 검사 | 106 / 190 | 106 / 190 | 106 / 190 |
| 14,848-token 적합 | 81 | 106 | 106 |
| 최대 prompt tokens | 28,277 | 8,136 | 9,491 |
| exact source 후보 span | 전체 원문 | 356 | 373 |
| gold nonempty e17 근거 | — | 1/1 | 1/1 |
| C005D positive e17 근거 | — | 13/13 | 13/13 |
| 모델 호출 | 0 | 0 | 0 |

v2에서 늘어난 17개 span은 카드에 있는 우선구매·수의·지명계약 및
특정 성능/기술/품질의 적용 예외 표현을 탐색한 결과다. 어떤 ID나
gold label을 규칙에 넣지 않았다. v1 결과는 별도 output에 유지했다.

실제 rendered input은 short, attachment, largest 및 기존 오류/양성
사례에서 export해 읽었다. `PPS-DEV-105`에서는 기업범위 조항과
**이번 계약에 적용한다고 명시한 우선조달 예외**가 같은 source span에
보인다. `PPS-DEV-177`에서는 공고 제목, 직접생산확인 관련 품명코드,
중소기업 참가조건 및 중견기업 참가조항이 분리되지 않고 보인다.
이는 관계를 모델이 판단할 재료가 존재한다는 뜻이지, 그 판정이 맞다는
증거는 아니다. rendered files:

- `outputs/clean-native-v17-relation-view-v2/dev200-review/rendered_inputs/short_complete_PPS-DEV-041.json`
- `outputs/clean-native-v17-relation-view-v2/dev200-review/rendered_inputs/attachment_complete_PPS-DEV-151.json`
- `outputs/clean-native-v17-relation-view-v2/dev200-review/rendered_inputs/largest_PPS-DEV-188.json`
- `outputs/clean-native-v17-relation-view-v2/dev200-review/rendered_inputs/review_PPS-DEV-105_PPS-DEV-105.json`
- `outputs/clean-native-v17-relation-view-v2/dev200-review/rendered_inputs/review_PPS-DEV-177_PPS-DEV-177.json`

남은 semantic gap: 각 문서 첫 1,300자와 기업범위/예외/코드 주변을
포함했더라도, 실제 구매내역·사업내용이 문서 뒤쪽에만 나타나면 그
역할 관계가 빠질 수 있다. 근거 quote recall 14/14로 이 관계의
완결성을 증명할 수 없다. 카드가 요구하는 실제 조달대상 설명의
source role을 추가 검증한 뒤 paid 여부를 결정한다. `NOT_FOUND`는
제품 비적용이나 예외 부재의 확정이 아니다.

재현:

```bash
.venv/bin/python scripts/audit_v17_relation_view.py --input data/raw/open/dev.jsonl.gz --labels data/raw/open/dev_labels.csv --base-submission outputs/clean-exp-c005d-v19-dev200-promotion-v1/dev200/submission.csv --cards data/derived/decision_cards_v31_v4_organizer_definition_resolution.json --products data/derived/competition_products_v1.json --tokenizer-dir /Users/a60157288/.cache/huggingface/hub/models--google--gemma-4-26B-A4B-it/snapshots/4d7ae4984b7db7de8f8457170b3f1a419ee76d52 --budget 14848 --view-version v2 --output-dir outputs/clean-native-v17-relation-view-v2/dev200
```
