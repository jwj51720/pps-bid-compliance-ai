# Native metadata-fact contract N1: label-blind audit

작성일: 2026-09-21

`src/pps_ai/facts/metadata.py`는 카드 v31에서 필요한 주최측 입력을 24개
항목별 field map으로 선택하여 한국어 사실로 렌더링한다. frozen L41/legacy
import, 법률 판단, V label override는 없다. 현재 owner prompt에는 연결하지
않았고 품질 점수를 측정하지 않았다.

| 입력 | 공고 | 매핑 항목 | 렌더 가능 field | field 누락 오류 | 지역/업종 flag–목록 모순 |
| --- | ---: | ---: | ---: | ---: | ---: |
| dev | 200 | 24 | 16 | 0 | 0 |
| 주최측 test sample | 10 | 24 | 16 | 0 | 0 |

dev에서는 계약법·업무구분·소관구분·입찰추정가격·배정예산금액·계약방법·
낙찰방법·공고일·지역/업종 flag가 각각 200/200 제공됐다. 지역 목록 87,
업종 목록 122는 해당 flag가 Y인 공고에만 있었고, flag/목록 불일치는
없었다. 긴급공고 입력은 62/200, 공동도급 구성방식은 41/200 제공됐다.
`정보화사업여부`는 200건 모두 `미입력`이므로 v20의 실질 SW 여부를 이
필드로 판단할 수 없다. null/미입력은 `확인되지 않음`으로 렌더링하며
`아니오`로 바꾸지 않는다.

렌더러가 보존하는 구별은 입찰추정가격 ≠ 배정예산금액, 계약 경쟁방식 ≠
낙찰방식, 지역/업종 flag ≠ 목록이다. 내부 `등록지역:r...`은 광역·기초
한국어 설명으로 바꾸되 세부 시군구를 만들지 않는다. 업종 목록은 이름·
4자리 식별번호 대응과 AND/OR 관계를 보존하되 raw 코드 배열 형태는 쓰지 않는다.

**남은 semantic-input gap:** field 존재/렌더 성공은 24개 판정의 완결성이
아니다. v24의 업종코드 사실은 이제 렌더되지만 실제 공고 원문의 대응
업종·역할을 찾아 같은 필드끼리 대조하는 경로는 아직 없다. v20 사업금액의
VAT·분담분/연평균은 원문에서 확인해야
하며 `정보화사업여부`는 전부 미입력이다. v5–v7의 지방 기관별 기준은
`소관구분`만으로 실제 적용을 확정할 수 없다. v23의 제안서 마감·설명회
날짜는 원문과 역할을 대조해야 한다. v4 항목명 금액범위와 카드 본문의
금액 독립성 충돌도 별도 organizer-source 검토 없이 확정하지 않는다.
이 gap이 해소되기 전에는 native final prompt를 `입력 완결`이라고
부르거나 유료 실행하지 않는다.

재현:

```bash
.venv/bin/python scripts/audit_native_metadata_facts.py --input data/raw/open/dev.jsonl.gz --output outputs/clean-native-metadata-facts-n1-v1/dev200/audit.json
.venv/bin/python scripts/audit_native_metadata_facts.py --input data/raw/open/data/test.jsonl.gz --output outputs/clean-native-metadata-facts-n1-v1/test/audit.json
```

ignored report에는 각 필드 제공/미제공 및 item별 **모든 매핑 필드 제공**
공고 수가 있다. 후자는 조건부 미제공이 정상이거나 원문 사실이 필요한
경우까지 센 단순 field 집계이며 item semantic completeness가 아니다.
