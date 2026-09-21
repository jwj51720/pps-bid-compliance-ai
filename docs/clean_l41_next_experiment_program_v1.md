# Clean L41 후속 실험 프로그램 v1

작성일: 2026-09-21

기준선: `clean-reference-l41-openrouter-dev200-v1`

- dev200 Macro positive-F1: `0.7796736645420856`
- fast20: `0.6791666666666667`
- holdout20: `0.3888888888888889`
- 공고당 logical calls: 3 (`r10`, `B19`, `C24`)
- 기준 manifest:
  `experiments/manifests/reference_l41_openrouter_dev200_v1.json`
- 결과 문서: `docs/clean_reference_l41_dev200_result.md`

## 1. 불변 경계

1. `legacy/pipeline_v1_20260921/`의 어떤 파일도 import, 실행, 복사, 수정하지 않는다.
2. 후속 구현은 `src/pps_ai` 아래의 새 native module만 사용한다.
3. `dist/reference/submit.zip`은 hash-pinned baseline oracle로만 남긴다. 새 판단 코드를 그 ZIP에
   삽입하거나 embedded source를 복사하지 않는다.
4. 한 실험은 final owner 하나 또는 transport/serialization 하나만 바꾼다.
5. 다른 23개 항목의 final cell은 byte-equivalent여야 한다. 다르면 실험 무효다.
6. 결과를 만들기 위해 dev label 문구를 keyword, code list, threshold에 직접 넣지 않는다.
7. Python selector는 고재현율 관측을 만들고, 누락·coverage를 명시한다. selector 미탐지를
   곧바로 사실 부재로 바꾸지 않는다.
8. Python final predicate는 organizer specification으로 완전히 표현 가능한 truth condition에만
   사용한다. 문장 역할·같은 요구의 연결·예외 의미는 구조화된 Gemma observation으로 받는다.
9. 모든 새 manifest는 fully resolved이며 `base_manifest`, `allowed_policy_changes`, owner matrix,
   logical call 식을 선언한다.
10. fast20 → holdout20 → dev200 순서를 지킨다. 단, transport-only 복구는 기존 실패 건만 재생해
    semantic label 변화 여부를 먼저 검사할 수 있다.

## 2. 수학적 우선순위

전체 metric은 24개 항목 F1의 산술평균이다.

```text
M = (Σ F1_i) / 24
ΔM = (F1_new(v) - F1_base(v)) / 24
```

따라서 다른 항목이 고정되어 있을 때 v24 개선의 이론적 효과는 다음과 같다.

| v24 목표 F1 | v24 개선폭 | 예상 dev200 Macro |
| ---: | ---: | ---: |
| 0.50 | +0.324561 | 0.793197 |
| 0.70 | +0.524561 | 0.801530 |
| 1.00 | +0.824561 | 0.814030 |

현재 주요 저성능 항목을 각각 F1 0.70까지 독립적으로 올린다고 가정한 상한 기여는 다음과 같다.

| item | baseline F1 | TP/FP/FN | F1=0.70일 때 ΔMacro |
| --- | ---: | --- | ---: |
| v24 | 0.175439 | 5/44/3 | +0.021857 |
| v3 | 0.363636 | 2/1/6 | +0.014015 |
| v9 | 0.428571 | 3/5/3 | +0.011310 |
| v19 | 0.476190 | 5/10/1 | +0.009325 |
| v4 | 0.533333 | 4/5/2 | +0.006944 |

다섯 항목을 모두 0.70으로 만들고 다른 항목이 완전히 고정된 이상적 dev Macro는 약 `0.8431`이다.
이는 보장이 아니라 실험 비용과 기대효과를 정렬하기 위한 산술 기준이다.

우선순위는 `기대 ΔMacro × 결함의 구조적 확실성 ÷ 변경 위험`으로 정한다.

1. C24 serialization recovery: 점수보다 실행 무결성, 의미 변경 없음
2. v24 atomic relation owner: 최대 기대 ΔMacro, 44 FP
3. v3 relation/provenance: 6 FN, truth condition이 원자 관계식에 적합
4. v19 requirement-instance relation: 10 FP
5. v9 target-role relation: 첨부 source coverage와 결합 필요
6. v4 exception reducer: 코드 결함은 확실하지만 `e` 품질을 먼저 검증해야 함

