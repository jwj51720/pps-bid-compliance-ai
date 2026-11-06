# N002: v1 explicit state-contract fast20

작성일: 2026-09-22

N001은 source/card/tokenizer 문제가 아니라 state/quote 의미가
불명확해 Y=0, N=1, U=19가 됐다. N002는 v1 source view v2,
v31 card, fast20 IDs, provider/generation/schema shape를 고정하고
system의 output semantic contract만 version v3로 바꾼다.

- Y = 카드의 1 조건을 충족한 v1 위반
- N = 카드의 0 조건을 충족한 비위반
- U = 후보가 상충하거나 필요한 참가자격 문맥이 실제로 부족
- quote = Y일 때만 exact 1~500자 source substring, N/U는 null

base config는 N001 manifest이며 `allowed_policy_changes`는
`prompt.task`, `data.source_audit_path`다. v3 prompt는 dev200 200건
전체를 다시 exact-token audit해 task hash와 short/attachment/largest
rendered review를 별도 output에 남긴다. fast20 mock과 preflight를
통과한 뒤 20회만 재호출한다.

성공 gate는 invalid 0, Y quote validity 100%, positive 3건 중 TP>=2,
FP<=2, U<=4다. 이는 완성 owner 승격 기준이 아니라 다음 holdout을
볼 최소 진단 조건이다. 실패하면 문구를 계속 변형하지 않고 실제
positive/negative 관측을 분석해 view 또는 truth contract 문제를
분리한다.
