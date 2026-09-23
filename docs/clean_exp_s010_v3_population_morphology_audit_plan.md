# S010 — v3 source-view 모집단 형태 감사 계획

상태: zero-call 일반화 진단 계획

## 질문과 가설

S001의 v3 전문경로는 dev200에서 61/200건(30.5%)에 호출됐지만 organizer 비라벨
20,000건에서는 20.42%만 호출된다. 마지막 `AGGREGATE` 허용은 알려진 dev FN 한 건을 본 뒤
선택되어 정확히 그 한 셀을 고쳤다. 그러나 이 사실만으로 v3 source view 전체를 버려야 하는지,
마지막 reducer만 과적합인지 구분할 수 없다.

S010은 정답을 추정하지 않고 동일한 `build_v3_monetary_view`를 두 cohort에 실행한다. 다음 형태가
dev와 모집단에서 크게 다르면 dev F1 0.941을 public 기대값으로 사용하지 않는다.

- candidate가 나온 문서 유형과 첨부문서 비중
- 공고당 candidate 수와 multi-candidate 비중
- 참가자격·평가·서식, 단일건·합계/누계의 **기술적 lexical morphology**
- candidate 안에서 기계적으로 파싱 가능한 금액과 입찰추정가격의 비율 구간
- dev 저장응답에서 Gemma가 실제 부여한 role/basis/mandatory 분포

Lexical morphology는 source review를 층화하기 위한 관측값일 뿐 v3 label, 역할 또는 법적
진리조건이 아니다. 모집단에는 Gemma를 호출하지 않으며 정답·F1·pseudo-label을 만들지 않는다.

## 변경 통제

- base config: `experiments/manifests/clean_exp_s001_integrated_v3_v19_v1.json`
- allowed change: `v3_population_morphology_audit` 추가만
- LLM/BGE calls: 0
- output: `outputs/clean-exp-s010-v3-population-morphology-audit-v1/`
- active imports: `src.pps_ai`만 사용
- final prediction / submission change: 없음

## 사전 고정 morphology

후보 원문에서 다음 표면형 존재만 센다. 서로 배타적이지 않으며 의미 역할로 환원하지 않는다.

- `qualification_surface`: 입찰참가·참가자격·자격충족·실적제한 계열
- `evaluation_surface`: 평가·배점·적격심사·신인도·정량 계열
- `form_surface`: 서식·양식·별지·작성요령 계열
- `single_surface`: 단일·1건·한 건·건당
- `aggregate_surface`: 합계·합산·누계·누적·총액·총실적

금액 관계는 candidate에 존재하는 모든 `MONEY_PATTERN` 표면형 중 파싱 가능한 값만 사용한다.
추정가격과 비교 가능한 candidate를 `all_le_estimate`, `any_gt_estimate`, `mixed`로 나누되 이는
실적 요구금액이라는 의미 검증 전의 **source upper bound**다.

## 판정 gate

1. dev 200/200, population 20,000/20,000과 모든 문서를 scan한다.
2. 입력 SHA-256, view module SHA-256, 패턴과 분모를 결과에 기록한다.
3. API/embedding calls가 0이고 final prediction이 없어야 한다.
4. notice-level과 candidate-level을 섞지 않고 각각 분모·rate·risk ratio를 기록한다.
5. `abs(rate difference) >= 0.10` 또는 risk ratio가 `[0.67, 1.50]` 밖이면 큰 shift로 표시한다.
6. 문서유형과 금액비 band에는 total-variation distance를 기록한다.
7. 수동 source review ID는 feature별 SHA-256 고정 순서로 선택한다. 원문은 결과 JSON에 복제하지
   않는다.
8. dev 저장 observation은 기존 artifact를 읽기만 하고, 모집단 분포와 직접 정확도 비교하지 않는다.
9. 결과가 v3 view의 구조적 이동을 보이면 S005 v3-only revert의 우선순위를 높인다. 이동이
   마지막 AGGREGATE 표면에 국한되면 full revert 대신 reducer rollback을 별도 one-change
   후보로 분리한다.

S010은 제출 후보가 아니라 다음 public ablation을 선택하는 진단이다. public 성능 향상은 이후
정확히 한 정책만 바꾼 제출에서만 검증할 수 있다.
