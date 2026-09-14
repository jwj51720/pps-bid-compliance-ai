# EXP204 one-call v24 role-pair context plan

작성: 2026-09-14, dev / mac

## dev200 concordance audit

Organizer 항목표와 공개 해석상 v24 비교축은 예산·계약방법·지역제한·업종 네 가지다.
dev200 gold-positive 8건을 이 네 축으로 다시 읽었다.

| ID | visible-source에서 설명되는 주된 불일치 |
|---|---|
| PPS-DEV-29 | 배정예산/기초금액 숫자 불일치 |
| PPS-DEV-049 | 네 축에서 명확한 불일치를 재현하지 못함 |
| PPS-DEV-055 | 문서에는 참가 업종이 있으나 metadata 업종제한은 없음 |
| PPS-DEV-057 | 문서 제한경쟁, metadata 일반경쟁 |
| PPS-DEV-062 | 네 축에서 명확한 불일치를 재현하지 못함 |
| PPS-DEV-071 | 문서 지역제한, metadata 지역제한 없음 |
| PPS-DEV-072 | 문서 허용지역 집합과 metadata 지역 집합이 다름 |
| PPS-DEV-079 | 문서와 metadata의 요구 업종 코드/종류가 다름 |

6/8은 동일 역할의 값, 존재 여부, AND/OR 집합 비교로 표현된다. 2/8은 visible input과
official truth condition만으로 설명되지 않으며 dev noise 또는 미공개 annotation 해석일 수 있다.
dev label을 prompt 예시나 Python rule로 옮기지 않는다. matched negative에도 겉보기 불일치가
있으므로 dev-fit threshold를 만들지 않는다.

EXP203의 false positive는 계약의 경쟁 범주와 낙찰 방식 혼합, 지역제한의 존재/집합 해석
오류였다. 즉 네 축 자체보다 축 내부 semantic role을 분리해야 한다.

## 가설과 호출 방식

별도 호출과 장황한 review output을 제거한다. EXP202의 한 번짜리 full-source V/E 호출에
organizer metadata를 다음 대응 역할로 재배열한 compact context를 원문 직전에 추가한다.

1. 문서의 총사업비·예산·기초금액 ↔ `배정예산금액`
2. 문서의 추정가격 ↔ `입찰추정가격` (예산과 교차 비교 금지)
3. 문서의 일반/제한/수의 경쟁 범주 ↔ `계약방법`
4. 문서의 협상/적격심사/규격가격동시/소액견적 등 낙찰자 결정 방식 ↔ `낙찰방법`
5. 참가자의 본점 소재지 허용 집합 ↔ `지역제한여부` + `제한지역코드목록`
6. 참가자에게 요구되는 등록·허가 업종 AND/OR 집합 ↔ `업종제한여부` + `면허업종제한목록`

납품장소·사업장소는 지역제한이 아니고 물품명·과업명은 참가업종이 아니다. 한쪽만 존재하거나
집합의 원소/논리관계가 다르면 불일치 후보이며, 띄어쓰기·분류명 표현 차이는 불일치가 아니다.
이는 label-derived 예시가 아니라 organizer field 의미의 compact mapping이다.

## base와 허용 변경

- base: `configs/config.exp202-corrected-input-direct-fast-panel-c4.yaml`
- candidate: `configs/config.exp204-v24-role-pairs-fast-panel-c4.yaml`
- allowed change: `prompt.mode` 하나
- 고정: cards, metadata/product/anonymization facts, admitted source, V/E schema, tokenizer budget,
  model/provider parameters, overflow merge, evidence, frozen postprocess
- Python은 metadata를 사람이 읽을 수 있게 재배열할 뿐 값 비교나 label을 계산하지 않는다.

## gates

유료 전 preflight, exact admission, 24-item semantic contract, short/attachment/overflow rendered
review, mock, full tests를 통과해야 한다. fast20에서 EXP202보다 macro와 v24 TP/FP가 개선되고
전체 recall이 악화되지 않을 때만 independent holdout20, 그 뒤 dev200으로 간다. target 개선
없이 다른 item의 우연한 변화만 생기면 EXP203처럼 중단한다.

## 2026-09-14 preflight 기록

- one-variable preflight: 통과, effective difference는 `prompt.mode` 하나.
- fast20 exact admission: 17×1 + 2×2 + 1×3 = 24 calls.
- dev200 complete-fact admission: 200 records / 374 documents, omission 0, metadata omission 0,
  over-budget 0; 184×1 + 13×2 + 3×3 = 219 calls.
- semantic-input contract: PPS-DEV-062와 PPS-DEV-194 모두 24/24 통과.
- rendered review: `outputs/exp204-preflight/rendered_inputs/`의 short, attachment, overflow를
  읽었다. system에 경쟁범주/낙찰방식/지역/업종 role separation이 있고, 실제 역할별 metadata
  값이 source 바로 앞에 있다. attachment source와 overflow의 모든 admitted pack에도 fixed
  context가 유지된다. raw metadata JSON, 법령 원문, case corpus는 추가되지 않았다.
