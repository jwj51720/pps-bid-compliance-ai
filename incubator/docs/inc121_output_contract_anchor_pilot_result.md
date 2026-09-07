# INC-121 — 출력 계약 / source-anchor pilot 결과

**판정: A branch 실패. A1과 A2 모두 제출 후보로 승격하지 않는다.**

## 실행 재현 정보

- source: dev SHA `7dedfaaf…`, labels SHA `84c79302…`, cards v6 SHA
  `609b60be…`; cohort ID SHA `053d58c9…`
- model: `google/gemma-4-26b-a4b-it`, temperature 0, seed 20260906
- cohort: 32 notices, 96 calls, reported total cost `$0.07410`
- fixed raw context budget: 4,000 characters; all three arms used the same
  numbered original source spans, metadata, and decision cards v6.
- preflight and all-negative mock passed. Raw prompts/responses/checkpoints are
  ignored under `runs/inc121_output_contract_anchor_pilot/`.

## 결과

| Arm | Valid records | Macro positive-F1 | Micro recall | Non-absence evidence validity | 결론 |
|---|---:|---:|---:|---:|---|
| `control_ve` | 32/32 | **0.25502** | 0.32787 | 0.35714 | comparator only |
| `a1_v_only` | 32/32 | 0.13472 | 0.11475 | n/a | reject |
| `a2_anchor` | 30/32 | unscorable | n/a | n/a | reject before score |

`a1_v_only`는 control보다 `-0.12030` macro-F1, `-0.21311` micro recall이다.
이는 EXP-120의 evidence-bearing answer process가 단순한 output 비용이 아니라
judgment signal이라는 기존 INC-054 관측을 같은 card-v6/4k policy family에서 다시
지지한다.

`a2_anchor`는 `PPS-DEV-058`과 `PPS-DEV-079`에서 모두 positive `v23`인데
`anchor_id=-1`을 출력했다. Python은 positive-without-anchor를 all-negative로
후처리해 F1을 계산하지 않았고, arm record failure로 남겼다. 2/32 = **6.25%**는
사전 failure ceiling 2%를 넘는다. 30개 성공 row만 골라 점수 내거나, `-1`을
자유-text evidence로 보정하거나, 같은 cohort에서 prompt를 고쳐 재실행하는 것은
허용하지 않는다.

## 해석

1. 현재의 joint 24-item Gemma policy에서 V-only는 recall을 급격히 잃는다. V-only는
   향후 제출 및 conditional second pass의 default가 아니다.
2. 모든 positive에 source-anchor selection을 강제하는 전역 A2 topology는 INC-060과
   같은 semantic failure를 다시 보였다. Python-generated source ID는 quote fidelity를
   보장할 수 있어도 model이 legal positive마다 evidence ID를 선택하게 만들지는 못한다.
3. control의 0.25502는 32건 cohort comparator일 뿐 EXP-120 dev200/public score의
   재현 주장으로 쓰지 않는다. 이 run은 raw source line markers라는 fixed rendering도
   EXP-120과 다르다.

## 다음 결정

A branch는 종료한다. 원문 span resolver는 final evidence validation 도구로 보존하되,
다음 A2 rewording, forced line-ID, V-only 제출, 또는 same-cohort repeat은 하지 않는다.

다음 독립 BFS branch는 **C: 짧은 공식 법령 문맥**이다. Luna의 official-law ledger
신호를 Gemma에 옮길 때 broad law injection 대신, card v6와 하나의 item-linked
official condition/exception excerpt만 다르게 하는 paired design을 만든다. 새로운
32-notice cohort와 independent holdout을 사용하고, absence items의 FP 증가와 token
admission을 별도 gate로 둔다.
