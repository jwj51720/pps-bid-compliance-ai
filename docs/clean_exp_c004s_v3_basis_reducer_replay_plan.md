# EXP-C004S — v3 requirement-basis reducer replay

작성일: 2026-09-21

## 확정 결함

C004R reducer는 실제 참가자격 금액 observation 중 `SINGLE_CONTRACT`만 인정하고
`AGGREGATE`를 버린다. 그러나 organizer source에는 이 gate의 근거가 없다.

- 항목표: `실적제한 1배수 이상`, 비고 `사업예산 기준`
- 국가계약법 시행규칙 제25조: `실적의 금액에 따르는 경우 ... 추정가격의 1배 이내`
- 지방계약법 시행규칙 제25조: `실적금액에 의하는 경우 ... 추정가격의 1배 이내`

어느 source도 위반 판단을 `단일 계약 실적`에 한정하지 않는다. `단일 과거실적`은 과거
decision card가 source 없이 추가한 조건이다. 따라서 model observation의 역할·mandatory·exact
amount 검증은 유지하되, verified requirement basis를 `SINGLE_CONTRACT | AGGREGATE`로 넓힌다.
`UNKNOWN`은 계속 fallback한다.

## base와 허용 변경

- base: C004RR final (`outputs/clean-exp-c004rr-v3-keyed-recovery-v1/`)
- allowed change: v3 reducer의 accepted basis set 하나
- calls: 0; 저장된 61 keyed responses와 2 recovery attempts만 재생
- fixed: source view, prompt, schema, observations, provider, evidence, 다른 23개 cells
- legacy import/execute/copy/generation: 금지

## 사전 영향 상한

저장 observation에서 role=BID_QUALIFICATION, mandatory=YES, basis=AGGREGATE, exact amount valid인
공고는 4건이다.

| notice | amount | estimate | strict `>` |
| --- | ---: | ---: | --- |
| PPS-DEV-03 | 30,000,000 | 89,090,909 | false |
| PPS-DEV-06 | 400,000,000 | 748,181,818 | false |
| PPS-DEV-059 | 200,000,000 | 83,454,545 | true |
| PPS-DEV-078 | 50,000,000 | 90,454,545 | false |

따라서 reducer가 새 positive로 만드는 상한은 059 한 건이다. 이 표는 저장 observation과 organizer
metadata로 계산했으며 notice ID나 금액을 reducer rule에 넣지 않는다.

## gate

1. unit test: SINGLE/AGGREGATE 모두 accepted, UNKNOWN rejected.
2. input response SHA/task identity 유지, calls 0.
3. 변경 cell은 v3/e3만 허용; v3 외 0 changes.
4. fast20·holdout20 성능 비열화 없음.
5. dev200에서 예상 변화는 059의 0→1 하나이며 다른 변화가 있으면 원인 검토 전 승격 금지.

예상 dev200 v3는 TP 8 / FP 1 / FN 0 / F1 `0.941176`, 예상 Macro는 약 `0.803738`이다.
이 replay는 FP 137의 FORM role 오류를 고치지 않으며 두 결함을 섞지 않는다.

