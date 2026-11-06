# S023 — dev 포화가 Python 과적합 제거 실험에 주는 선택 편향

2026-09-23, 0-call analytical audit. 정책·예측·라벨 변경 없음.

재현 근거:

- `outputs/clean-exp-s001-integrated-v3-v19-v1/metrics.json` SHA-256
  `3cab90043a186e706aa9817600501bcce342954c9323eebb777ad047adac5323`
- `outputs/clean-exp-s019-python-policy-population-audit-v1/audit_report.json` SHA-256
  `2f6a10e3d38c84bc7a99d1a9e1d882acefd7d40ad2c7266e4e72306648706083`
- `outputs/clean-exp-s020-direct-owner-source-role-audit-v1/source_samples.json` SHA-256
  `1301658983685768d459bc3c3098f85a5043183ac432884812e4355a432082a2`

## 관측된 포화

| final Python owner | dev TP/FP/FN | dev F1 | 비라벨 20k 발화 | dev 양성 한 건 제거 시 Macro 변화 |
|---|---:|---:|---:|---:|
| v1 | 7/0/0 | 1.0000 | 118 | -0.003205 |
| v2 | 7/0/0 | 1.0000 | 255 | -0.003205 |
| v5 | 7/0/0 | 1.0000 | 42 | -0.003205 |
| v6 | 6/1/0 | 0.9231 | 197 | -0.003739 |
| v7 | 7/0/0 | 1.0000 | 349 | -0.003205 |
| v8 | 6/0/0 | 1.0000 | 34 | -0.003788 |

다섯 항목은 dev에서 FP와 FN이 아예 없다. 이 항목의 양성 예측을 더 보수적으로
만드는 어떤 gate도 dev에서 제거되는 양성이 한 건이라도 있으면 F1이 내려간다. 기존
fast20과 holdout20은 모두 같은 dev200의 부분집합이고, 이미 선택에 사용됐다. 따라서
이 세 점수의 **상승을 필수 조건**으로 삼으면 false positive를 줄여 public에서 이득을 줄
수 있는 변경까지 구조적으로 탈락시킨다. 반대로 dev 양성을 모두 보존하는 gate가
public을 개선한다는 보장도 없다.

수식: 현재 `TP=T, FP=F, FN=N`인 항목에서 gate가 기존 양성의 참양성 `x`개와
거짓양성 `y`개를 제거할 때, `F1_new > F1_old`의 필요충분조건은
`T*y > x*(T+F+N)`이다. dev에서 `F=0`이면 `y=0`이므로 `x>0`인 제거는 절대
dev F1을 올릴 수 없다. 이 식은 같은 정답 집합에서 고정된 예측을 비교할 때만
성립하며 비라벨 20k에서는 `x,y`를 계산할 수 없다.

여섯 direct owner의 dev item-F1 합은 `5.9230769`, Macro 기여는 `0.2467949`다.
관측 local-public 괴리 `0.2097938`보다 크므로 이 계열만으로도 **수학적 상한상**
괴리를 설명할 수 있다. 그러나 public per-item 결과가 없으므로 실제 기여를
추정할 수 없고, 다른 owner·생성 환경의 손실을 배제할 수도 없다.

S020의 고정 8건/owner 원문 검토에서는 v1 네 건, v5 두 건, v6 두 건에서 Python hit가
실제 참가제한과 다른 역할을 가리켰다. 이것은 **source-role 반례**이지 대회 라벨 FP
확정이나 모집단 오류율 추정이 아니다. S022는 v5에서 전체 원문 역할 관측 가능성을
보였지만 blind 비라벨 8건이 모두 역할 양성이라 음성 판별은 아직 검증되지 않았다.

## 수정된 승격 기준

1. dev200·그 부분집합은 **알려진 TP 손실과 회귀**를 기록하는 용도로 쓴다. 포화 item의
   dev F1 증가를 과적합 제거의 필수 gate로 사용하지 않는다.
2. 비라벨 20k에서는 final activation을 정확히 세고, 여러 source strata에서 공고 전체를
   읽어 역할·제품 적용성·예외의 구조적 반례를 blind로 검토한다. 후보 전후에 source-role
   오독이 줄어드는지 측정하되 이를 대회 F1이라고 부르지 않는다.
3. 역할 guard가 기존 dev TP를 제거하지 않고 모집단의 명백한 역할 혼동을 제거하더라도,
   그 자체로 public 성능을 주장하지 않는다. 대체 owner와 근거·호출시간을 검증하고,
   가능한 독립 라벨 또는 **한 변경의 public 평가**로만 실제 일반화 효과를 판별한다.
4. public 제출은 하루 한 번이고 직전 runtime 95분 27초이므로, full-Python rollback이나
   다항목 동시 변경을 하지 않는다. 여러 owner의 공통 원리는 한 item에서 반례와 대체
   경로를 입증한 뒤 item별로 확장한다.

현재 결정: **Python final owner를 삭제하지 않는다.** 20k 분포 차이와 source-role
반례로 교체 우선순위는 높아졌지만, 새 gate의 양성·음성 일반화와 public 효과는 미측정이다.
