# EXP-C002R v24 multi-observation fast20 결과

작성일: 2026-09-21

## 결론

EXP-C002R은 C002가 회수하지 못한 v24 양성 1건을 회수해 fast20 Macro positive-F1을
`0.6791666667`에서 `0.6895833333`으로 높였다. 그러나 FP가 4건이고 structured fallback이 1건이라
사전 승격 조건을 통과하지 못했다. holdout20과 dev200은 실행하지 않는다.

- base v24: TP 0 / FP 5 / FN 3 / F1 0
- C002 v24: TP 0 / FP 3 / FN 3 / F1 0
- C002R v24: TP 1 / FP 4 / FN 2 / F1 0.25
- C002R Macro positive-F1: `0.6895833333333333`
- baseline 대비 Macro: `+0.0104166667`
- logical calls: 20
- runtime: 46.122초
- fallback: 1
- non-v24 changed cells: 0
- v24 positive without evidence: 0

사전 gate는 `TP>=1`, `FP<=3`, fallback 0이었다. TP 조건만 충족했고 FP와 fallback 조건을
위반했다. canonical baseline은 계속 `clean-reference-l41-openrouter-dev200-v1`이다.

## 실행 무결성

- manifest preflight: PASS
- dev200 source documents inspected: 374/374
- exact tokenizer admission: 200/200
- fast20 prompt tokens sum/max: 99,692 / 9,762
- fast20 completion tokens sum/max: 15,951 / 1,536
- 20개 ID와 49개 ordered columns: PASS
- v1-v23/e1-e23 baseline equality: PASS
- v24 positive evidence exact substring: PASS

ignored result artifacts:

- `outputs/clean-exp-c002r-v24-multi-observation-v2/fast20/responses/`
- `outputs/clean-exp-c002r-v24-multi-observation-v2/fast20/observations.json`
- `outputs/clean-exp-c002r-v24-multi-observation-v2/fast20/submission.csv`
- `outputs/clean-exp-c002r-v24-multi-observation-v2/fast20/metrics.json`
- `outputs/clean-exp-c002r-v24-multi-observation-v2/fast20/run_report.json`

## 유효했던 구조 변화

지역을 대표 문자열 하나가 아니라 복수 원자 집합으로 보존하면서 C002가 놓친 양성 1건을 정확히
회수했다. metadata 지역 집합과 공고의 bidder-location 집합이 실제로 달랐고, 두 지역 원자는 같은
exact source span으로 검증됐다.

즉 다음 관계 표현은 실제 recall 개선 신호가 있었다.

```text
document_regions = UNION(valid BIDDER_LOCATION observations)
v24_region = document_regions != metadata_regions
```

이는 fast20 한 건의 증거이며 아직 holdout 일반화 증거는 아니다.

## 실패 분해

### 1. 구현이 사전 계획의 4자리 업종코드 계약을 지키지 않았다

한 FP에서 모델은 4자리 업종코드 둘과 10자리 세부품명번호 하나를 모두
`industry_codes`에 넣었다. reducer는 metadata에서 4자리 코드만 추출하면서 모델 output에는 길이
필터를 적용하지 않아 10자리 제품코드를 업종 불일치로 계산했다.

계획서는 이미 “4자리 organizer 업종코드 집합 비교”라고 선언했다. 따라서 이는 새 label rule이
아니라 구현 결함이다. schema와 parser/reducer가 `^[0-9]{4}$`를 강제해야 한다.

### 2. code와 name provenance를 한 boolean으로 묶어 명시적 코드를 버렸다

다른 FP에서는 4자리 코드 세 개가 모두 observation에 있었고 원문에도 존재했다. 그러나 업종명의
띄어쓰기·구두점 표면형 하나가 source text와 exact-normalized match에 실패하자 observation 전체를
invalid로 만들었다. 그 결과 valid code 하나가 집합에서 빠져 거짓 불일치가 만들어졌다.

code와 name은 다음처럼 독립 provenance를 가져야 한다.

```text
valid_codes = codes whose exact digits occur in source
valid_names = names whose normalized surface occurs in source
```

업종코드 비교는 `valid_codes`만 사용해야 한다. name 실패가 code를 무효화하면 안 된다.

이 두 correctness bug를 기존 response에 label-independent하게 고치면 FP 2건이 제거되는 것이
예상되지만, v2 결과를 사후에 바꾸지 않는다. 별도 reducer version과 offline replay로 검증해야 한다.

### 3. observation 중복이 completion budget과 serialization을 소모했다

여러 응답이 같은 `source_id/role/value`를 최대 8회 반복했다. 한 건은 첫 value 앞에서 whitespace
loop를 일으켜 정확히 1,536 completion tokens를 사용하고 `finish_reason=length`로 종료됐다.

이는 provider transport 실패가 아니라 output contract가 distinct observation을 강제하지 못한
serialization 결함이다. 재시도만으로 일반화된 해결을 주장할 수 없다. 다음 schema/prompt에서는
동일 source/role/value 중복을 금지하고 배열 상한을 실제 가능한 distinct 공식 값 수에 맞춰 줄여야
한다.

### 4. 남은 두 FP는 단순 reducer bug라고 볼 수 없다

한 건은 metadata가 지역제한 없음인데 공고의 참가업체 본점 제한이 두 지역으로 명시돼 있었다.
다른 건은 metadata 경쟁방식과 공고의 명시적 제한경쟁 문구가 달랐다. 둘 다 현재 v24 정의
“예산, 계약방법, 지역제한, 업종”에 따르면 명시적 대조 후보다.

정답은 두 건 모두 0이지만, fast20 정답에 맞추기 위해 해당 지역·계약 표현을 예외 처리하지 않는다.
organizer의 v24 annotation operational rule이 현재 항목표보다 좁은지, label noise인지, 다른 source
우선순위가 있는지 organizer-provided examples 전체에서 별도로 입증해야 한다.

### 5. 남은 두 FN은 현재 네 축의 값 비교로 설명되지 않는다

두 FN 중 하나는 공고의 금액·경쟁방식·지역·4자리 업종코드가 metadata와 모두 일치했다. 다른
하나는 명시적 금액·경쟁방식이 일치했고 업종명은 있었지만 source에 4자리 코드가 없어 reducer가
불일치를 만들지 않았다.

따라서 “네 축의 canonical 값 중 하나가 다르면 v24”만으로는 fast20의 모든 positive truth를
표현하지 못한다. 추가 참가자격, 제품/직접생산, 입력 누락, 공고 내부의 문구 우선순위 중 무엇이
실제 annotation 대상인지 source와 organizer specification으로 먼저 확정해야 한다. 정답 사례의
고유 문구를 즉시 새 축으로 승격하지 않는다.

## 다음 단계

계획에 따라 C002R 유료 경로는 여기서 중단한다. 다음 작업은 유료 호출이 아니라 다음 두 단계다.

1. 계획-구현 불일치 두 건을 별도 reducer v2.1로 고치고, 저장된 20개 response를 offline replay해
   예상된 FP 제거와 다른 prediction 불변성을 검증한다.
2. v24 organizer operational truth audit를 전체 dev200 error ledger로 작성한다. label은 평가·분류에만
   쓰고 selector keyword나 final override를 만들지 않는다.

offline replay가 `TP>=1, FP<=3`을 충족하더라도 fallback 1이 남으므로 자동으로 holdout을 실행하지
않는다. distinct serialization contract를 별도 가설로 preflight한 뒤 fast20 전체를 재호출할지
결정한다.