## 3. EXP-C001: C24 serialization-only recovery

### 가설

C24의 9개 `finish_reason=length`는 법률판정 실패가 아니라 JSON value 앞 whitespace가 1,536
completion tokens를 소모한 serialization 실패다. 동일 prompt, 동일 schema, 동일 generation
parameter로 malformed/length 응답만 한 번 재시도하면 의미 정책을 바꾸지 않고 coverage를
600/600 valid로 만들 수 있다.

### base와 허용 변경

- base manifest: `reference_l41_openrouter_dev200_v1.json`
- base output: `outputs/clean-reference-l41-openrouter-dev200-v1/`
- allowed changes:
  - `runtime.invalid_structured_response_retry: 0 -> 1`
  - 실패 response checkpoint를 성공 response로 대체하지 않고 attempt ledger에 append
- 금지: prompt, schema, max tokens, owner, source view, reducer 변경

### 성공 조건

- 대상 9건 모두 parse-valid 또는 남은 실패를 명시
- 기존 정상 591응답 재호출 0
- 재시도 전후 정상 응답과 v1-v23 완전 동일
- v24 변화는 복구된 9건에서만 허용
- retry logical calls `<=9`

이 실험은 품질 후보가 아니라 runtime correctness 실험이다. 결과가 좋아도 별도 v24 semantic
개선으로 부르지 않는다.

## 4. EXP-C002: native v24 atomic relation

### 가설

현재 C24의 직접 0/1 판정은 계약방법/낙찰방법, 참가업체 지역/현장 지역, 필수 업종/과업 분야,
예산/VAT 제외 추정가격의 역할을 혼동한다. Gemma가 각 축의 원자값·역할·source를 추출하고,
새 Python reducer가 **동일 필드 양쪽 확정값**만 비교하면 recall을 유지하면서 FP를 줄일 수 있다.

### 새 native module

```text
src/pps_ai/views/v24_relation.py
src/pps_ai/decisions/v24_relation.py
src/pps_ai/assembly/replacement.py
```

legacy와 frozen embedded module을 import하지 않는다. baseline과 공통인 것은 immutable
`NoticeRecord`, `SourceSpan`, tokenizer/runtime interface뿐이다.

### observation schema

각 축은 다음을 출력한다.

```text
axis
meta_state/value
document_state/value
document_role
scope
time_role
source_ids[]
relation_candidate = SAME / DIFFERENT / NOT_COMPARABLE / UNKNOWN
```

Python reducer는 다음 조건을 모두 만족할 때만 그 축을 `EXPLICIT_CONTRADICTION`으로 인정한다.

```text
meta_state = PRESENT
AND document_state = PRESENT
AND semantic_field_same = true
AND scope_same = true
AND time_role_same = true
AND normalized_value_different = true
AND valid SourceSpan exists
```

최종식:

```text
v24 = ANY(axis == EXPLICIT_CONTRADICTION)
```

Gemma의 최종 `y`는 받지 않는다. Python은 문장 역할을 keyword만으로 확정하지 않고 Gemma가
출력한 typed observation과 exact source를 검증한 뒤 명시식만 계산한다.

### source coverage

- 모든 제공 문서를 스캔한다.
- 금액·계약·지역·업종별 high-recall candidate span을 독립 구성한다.
- 각 문서별 inspected/selected/omitted reason을 기록한다.
- 후보가 없다는 사실은 `NOT_FOUND`, 문서 미관측은 `UNOBSERVED`로 구분한다.
- 제공 문서가 있는데 어떤 축에도 inspect 기록이 없으면 paid run 금지다.

### allowed changes

- final owner: `v24 llm.C24 -> hybrid.native_v24_relation_v1`
- v24 전용 source view, prompt, schema, reducer
- 다른 owner·facts·retrieval·evidence·provider parameter는 고정
- 공고당 logical calls는 3으로 유지

### 단계별 gate

