# EXP-C002 native v24 relation fast20 결과

작성일: 2026-09-21

## 결론

EXP-C002는 fast20 승격 게이트를 통과하지 못했다. 실행·파싱·provenance 검증은 모두 정상이나,
양성 3건을 하나도 회수하지 못했으므로 holdout20과 dev200을 실행하지 않는다. 이 owner를 clean
L41 기준선에 병합하지 않는다.

- base: `clean-reference-l41-openrouter-dev200-v1`
- candidate: `clean-exp-c002-native-v24-relation-v1`
- cohort: `configs/dev_fast_panel_v1.json`의 20건
- logical calls: 20
- parse/fallback failure: 0
- 다른 v1-v23 cell 변화: 0
- baseline v24: TP 0 / FP 5 / FN 3 / F1 0
- candidate v24: TP 0 / FP 3 / FN 3 / F1 0
- fast20 전체 Macro positive-F1: `0.6791666666666667`로 동일
- runtime: 28.605초

사전 선언한 fast20 최소 조건은 `TP>=1`, `FP<=5`, parse failure 0이었다. FP는 2건 줄었지만
`TP>=1`을 만족하지 못했다.

## 실행 무결성

유료 호출 전 active clean preflight와 실제 rendered input 검토를 완료했다.

- manifest diff는 선언한 `layers.views`, `layers.decisions`, `layers.assembly`, `v24_policy`만 허용했다.
- dev200의 organizer 제공 문서 374/374개를 검사했고 미검사 문서는 0개였다.
- exact tokenizer admission은 200/200건에서 통과했다.
- v24 logical call은 공고당 1회, 총 200회로 계산됐고 overflow는 없었다.
- short, attachment, largest rendered message를 사람이 읽어 raw metadata dump가 없고 exact source
  ID/type/offset/text가 포함됨을 확인했다.
- fast20 결과의 20개 structured response는 모두 `finish_reason=stop`이고 reducer fallback은 0이었다.
- v24 외 23개 항목과 evidence는 baseline output에서 그대로 보존됐으며 변경 cell은 0개였다.

검증된 산출물은 다음 ignored output에 있다.

- `outputs/clean-exp-c002-native-v24-relation-v1/fast20/preflight.json`
- `outputs/clean-exp-c002-native-v24-relation-v1/fast20/responses/`
- `outputs/clean-exp-c002-native-v24-relation-v1/fast20/observations.json`
- `outputs/clean-exp-c002-native-v24-relation-v1/fast20/submission.csv`
- `outputs/clean-exp-c002-native-v24-relation-v1/fast20/metrics.json`
- `outputs/clean-exp-c002-native-v24-relation-v1/fast20/run_report.json`

## 실패 분해

### 1. 한 축당 단일 observation은 복수 후보의 충돌을 표현하지 못한다

현재 schema는 amount/contract/region/industry마다 `document_value`와 `source_id`를 하나만 받는다.
PPS-DEV-062의 계약 후보에는 서로 다른 두 문구가 동시에 존재했지만, 모델은 metadata와 일치하는
후보 하나만 선택했다. 같은 축의 나머지 공식 문구를 보존하거나 서로 대조할 수 없었다.

따라서 이 schema는 “축별 원자 관계”가 아니라 실질적으로 “축별 대표값 하나 선택”이다. v24의
truth condition이 복수 문구 중 어느 하나의 불일치도 찾는 것이라면 다음 식을 표현하지 못한다.

```text
v24_axis = ANY(candidate_j is an official value
               AND comparable(candidate_j, metadata)
               AND different(candidate_j, metadata))
```

이 결함은 프롬프트 문구를 강화하는 것으로 해결되지 않는다. schema가 후보별 판단 배열과
후보 간 역할·우선순위를 표현해야 한다.

### 2. 지역 제한을 문자열 하나로 축약해 집합 차이를 잃었다

PPS-DEV-072의 exact source span에는 metadata보다 넓은 복수 지역이 있었지만 모델의
`document_value`는 metadata와 같은 한 지역만 남겼고 `different=N`을 출력했다. 지역 제한은 단일
문자열 동등성보다 정규화된 집합 관계가 필요하다.

```text
meta_regions = {r1}
document_regions = {r1, r2}
meta_regions != document_regions
```

Python이 지역명을 keyword로 찾아 최종 label을 덮는 방식은 채택하지 않는다. 대신 Gemma가 exact
source에 연결된 복수 원자값을 빠짐없이 구조화하고, organizer가 정의한 동일성에 한해 reducer가
집합을 비교하는 방식을 별도 가설로 검증해야 한다.

### 3. high-recall selector도 표와 표현 변이를 완전히 보존하지 못했다

PPS-DEV-049의 금액 표에서는 역할 header와 숫자 value가 서로 다른 줄에 놓여 selector span이
header만 남겼다. 이 건의 v24 양성 원인을 금액이라고 단정할 근거는 없지만, 현재
`line ± fixed window` 후보가 표의 field-value 결합을 보장하지 않는다는 독립적인 coverage 결함은
확인됐다. 또한 계약 후보가 0개인 공고도 있었다.

향후 view는 label 문구를 추가하는 방식이 아니라 다음 coverage invariant를 가져야 한다.

- field header를 선택하면 인접 cell/value가 같은 source span에 들어간다.
- 같은 축의 모든 후보가 stable candidate ID로 보존된다.
- 후보 0개는 `NOT_FOUND`, 잘림·budget 때문에 보지 못한 경우는 `UNOBSERVED`로 구분된다.

### 4. FP 감소는 유효하지만 승격 근거가 아니다

새 owner는 baseline의 FP 5건 중 4건을 제거했지만 새로운 FP 2건을 만들었다. 즉 FP 집합은 단순
부분집합이 아니며, 보수적 reducer 하나만으로 오류가 단조 감소하지 않았다. 특히 계약방법과
낙찰/협상 방식을 의미적으로 구분하려는 prompt가 일부 공고에서는 유효했지만, 다른 공고에서는
공고의 명시적 표제와 metadata 필드가 어떤 organizer 입력축에 대응하는지 일관되게 정하지 못했다.

## 해석 경계

- fast20 정답을 보고 특정 문구·지역명·업종명을 selector 규칙에 추가하지 않는다.
- 세 FN의 개별 양성 사유를 모두 확정했다고 주장하지 않는다. 현재 결과가 입증한 것은 단일값
  schema와 span coverage가 해당 정답을 표현·회수하기에 불충분하다는 점이다.
- C002는 구조적으로 불완전하므로 prompt-only 수정본을 C002 재실행으로 만들지 않는다.
- holdout20/dev200 미실행은 계획된 승격 규칙에 따른 중단이며 비용 부족이나 runtime 실패가 아니다.

## 다음 결정

계획서의 “실패한 단계는 다음 단계로 자동 진행하지 않는다” 원칙에 따라 여기서 중단한다.
후속 선택지는 서로 섞지 않는다.

1. **C002 후속을 새 가설로 재설계**: 후보별 observation 배열, 지역/업종의 복수 원자값,
   table-aware exact span을 먼저 mock panel에서 입증한 뒤 별도 manifest로 실행한다.
2. **독립 EXP-C003 수행**: r10의 dead output 제거만 검증한다. 이는 v24 개선이 아니라 token/attention
   ablation이므로 C002 변경과 결합하지 않는다.

현재 기준선은 계속 `clean-reference-l41-openrouter-dev200-v1`이다.
