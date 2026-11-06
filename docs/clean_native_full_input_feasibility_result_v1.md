# Native full-input 0-call feasibility result

작성일: 2026-09-22

결론: **24개 카드 + 필요한 metadata/product facts + 모든 제공 문서를
공고당 한 번에 넣는 구조는 채택할 수 없다.** 이는 품질 실험이 아니라
token/admission 진단이다. 모델 호출, v 예측, 점수는 0건이다.

| dev200 | 측정값 |
| --- | ---: |
| 공고 / 제공 문서 / 카드 | 200 / 374 / 24 |
| 14,848-token 한 호출에 적합 | 63건 |
| 예산 초과 | 137건 (68.5%) |
| prompt token 최소 / p95 / 최대 | 10,923 / 35,447 / 37,687 |
| token 총합 / 최대 초과량 | 3,998,310 / 22,839 |
| 모델 호출 | 0 |

가장 짧은 적합 사례에서 문서 전까지의 system+card+metadata+product
고정 입력만 **9,093 tokens**였다. 따라서 같은 14,848 한도에 남는
원문 공간은 약 5,755 tokens이다. overflow 137건을 모두 원문 커버하려면
최소 337 notice-context calls가 필요하지만, 이는 각 초과 공고가 정확히
두 pass로 끝난다는 비현실적인 하한이다. 문서·fragment가 더 크면 calls는
증가한다. batch size로 logical call 수는 줄지 않는다.

실제 rendered system/user/schema를 다음 파일에서 점검했다.

- short complete: `outputs/clean-native-full-input-feasibility-v1/dev200/rendered_inputs/short_complete_PPS-DEV-077.json`
- attachment complete: `outputs/clean-native-full-input-feasibility-v1/dev200/rendered_inputs/attachment_complete_PPS-DEV-130.json`
- largest/overflow: `outputs/clean-native-full-input-feasibility-v1/dev200/rendered_inputs/overflow_PPS-DEV-11.json`

review: 출력 계약은 24개 V와 24개 E이고, e10/e11/e16/e18/e20 공란
제약이 있다. 24개 카드 `prompt_text`만 법률 판단 기준으로 들어가며
법령 원문·사례 corpus는 없다. metadata는 한국어 사실로, 제품은 exact-code
결과 및 `특이사항`으로 들어간다. 공고문→규격서→과업지시서 등 유형 순서의
본문이 원문 그대로 보이고, 위 세 사례에 각각 1/2/3개 문서가 실제로
렌더됐다. 원문을 줄이지 않았기 때문에 대다수 공고가 admission에 실패했다.
v4 금액 scope와 v20/v24 관계의 기존 semantic gap은 그대로 남는다.

따라서 이 draft를 유료 실행하거나 제출물로 패키징하지 않는다. 다음 native
구조는 24개 긴 카드를 매 호출에 반복하고 문서×v-group을 곱하는 방식이
아니라, **문서 전체를 한 번 스캔하는 source-view/fact layer와 item owner별
필요 최소 입력**을 설계해야 한다. source view의 미탐지는 음성 판정이
아니며, 첨부문서에서 근거를 잃지 않는 coverage audit가 먼저다. 기존
reference/frozen 출력 또는 코드는 active 경로에 복사·import하지 않는다.

재현:

```bash
.venv/bin/python scripts/audit_native_full_input.py --input data/raw/open/dev.jsonl.gz --cards data/derived/decision_cards_v31_v4_organizer_definition_resolution.json --products data/derived/competition_products_v1.json --tokenizer-dir /Users/a60157288/.cache/huggingface/hub/models--google--gemma-4-26B-A4B-it/snapshots/4d7ae4984b7db7de8f8457170b3f1a419ee76d52 --budget 14848 --output-dir outputs/clean-native-full-input-feasibility-v1/dev200
```

`audit.json`에는 input/card/product hash, 200개 task hash, exact token 수,
문서 type/id/order/hash ledger 및 rendered sample 경로가 있다.
