# EXP-C002R v24 multi-observation 계획

작성일: 2026-09-21

## 1. 목적과 기준선

EXP-C002R은 실패한 EXP-C002를 수정 실행하는 것이 아니라, C002 fast20에서 입증된 표현력 결함을
별도 가설로 검증하는 새 clean-room 실험이다.

- canonical base manifest:
  `experiments/manifests/reference_l41_openrouter_dev200_v1.json`
- canonical base output: `outputs/clean-reference-l41-openrouter-dev200-v1/`
- baseline dev200 Macro positive-F1: `0.7796736645420856`
- baseline v24: TP 5 / FP 44 / FN 3 / F1 `0.1754385965`
- 구현 경계: 새 active module은 `src/pps_ai`만 사용한다.
- `legacy/pipeline_v1_20260921/`의 import, 실행, 복사, 수정은 금지한다.
- frozen L41 artifact는 다른 v의 immutable baseline cell을 읽는 기준선일 뿐 새 v24 판단 구현으로
  사용하지 않는다.

## 2. C002에서 새로 확인된 사실

C002는 한 축당 `document_value/source_id` 하나만 출력했다. 따라서 다음 truth condition을 표현하지
못했다.

```text
contradiction(axis) = ANY(
    official_statement_j
    AND same_organizer_field(statement_j, metadata)
    AND normalized_value(statement_j) != normalized_value(metadata)
)
```

fast20에서 실제로 확인된 구조적 결함은 다음 세 가지다.

1. 같은 축에 공식 문구가 여러 개 있어도 대표값 하나만 남아 나머지 후보가 소실됐다.
2. 복수 지역 제한을 단일 문자열로 축약해 집합 차이를 잃었다.
3. 표의 field header와 value가 빈 줄로 분리되면 line/paragraph window가 header만 남겼다.

고유 공고 문구나 정답 ID를 규칙에 추가하지 않는다. 위 세 결함은 label-independent fixture와 전체
dev source-coverage audit로 구현 여부를 검증한다.

## 3. 가설

Gemma가 최종 v24를 직접 고르거나 축별 대표값 하나를 고르게 하지 않는다. 모든 축에서 서로 다른
공식 field statement를 복수 atomic observation으로 구조화하고, Python은 organizer metadata와
동일한 필드라고 typed role이 확정된 observation만 기계적으로 정규화·비교한다.

```text
Gemma:
  exact source candidate
    -> role
    -> canonical atomic value(s)

Python:
  validate source_id and axis
  -> compare only allowed role/meta-field pairs
  -> ANY explicit normalized mismatch
  -> v24
```

Gemma output에는 최종 `y`, `different`, `violation`을 넣지 않는다. Python도 source text keyword를
직접 최종 label로 바꾸지 않는다.

## 4. 허용 변경

Manifest의 `experiment.base_config`는 canonical base manifest를 가리킨다.
`experiment.allowed_policy_changes`는 다음 네 경로만 선언한다.

- `layers.views`
- `layers.decisions`
- `layers.assembly`
- `v24_policy`

유일한 final owner 변경은 다음과 같다.

```text
v24: llm.C24 -> hybrid.native_v24_multi_observation_v2
```

다른 23개 v/e, facts, retrieval, provider parameter, tokenizer budget, generation setting은 고정한다.
다른 v1-v23/e1-e23 cell이 하나라도 달라지면 실험은 무효다.

## 5. 새 source view

새 모듈은 C002 v1 모듈을 수정하지 않고 별도 version으로 추가한다.

```text
src/pps_ai/views/v24_multi_observation.py
```

요구사항:

1. organizer가 제공한 모든 문서를 실제로 순회한다.
2. 금액·계약방식·지역제한·업종제한의 generic axis term으로 high-recall exact span을 만든다.
3. blank-line separated table cell을 고려해 field match 앞뒤의 인접 block을 함께 보존한다.
4. overlapping window를 합쳐 같은 source 문구의 중복만 제거한다.
5. 선택·미선택 후보와 omission reason을 축/문서별로 기록한다.
6. 후보 없음 `NOT_FOUND`와 budget omission `UNOBSERVED`를 구분한다.
7. text는 항상 원문 substring이고 doc ID/type/order/start/end provenance를 유지한다.

Python selector는 `different`, 지역명, 업종명, 정답 사례별 문구로 후보를 순위화하지 않는다.

## 6. observation schema와 reducer

각 축은 `maxItems`가 있는 observation 배열이다. 배열 원소는 반드시 하나의 valid `source_id`를
가리킨다.

```text
amount[]:
  source_id, role, value_won

contract[]:
  source_id, role, competition_method

region[]:
  source_id, role, regions[]

industry[]:
  source_id, role, industry_codes[], industry_names[]
```

