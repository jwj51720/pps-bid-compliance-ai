# S007 — 제품·기업범위 Python owner 모집단 funnel 감사 계획

상태: zero-call 일반화 진단 계획

## 가설

S001의 v10~v18 deterministic owner는 금액·계약방법 같은 안정적 gate와, 기업범위 lexical hit,
제품 적용성, absence, cross-item veto를 한 label에 결합한다. dev200은 소액수의와 1억원 미만을
과소표집했으므로 dev에서 높은 F1을 보인 결합이 organizer 20,000건에서는 전혀 다른 비율로
발화할 수 있다.

비라벨 데이터로 정답이나 F1을 추정하지 않는다. frozen L41이 실제 사용하는 동일 함수로 각
owner의 중간 predicate를 계산하고, 최종 label 이전의 funnel 발화율과 dev/population 차이만
측정한다. BGE ranking이나 Gemma가 필요한 단계는 빈 ranking으로 대체해 final verdict를 만들지
않고 `unresolved_semantic_stage`로 명시한다.

## 변경 통제

- base config: `experiments/manifests/clean_exp_s001_integrated_v3_v19_v1.json`
- allowed change: `python_owner_population_funnel_audit` 추가만
- LLM/BGE calls: 0
- output: `outputs/clean-exp-s007-python-owner-population-funnel-v1/`
- code source: hash-pinned frozen L41 loader만 사용; legacy import·실행 0

## 감사 대상

공통:

- 금액 band (`<1억`, `1억~2.3억`, `>=2.3억`)
- `complete_observation`
- broad/small 기업범위 hit
- metadata/document exact 경쟁제품 code와 catalog 특이사항 적용
- organizer `조항호내용`의 exact 중기업포함/소기업전용 제한 범주와 lexical scope 결과의 모순
- explicit exception
- r2 deterministic absence의 v10/v11

item funnel:

- v12: same-line 직접생산 hit → metadata noncatalog/특이사항 금액실패
- v13: exact 공고문 제품 → small-only scope → 소액수의·특례 veto
- v14: 금액·scope 진입 → exact product/예외 veto → BGE unresolved
- v16/v18: 제한경쟁·완전관측·no-scope 진입 → exact product와 v10/v11 cross-veto → BGE unresolved
- v17: 1억원 미만·broad-only 진입 → exact product와 v10/v11 cross-veto → BGE unresolved

## 판정 gate

1. dev 200/200, population 20,000/20,000, 모든 문서가 scan된다.
2. frozen archive SHA-256과 함수 소유 module을 결과에 기록한다.
3. API/embedding calls 0.
4. 각 predicate의 dev/pop rate, percentage-point 차이, risk ratio를 기록한다.
5. `abs(rate difference) >= 0.10` 또는 risk ratio가 `[0.67, 1.50]` 밖이면 큰 shift로 표시한다.
6. BGE/LLM 미실행 결과를 final v prediction이나 F1로 명명하지 않는다.
7. 샘플 ID는 strata별 deterministic hash 순서로만 선택하고 dev label을 사용하지 않는다.
8. organizer clause와의 모순은 exact known category만 사용하며, 자유문장 키워드로 법적 label을
   추정하지 않는다.

결과는 owner 제거·승격의 단독 근거가 아니다. 다만 높은 shift와 의미적으로 불완전한 lexical/
absence 단계가 겹치면 해당 Python final owner를 source candidate로 강등할 우선순위를 높인다.
