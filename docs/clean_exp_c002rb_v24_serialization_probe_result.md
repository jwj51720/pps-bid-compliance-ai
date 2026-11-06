# EXP-C002RB v24 serialization diagnostic 결과

작성일: 2026-09-21

## 결론

C002RB one-record probe는 whitespace length loop는 제거했지만 semantic structured-output gate를
통과하지 못했다. fast20 전체 실행은 하지 않는다.

- records/logical calls/external calls: 1/1/1
- old C002R response: `finish_reason=length`, completion 1,536
- C002RB response: `finish_reason=stop`, completion 416
- JSON parse: 성공
- local distinct serialization validation: 실패
- reducer fallback: 1
- performance result: 아님

즉 integer amount, axis source enum, 4자리 code pattern, 배열 상한 축소는 무한 whitespace 생성을
막았지만, 모델이 의미적으로 중복 없는 atomic set을 출력하게 만들지는 못했다.

## 실패 원인

### 1. exact duplicate observation

contract 배열에서 동일한 `source_id/role/competition_method` object가 각각 반복됐다. provider의
JSON schema는 배열 길이와 enum은 지켰지만 distinctness를 보장하지 않았고, local parser는 계획대로
중복을 거부했다.

Python이 exact duplicate를 stable deduplicate하는 것은 serialization recovery로 구현할 수 있다.
그러나 이 response에는 중복 외의 semantic 문제가 동시에 있어 dedup만으로 probe를 성공 처리하지
않는다.

### 2. 원 단위 변환 실패

규격서의 `66,000천원`을 model이 integer `66000`으로 출력했다. schema type은 맞지만
`value_won` 의미 계약은 위반했다. 이를 그대로 reducer에 넣으면 metadata 66,000,000원과 거짓
금액 불일치가 된다.

Python이 `천원` keyword를 보고 자동으로 1,000을 곱해 final label을 바꾸는 보정을 이 probe에
사후 추가하지 않는다. unit과 raw numeric value를 별도 typed field로 받아 기계적으로 변환하는
새 schema가 필요하다.

### 3. 경쟁방식 원자값의 operational ambiguity

같은 공고 span에는 소액 수의견적과 제한경쟁 문구가 함께 있었고 model은 `DIRECT`와 `LIMITED`를
둘 다 `COMPETITION_METHOD`로 출력했다. metadata는 수의계약이다. 현재 ANY-different reducer는
LIMITED를 contradiction으로 보지만 이 공고의 v24 label은 0이다.

이는 serialization 문제가 아니라 나라장터 계약방법 필드가 복합 문구 중 어떤 원자를 대표하는지의
operational truth 문제다. 특정 공고를 위해 LIMITED를 무시하지 않는다.

### 4. 제품번호를 업종처럼 해석

model은 10자리 세부품명번호의 앞 네 자리를 4자리 industry code처럼 출력했다. schema pattern은
형식만 제한하며 의미 역할까지 보장하지 못한다. source ID도 실제 industry candidate를 가리켰지만
해당 4자리 code는 그 source에 없어 reducer provenance에서 결국 제거될 값이다. 그래도 atomic
extractor 자체의 역할 안정성이 부족함을 보여준다.

## 해석

C002RB는 다음을 입증했다.

1. whitespace loop는 좁은 numeric/schema contract로 크게 완화할 수 있다.
2. JSON/schema validity만으로 semantic contract가 충족되지는 않는다.
3. v24는 amount unit, 복합 계약방법, 제품번호/업종 역할, organizer annotation 범위를 함께 해결해야
   하며 단순 serialization 수정으로 승격할 수 없다.

probe response와 report:

- `outputs/clean-exp-c002rb-v24-distinct-serialization-probe-v22/response.json`
- `outputs/clean-exp-c002rb-v24-distinct-serialization-probe-v22/run_report.json`

## 결정

- C002RB full fast20: 실행하지 않음
- C002RB holdout/dev200: 실행하지 않음
- v24 multi-observation 계열: organizer operational truth audit 전까지 중단
- canonical baseline: 변경 없음

다음 품질 실험은 현재 dev200에서 FN 6, F1 0.363636인 v3의 qualification/amount relation으로
이동한다. v3의 truth condition은 v24보다 명확하고, F1 0.70 도달 시 이론적 Macro 기여가
`+0.014015`로 크다. C003 dead-output 제거는 runtime/attention ablation으로 남기되 품질 owner
실험과 섞지 않는다.
