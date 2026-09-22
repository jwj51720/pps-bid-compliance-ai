# Native v1 qualification input: 0-call result

작성일: 2026-09-22

결론: **v2 source view는 tokenizer/provenance gate를 통과했지만,
독립 v1 final owner의 품질은 아직 검증하지 않았다.** 유료 모델 호출은
하지 않았다. 후보 미발견이나 U 관측을 0으로 바꾸는 reducer도 없다.

| dev200 audit | v1 광범위 어휘 view | v2 참가자격 연결 view |
| --- | ---: | ---: |
| 제공 공고 / 문서 scan | 200 / 374 | 200 / 374 |
| exact source spans | 1,674 | 971 |
| 14,848-token 1회 admission | 157 | **200** |
| 최대 prompt tokens | 25,843 | **13,370** |
| gold nonempty e1 포함 | 1/1 | 1/1 |
| C005D positive e1 포함 | 7/7 | 7/7 |
| 모델 호출 | 0 | 0 |

v1은 기관·인력·시설 같은 일반 단어를 문서 전체에서 독립 탐색해
43건이 초과했다. v2는 참가/참여 자격·가능 여부 anchor 전후 450자와
문서 도입부 1,000자만 보존한다. 별도 entity window를 없애면서
총 prompt tokens는 710,040 감소했고, 중앙값은 6,870→5,022.5다.
모든 제공 문서는 scan되며 각 span은 원문 offset/hash로 검증된다.
원문 분류어가 없거나 원문 조각에 보이지 않는 조건은 0이라는
뜻이 아니다.

렌더링된 short (`PPS-DEV-179`), attachment (`PPS-DEV-111`),
largest (`PPS-DEV-11`), 양성 근거 예시 (`PPS-DEV-01`, `072`)의
메시지에서 v1 카드의 1/0 조건, 원문 source ID, unknown=U 계약이
각각 한 번씩 나타나는 것을 확인했다. 두 양성 예시에서는 실제
입찰참가자격 조항과 대학만 참여/교육시설 보유 조건이 각각 같은
원문 span 안에 보였다. largest는 13,370 tokens로 한도 아래지만
여유가 1,478 tokens뿐이다. 전체 0 조건/예외가 모든 200개
메시지에서 완결됐다는 증거로 확대하지 않는다.

제한: baseline positive quote coverage는 7개 기존 정답의 부분
회수 검사일 뿐, public 미관측 참가자격 표현의 recall 검사가 아니다.
v1의 `N` 관측이 진짜 0인지 확인하려면 source view 바깥 원문에
제한이 없는지 재검증하는 독립 절차 또는 full-source overflow
계약이 필요하다. 모델이 `U`를 내면 frozen 결과로 돌아가서는
독립 기준선이 아니다. 이 두 문제를 정리하기 전에는 v1을
native final owner라고 부르지 않는다.

산출물: `outputs/clean-native-v1-qualification-view-v1/dev200/audit.json`,
`outputs/clean-native-v1-qualification-view-v2/dev200/audit.json` 및
각 `rendered_inputs/` (ignored; 공고 원문 포함).

재현:

```bash
.venv/bin/python scripts/audit_v1_qualification_view.py --input data/raw/open/dev.jsonl.gz --labels data/raw/open/dev_labels.csv --base-submission outputs/clean-exp-c005d-v19-dev200-promotion-v1/dev200/submission.csv --cards data/derived/decision_cards_v31_v4_organizer_definition_resolution.json --tokenizer-dir /Users/a60157288/.cache/huggingface/hub/models--google--gemma-4-26B-A4B-it/snapshots/4d7ae4984b7db7de8f8457170b3f1a419ee76d52 --budget 14848 --view-version v2 --review-id PPS-DEV-01 --review-id PPS-DEV-072 --output-dir outputs/clean-native-v1-qualification-view-v2/dev200
```