역할은 최소한 다음 오염원을 분리한다.

- amount: VAT 포함 총액 / VAT 제외 추정가격 / 부분·단가·실적금액
- contract: 경쟁방식 / 낙찰·협상방식 / 전자·직찰 제출방식
- region: 참가업체 소재지 / 현장·납품지 / 낙찰 후 사무소
- industry: 참가업체 필수 업종·면허 / 과업분야 / 인력자격 / 제품등록

Reducer는 다음 경우만 explicit contradiction으로 인정한다.

- amount: 역할에 대응하는 organizer 숫자와 canonical integer가 다르다.
- contract: `COMPETITION_METHOD`의 canonical enum이 organizer 계약방법의 경쟁방식과 다르다.
- region: `BIDDER_LOCATION` 지역 원자 집합과 organizer 제한지역 집합이 다르거나, organizer가
  제한 없음인데 공식 bidder-location 제한 집합이 존재한다.
- industry: `BIDDER_MANDATORY_INDUSTRY`의 업종코드 집합과 organizer 제한업종 코드 집합이
  명시적으로 다르거나, organizer가 제한 없음인데 공식 필수 업종코드가 존재한다.

문장 의미·역할은 Gemma observation이 소유한다. Python normalization은 숫자, code, 공백·구두점,
집합 비교만 담당한다. 이름만 있고 code가 없는 industry comparison은 자동 양성으로 만들지 않는다.

## 7. semantic-input contract

v24 final rendered message에는 다음이 모두 있어야 한다.

- 적용범위: 모든 공고, 모든 제공 문서
- 1 조건: 공고서의 명시적 공식 값과 동일 organizer input field가 서로 다름
- 핵심 0 조건: 다른 의미 역할, 부분값, 현장 위치, 낙찰방법, 인력/제품 조건, 불명확 값
- metadata: 예산금액, 추정가격, 계약방법, 지역제한 여부/지역, 업종제한 여부/업종
- source: 모든 문서를 순회해 만든 exact candidate span과 provenance
- output: 복수 atomic observation만 존재하고 final v24는 없음

raw metadata JSON, internal status/code array, 법령 원문·요약·RAG corpus는 넣지 않는다.

## 8. 단계별 gate

### 8.1 무과금 fixture와 preflight

- 네 축별 positive/negative role fixture 최소 2쌍
- 한 축 복수 statement 보존 fixture
- blank-line table header/value 결합 fixture
- 지역 복수 원자 집합 fixture
- invalid/cross-axis source rejection fixture
- full dev200 문서 coverage 100%
- exact tokenizer admission 200/200
- short complete, attachment, largest/overflow rendered message 사람 검토
- active preflight의 undeclared policy difference 0

### 8.2 fast20

- baseline: TP 0 / FP 5 / FN 3
- C002: TP 0 / FP 3 / FN 3
- C002R 최소 승격 조건: TP >= 1, FP <= 3, fallback 0
- 다른 23개 v/e 변화 0

`TP=1, FP=3, FN=2`이면 v24 F1은 `2/(2+3+2)=0.285714`, fast20 Macro 개선은
`0.285714/24 = 0.011905`다.

### 8.3 independent holdout20

- baseline v24 positive 0, FP 5
- 최소 조건: FP <= 2, fallback 0, 다른 v/e 변화 0

### 8.4 dev200

- 최소 조건: TP >= 5, FP <= 15, FN <= 3
- 최소 조건 예시 F1: `10/(10+15+3)=0.357143`
- 예상 Macro: `0.779674 + (0.357143-0.175439)/24 = 0.787245`
- 목표 조건: TP >= 6, FP <= 10, FN <= 2
- 목표 예시 F1: `12/(12+10+2)=0.5`
- 목표 Macro: 약 `0.793197`

fast20을 통과하지 못하면 holdout20으로 넘어가지 않는다. holdout20을 통과하지 못하면 dev200을
실행하지 않는다.

## 9. 실행 전 체크리스트

1. fully resolved manifest와 allowed diff를 active preflight로 검증한다.
2. label을 읽지 않는 view/schema/reducer unit test를 통과한다.
3. dev200 source/provenance/token admission audit를 통과한다.
4. 세 종류 rendered message를 직접 읽고 semantic-input contract를 기록한다.
5. fast20 mock이 49열, ID, evidence, 다른 owner 불변성을 통과한다.
6. 유료 실행 직전 manifest가 이 계획의 v2 module을 실제 선택하는지 재확인한다.

이 모든 조건을 통과하기 전에는 EXP-C002R 결과를 생성하지 않는다.
