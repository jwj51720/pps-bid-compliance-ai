# INC-121 — EXP-120 출력 계약 / source-anchor pilot

## 가설

EXP-120의 4,000자 card-v6 입력을 고정할 때, 자유 텍스트 evidence 대신 원문에서
결정적으로 생성한 source-anchor ID를 선택하게 하면 Gemma의 24개 위반 판단 F1을
개선하면서 제출 evidence를 100% 원문으로 보존할 수 있다.

## 기존 실패와 설계 경계

- INC-054의 일반 V-only는 비교군보다 약했고, 따라서 A1은 제출 후보가 아닌 진단 arm이다.
- INC-060은 모든 positive에 global source-line ID를 요구했지만 positive-without-ID가
  반복돼 무효였다. 이번에는 그 실패를 score에서 0으로 숨기지 않고 record failure로
  처리한다.
- INC-117의 generated quote/e-prime은 63개 nonempty quote 중 2개가 원문에 복구되지
  않아 무효였다. 이번 output에는 생성 quote나 model rationale을 전혀 받지 않는다.

## 고정 요소

- `google/gemma-4-26b-a4b-it`, temperature 0, 동일 seed, max tokens 1,536
- decision cards v6, metadata, 4,000 raw-character ordered document budget
- 각 source span은 input에 포함된 원문 그대로이고 최대 500자다.
- 동일 notice, 동일 numbered-source rendering, 동일 retry/transport policy를 세 arm에
  적용한다. label은 prompt에 절대 포함하지 않는다.

## Arm

| Arm | 출력 | 역할 |
|---|---|---|
| `control_ve` | EXP-120 호환 `{위반여부, 근거문구}` | output-contract control |
| `a1_v_only` | 24개 0/1 label | 판단/evidence 부담 분리의 진단 |
| `a2_anchor` | 24개 `{위반여부, anchor_id}` | 유일한 제출 승격 대상 |

`a2_anchor`는 non-absence positive에 source span ID를 반드시 선택하고, negative에는
`-1`을 반환한다. Python은 ID에서 original substring을 직접 복구한다. ID 누락·범위
오류·source mismatch는 all-negative로 고쳐 score를 내지 않고 해당 arm record failure로
기록한다.

## Cohort

크기 32의 exploration cohort는 다음 label-blind-compatible selection rule을 실행 전에
고정한다.

1. 각 `v1`~`v24`의 dev positive 중 SHA-256 최소 ID 하나를 선택한다. 이는 evaluation
   coverage를 위한 cohort construction이며 prompt에는 사용하지 않는다.
2. 아직 선택되지 않은 records에서 source document 수(1/2/3+), complete/incomplete,
   source-length tercile의 각 strata 대표를 SHA-256로 선택한다.
3. 남은 자리는 SHA-256 순서로 채운다.

manifest에는 selection rule, IDs, source hashes, prompt hashes만 남기며 raw notice나
gold label은 넣지 않는다. 성공 시에는 disjoint hash holdout 32건에서 같은 protocol을
한 번 확인하고 dev-200으로 승격한다.

## 사전 gate

- preflight/mock에서 32 records × 3 arms = 96 requests, 모든 prompt/source anchor가
  admission 및 substring validator를 통과해야 한다.
- run ceiling은 $1.00, 96 requests, retry 포함 2% 초과 failure 시 즉시 중단이다.
- A2가 control보다 macro positive-F1 `+0.02` 이상, recall 비감소, non-absence evidence
  validity 100%일 때만 holdout으로 간다.

작거나 좋지 않은 결과는 prompt rewording 반복 근거가 아니다. changed-cell dossier가
하나의 transport/semantic 원인을 입증할 때만 한 번의 repair를 허용한다.
