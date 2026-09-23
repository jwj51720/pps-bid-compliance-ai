# S004 — dev200 대 organizer 20,000 입력분포 감사 결과

실행일: 2026-09-23

상태: **PASS — 큰 모집단 shift 확인, submission 정책 변경 없음**

## coverage와 실행

- dev: 200 records / 374 documents
- organizer 비라벨 모집단: 20,000 records / 38,862 documents
- LLM calls: 0, embedding calls: 0
- runtime: 12.138초
- preflight undeclared differences: 0
- 결과: `outputs/clean-exp-s004-generalization-shift-audit-v1/audit_report.json`

두 입력 JSONL의 SHA-256과 native v3/v19 source-view 경로를 결과에 기록했다. raw source 문장은
산출물에 복제하지 않고 집계값만 남겼다.

## 핵심 분포 차이

| feature | dev200 | 20,000 | 차이 |
|---|---:|---:|---:|
| 제한경쟁 | 67.50% | 42.37% | +25.14%p |
| 수의계약 | 17.50% | 44.81% | -27.31%p |
| 협상에의한계약 | 42.50% | 24.34% | +18.15%p |
| 소액수의견적 | 17.50% | 44.81% | -27.31%p |
| 입찰추정가격 5억원 이상 | 12.00% | 2.82% | +9.18%p |
| 입찰추정가격 1억원 미만 | 53.00% | 71.66% | -18.66%p |
| 첨부 있음 | 66.50% | 76.83% | -10.33%p |
| v3 candidate route | 30.50% | 20.42% | +10.08%p |
| v19 candidate route | 82.50% | 76.10% | +6.40%p |

범주분포 total variation은 계약방법 `0.2772`, 낙찰방법 `0.27845`, 가격 band `0.19785`,
문서유형 signature `0.2117`이다. 반면 적용계약법 `0.04425`, 업무구분 `0.01355`는 상대적으로
유사했다. 평균 문서 수와 전체 문자 수의 standardized mean difference는 각각 `-0.0948`,
`0.0921`로 작았다. 즉 단순히 test 문서가 훨씬 길어서가 아니라 **계약·가격·첨부 조합의
구성이 다르다**는 신호다.

## specialist 해석

v3 source route는 dev에서 모집단보다 `1.4936x` 자주 발동한다. rate 차이도 `10.08%p`로
사전 large-shift gate를 넘었다. S001 v3의 local 이득은 dev 오류를 본 뒤 선택한 reducer까지
포함하므로, v3 specialist의 `+0.024064` local Macro 기여를 그대로 public 기대값으로 쓰면 안 된다.

v19 route는 risk ratio `1.0841`, 차이 `6.40%p`라 사전 large-shift gate를 넘지 않았다.
이는 v19 판단 정확성을 증명하지 않지만, 적어도 candidate admission 빈도 면에서는 v3보다
모집단 이동이 작다. 따라서 specialist 과적합을 분리할 첫 ablation은 v3와 v19를 동시에
제거하기보다 **v3만 base owner로 되돌리는 것**이 더 식별력이 높다.

## base owner에 대한 의미

dev는 위반 가능성이 높은 제한경쟁·협상·고액 strata를 의도적으로 많이 포함하고,
organizer 모집단은 저가·소액수의 strata가 훨씬 많다. 따라서 dev에서 5~8개 양성을 맞혀
F1 1.0이 된 owner도 다음을 거의 검증하지 못했을 수 있다.

- 소액수의 예외의 recall과 다양한 표현
- 1억원 미만 제품·기업범위·부재 항목의 precision
- 첨부문서에만 존재하는 예외·적용 조건
- 수의계약과 제한경쟁에서 같은 문구가 가지는 서로 다른 역할

분포 차이만으로 어느 label이 틀렸다고 할 수는 없다. 그러나 dev-perfect owner를 그대로
source-correct라고 간주하거나 한두 dev 오류를 더 고치는 전략은 중단해야 한다.

## 다음 조치

1. S005는 S001에서 v3 specialist owner/routing만 제거하고 v19와 base 22 item, runtime,
   evidence를 고정한 stored-response replay와 call audit로 설계한다.
2. 다음 public 제출에 여러 correction을 섞지 않는다. v3 ablation과 2026-09-22 지역금액
   correction은 별도 후보다.
3. base deterministic owner는 소액수의·1억원 미만·첨부-only strata에서 activation과 source
   role을 우선 감사한다. 비라벨 자료의 label을 추정하지 않고, organizer truth condition과
   source role이 맞는지만 stratified review한다.
4. exact reference public score와 ZIP hash가 확보되기 전까지 `0.7+`를 수치 기준선으로 쓰지 않는다.
