# EXP-C002 native v24 relation preflight

작성일: 2026-09-21

상태: fast20 paid gate 통과

## 가설

frozen C24가 최종 0/1을 직접 출력하면서 계약방법/낙찰방법, 참가업체 지역/현장, 필수 업종/
과업 분야, 예산/VAT 제외 추정가격을 혼동했다. native module은 네 축의 원자 역할과 관계만
Gemma에서 받고, Python은 `동일 필드 + 동일 범위/시점 + 명시적 값 차이 + exact source`의
AND 식만 계산한다.

## semantic-input contract

| 요소 | organizer source | rendered input |
| --- | --- | --- |
| 적용 대상 | `항목표.json` v24: 예산·계약방법·지역·업종 | system의 네 축 한정 계약 |
| 양성 조건 | 같은 의미·범위·시점의 양쪽 확정값이 다름 | comparable/different typed fields + reducer |
| 0 조건 | 한쪽 미입력, 역할 다름, 부분금액, 현장·납품지, 낙찰방법, 과업분야 | system의 역할 enum과 N/U 계약 |
| meta | `배정예산금액`, `입찰추정가격`, `계약방법`, `지역제한여부/코드`, `업종제한여부/목록` | user의 사람이 읽는 7개 필드 |
| 원문 | 모든 organizer 제공 공고문·첨부 | A/C/R/I source ID, doc type/id, offset, exact span |
| evidence | 양성 axis의 source ID | Python이 원문 substring을 재검증하고 최대 500자 사용 |

raw meta JSON, 내부 status/code key, 법령 원문, 사례 corpus는 넣지 않는다.

## manifest/preflight

- base: `experiments/manifests/reference_l41_openrouter_dev200_v1.json`
- candidate: `experiments/manifests/clean_exp_c002_native_v24_relation_v1.json`
- allowed changes: `layers.views`, `layers.decisions`, `layers.assembly`, `v24_policy`
- undeclared changes: 0
- 다른 23개 final owner: baseline cell read-only
- active native code:
  - `src/pps_ai/views/v24_relation.py`
  - `src/pps_ai/decisions/v24_relation.py`
  - `src/pps_ai/v24_experiment.py`
- legacy import/copy: 없음

## source coverage와 tokenizer admission

- records: 200
- documents inspected: 374/374
- uninspected: 0
- v24 logical calls: 200
- prompt tokens: min 971, max 9,230, sum 943,636
- prompt budget 14,848 초과: 0
- 후보 0건 notice 수: amount 0, contract 6, region 72, industry 4
- 축별 3,500자 상한; 초과 후보는 generic term score 후 document order로 제한하고 coverage에
  omission policy를 기록

최초 8,000자/축 설계는 `PPS-DEV-06` 17,540토큰으로 admission 실패하여 유료 실행 전에
폐기했다. 3,500자/축으로 줄인 뒤 최대 9,230토큰이다.

## rendered-message 사람 검토

- short:
  `outputs/clean-exp-c002-native-v24-relation-v1/dev200/rendered_inputs/short_PPS-DEV-077.json`
- attachment:
  `outputs/clean-exp-c002-native-v24-relation-v1/dev200/rendered_inputs/attachment_PPS-DEV-01.json`
- largest:
  `outputs/clean-exp-c002-native-v24-relation-v1/dev200/rendered_inputs/largest_PPS-DEV-188.json`

검토 결과:

- system에 동일필드 비교, 역할 구분, 중요한 0 조건이 모두 존재한다.
- user에 7개 공식 meta와 exact source ID/type/id/offset/text가 존재한다.
- attachment 표본은 공고문 외 제공 문서 후보를 포함한다.
- largest도 9,230토큰으로 truncation/overflow가 없다.
- selector는 고재현율이라 안전보건 “예산”, 입찰보증금 같은 잡음도 포함한다. 이는 숨기지
  않으며 amount role과 comparable gate가 배제해야 한다.
- 일부 축 후보 없음은 그 축의 `미관측`이지 자동 일치나 자동 음성이 아니다.

## mock

fast20 mock 20행/49열을 생성했고 non-v24 cell 변화는 0, fallback 0이었다. mock은 모든 native
v24를 0으로 만들므로 품질 결과가 아니며 schema/assembly 검증만 의미한다.

## paid gate

fast20만 먼저 실행한다.

- baseline fast20 v24: TP=0, FP=5, FN=3, F1=0
- 통과: TP>=1, FP<=5, parse/fallback=0, 다른 23개 cell 변화=0
- 실패하면 holdout/dev200을 실행하지 않는다.