1. unit fixtures: 계약방법/낙찰방법, 지역/현장, 업종/과업, budget/estimate 최소 2쌍씩
2. dev200 label-blind rendered-input audit
3. fast20 실행
   - baseline v24: TP=0, FP=5, FN=3
   - 최소 조건: TP>=1, FP<=5, parse failure=0
4. holdout20 실행
   - baseline v24: positive 0, FP=5
   - 최소 조건: FP<=2, 다른 v 완전 동일
5. dev200 실행
   - 최소 조건: TP>=5(현재 recall 유지), FP<=22(최소 절반 감소), FN<=3
   - 목표 조건: TP>=5, FP<=10, FN<=3

최소 조건의 보수적 예시 `TP=5, FP=22, FN=3`이면 v24 F1은 `10/35=0.285714`, 전체 Macro는
약 `0.784269`이다. 목표 예시 `TP=5, FP=10, FN=3`이면 v24 F1은 `10/23=0.434783`, 전체
Macro는 약 `0.790480`이다.

## 5. EXP-C003: r10 dead-output removal

### 가설

r10이 출력하는 v19·v20·v24는 final owner가 각각 B19·Python·C24라 사용되지 않는다. 세 출력을
schema와 card에서 제거하면 logical calls를 늘리지 않고 prompt/completion과 attention 간섭을 줄일
수 있다.

- owner 변화 없음
- r10 output: 10개 → 7개(v3,v4,v9,v15,v21,v22,v23)
- B19와 v24 owner는 그대로
- 모든 deterministic output 고정
- 별도 실행하며 EXP-C002와 결합하지 않는다.

성공 조건은 r10 parse failure 0, token 감소, v3/v4/v9/v15/v21/v22/v23의 fast/holdout 성능
비열화다. 이 실험은 C002 이후에 한다.

## 6. 후속 item 실험

### v3

단일 `id`를 없애고 qualification source와 amount/scale source를 분리한다. Python은
`qualification=Y AND required_amount>=budget OR required_scale>current_scale/3`만 계산한다.

### v19

문서 전체에서 requirement instance를 복수 추출한다. issuer/content/deadline/mandatory가 같은
요구에 연결된 경우만 양성으로 합성한다. 서로 다른 서류의 속성을 join하지 않는다.

### v9

모델명 후보마다 target role을 `NEW_PURCHASE / EXISTING_ENVIRONMENT / EXAMPLE / UNKNOWN`으로
분리하고 mandatory/equivalent/compatibility를 typed observation으로 받는다. 규격서·과업지시서
coverage가 없으면 negative를 확정하지 않는다.

### v4

현재 reducer가 `e`를 무시하는 결함은 확인됐지만 즉시 `q AND r AND NOT e`로 바꾸지 않는다.
먼저 모든 v4 오류에서 `e`가 같은 자격조항의 실질 예외인지 source join 정확도를 측정한다.

## 7. 산출물 계약

각 실험은 독립 output 아래에 다음을 남긴다.

```text
resolved_manifest.json
preflight.json
source_coverage.json
rendered_inputs/{short,attachment,largest,error-panel}.json
responses/attempt_*.json
observations.jsonl
writer_trace.jsonl
submission.csv
metrics.json
run_report.json
result.md
```

필수 report:

- config/reference/input/asset/task hash
- logical calls와 retries를 분리한 수
- prompt/completion token sum/max/p95
- parse/length/fallback count
- 변경 owner의 TP/FP/FN/precision/recall/F1
- 나머지 23개 final cell equality
- evidence substring validity와 positive-without-evidence
- fast/holdout/dev200의 단계별 결론

## 8. 즉시 실행 순서

1. 이 계획을 커밋한다.
2. 새 active code에 append-only response attempt ledger와 invalid-response retry를 구현한다.
3. EXP-C001 manifest, tests, 9건 exact replay를 실행하고 결과를 커밋한다.
4. v24 error ledger를 네 축별로 생성하되 label은 평가에만 사용하고 extractor rule 생성에는
   직접 사용하지 않는다.
5. EXP-C002의 native view/schema/reducer를 구현하고 mock/rendered audit를 통과시킨다.
6. fast20, holdout20 gate를 통과한 경우에만 dev200을 실행한다.

실패한 단계는 그대로 기록하고 다음 단계로 자동 진행하지 않는다.
