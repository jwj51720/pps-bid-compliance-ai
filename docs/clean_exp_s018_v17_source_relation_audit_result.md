# S018 — v17 원문 관계 감사 결과

실행일: 2026-09-23

상태: **PASS — 원문 역할 결함 재현, 단어 veto와 v17 전체 rollback 모두 기각**

## 무결성

- frozen L41 ZIP SHA-256 검증; `dev.final_tqec_pipeline.scope_hits_v2`는 격리 loader를 통해서만 사용.
- S001 dev200 V17 양성 13건의 원본/정답/제출 ID 완전 일치.
- frozen scope hit와 제품 후보의 원문 위치를 문서 ID·offset·SHA-256으로 검증.
- 비라벨 20,000건 동일 source detector 실행. Gemma/BGE calls 0.
- 실행 약 32초. 원문 발췌와 input hash는 ignored
  `outputs/clean-exp-s018-v17-source-relations-v1/audit_report.json`에 보관.
- 고정 manifest: `experiments/manifests/clean_exp_s018_v17_source_relations_v1.json`.
- 재현: `.venv/bin/python scripts/audit_v17_source_relations.py --config experiments/manifests/clean_exp_s018_v17_source_relations_v1.json`.

## dev200에서 실제로 놓친 관계

S001 v17은 TP 6, FP 7, FN 0, F1 0.631579이다. 기존 frozen final owner는
`입찰추정가격 < 1억원 ∧ 비공사 ∧ broad scope hit ∧ no small scope hit ∧
no competitive product ∧ no v10/v11`로 판정한다. **현재 계약에 적용되는 예외**를 별도로
확인하지 않고, broad hit가 실제 중기업 참가조건인지도 문장 역할로 검증하지 않는다.

| 사례 | 원문 및 organizer CSV 대조 | 기존 owner의 결함 |
| --- | --- | --- |
| `PPS-DEV-098` (FP) | 공고문 D0 `1707:1823` 참가조건은 **소기업 및 소상공인**이다. 뒤의 `중‧소기업·소상공인 확인서`는 확인서 명칭이다. | 확인서의 넓은 이름을 참가 가능 기업범위로 승격. |
| `PPS-DEV-105` (FP) | 공고문 D0 `1904:2187`에 이번 용역이 시행령 제2조의3 제1항 1호의 우선조달 예외라고 명시된다. | broad 참가조건만 보고 적용 예외를 무시. |
| `PPS-DEV-139` (FP) | 공고문 D0 `1642:1876`의 세부품명에 CSV exact match `8214150201`과 조건부 `8213160301`이 있다. | 문서 exact code를 얻었지만 BGE top-10과 상품명 질의의 교집합이 없어 `competitive=false`. 실제 구매대상/특이사항 관계 검증이 빠짐. |
| `PPS-DEV-177` (FP) | 공고문 D0 `2256:2466`의 직접생산 참가조건에 CSV exact match `8014198801`이 있다. | 위와 같이 코드 존재를 적용제품 여부로 연결하지 못함. 구매대상 관계는 별도 확인 필요. |
| `PPS-DEV-093` (FP) | 공고문 D0 `4625:4835`의 직접생산 코드 `8014199001`이 CSV와 매칭된다. | 실제 계약은 직무교육 기획 운영이므로 **코드가 구매대상인지 미확정**. 코드 존재만으로 veto하면 안 됨. |

반례도 확인했다. `PPS-DEV-053`은 정답 1이지만 공고문 D0 `2549:2786`에 경쟁제품
코드 두 개가 직접생산확인서 참가요건으로 있고, D0 `2449:2674`에 제2조의3 비영리법인
문구도 있다. 따라서 `CSV 코드가 있으면 0`, `제2조의3이 있으면 0`이라는 Python 단어
veto는 확인된 TP를 잃는다. `PPS-DEV-090`, `126`도 오탐이지만 이번 감사만으로
구매대상·적용 예외의 참값을 확정하지 않았다.

## 비라벨 20,000건의 이동

동일 frozen scope detector가 `금액 <1억원`, `비공사`, `broad 있음`, `small 없음`으로
잡은 것은 **1,702/20,000건(8.51%)**이다. 제품/BGE 및 v10/v11 veto 전의 상한 route이므로
실제 v17 양성률이 아니다. 이 중 657건(38.60%)은 어느 문서에든 경쟁제품 CSV와 일치하는
10자리 코드가 있었다. 단순 코드 유무는 실제 구매대상 적용성과 다르다.

| stratum | CSV 코드 있음 | 없음 |
| --- | ---: | ---: |
| 경쟁, 첨부 있음 | 314 | 412 |
| 경쟁, 공고문만 | 94 | 84 |
| 수의, 첨부 있음 | 232 | 406 |
| 수의, 공고문만 | 17 | 143 |

각 8개 cell에서 ID 해시 최소 2건을 골라, 정답을 보지 않고 원문을 확인했다. 16건 중
`PPS-D-000730`, `007638`, `012279`, `014315` 네 건은 frozen broad hit 자체가
**소기업·소상공인 전용** 참가조건이다. `PPS-D-001045`, `011561` 두 건은 frozen broad hit
자체가 **이번 계약의 우선조달 예외 문장**이다. 이는 dev 한두 ID의 희귀 오탈자에 맞춘
문제가 아니라, source detector가 문장 역할을 혼동하는 재현 가능한 구조 결함이다.
16건은 작은 계층별 해시 표본이므로 `6/16`을 모집단 오류율로 외삽하지 않는다.

같은 frozen `scope_hits_v2`를 쓰는 v16/v18도 dev 오류를 교차 감사했다. v16 FP 3건,
v18 FP 4건 **모두 broad hit가 없었다**. 따라서 v17의 `거짓 broad hit`를 고치면 이
7개 오류까지 함께 해결된다고 주장할 수 없다. 반대 방향의 detector 누락은 존재한다.
예를 들어 `PPS-DEV-173`의 공고문 D0 `3155` 부근에는 소기업 또는 소상공인을
참가조건으로 둔 문장이 있는데 `small` hit가 없다. 이 항목에는 별도 source-role 진단이
필요하다. 교차 결과는 동일 audit JSON의 `shared_scope_error_overlap`에 있다.

## 수학적 결정

현재 v17의 `A=TP=6`, `B=FP=7`, `C=FN=0`에서 positive를 일부 제거하는 guard가
`t`개 TP와 `f`개 FP를 함께 지우면 F1 개선의 필요충분조건은
`f > t(A+B+C)/A = 13t/6`이다. 즉 TP 한 개를 잃는 guard는 FP를 적어도 세 개
제거해야 한다. S014 weight를 쓰면 필요한 **weighted FP 제거량**은
`3.158 × weighted TP 손실량`을 넘는다.

오류를 이미 본 dev에서 `098`, `105` 두 FP만 완벽하게 제거한다고 가정하면 v17 F1은
0.631579→0.705882, Macro는 +0.003096이다. S014 weighted v17 F1은
0.481013→0.615759, weighted Macro는 +0.005614다. `139`, `177`까지 완벽히
제거한다는 낙관 상한은 raw v17 F1 0.800000, Macro +0.007018이며 weighted v17
F1 0.641269, weighted Macro +0.006677이다. 이는 **오류 ID를 알고 선택한 oracle
counterfactual**이며 실행 가능한 일반 규칙의 점수가 아니다.

따라서 v17을 전부 초기 R2로 되돌리는 안은 S011/S014의 큰 recall 손실 때문에 유지하지
않는다. 개별 단어/코드 veto도 기각한다. 실제 제거 대상은 `broad hit = 중기업 참가 허용`,
`문서의 CSV 코드 = 구매대상 경쟁제품`, `예외 문자열 = 이번 계약의 예외`처럼 서로 다른
관계를 한 비트로 취급하는 **잘못된 승격 가정**이다.

## 다음 품질 실험

v17 한 항목에 한해 source span의 역할을 `실제 참가 가능 범위`, `실제 구매대상과 CSV
행·특이사항의 관계`, `이번 계약에 적용된 예외`로 관측한 후 원문과 다시 대조하는
후보를 설계한다. 기존 `src/pps_ai/views/v17_full_source.py`의 초안은 원문 전체를 담는
형태와 relation-view로 줄이는 형태가 섞여 있으므로, 먼저 final input completeness와
token/runtime을 감사해야 한다. 양성 후보에 대한 별도 호출은 현 제출 95분 27초와 120분
제한 사이의 여유를 넘길 수 있어 evaluator vLLM 계측 없이 승격하지 않는다.

v16/v18은 공유 detector를 사용하지만 이번 v17 오류와 같은 방향의 dev 오류가 없다.
따라서 관계 관측 schema를 이 두 항목에 곧바로 확장하지 않는다. 큰 Macro 개선을 위해서는
v24의 44 FP와 v4/v9의 의미 판정 누수도 각 truth condition에 따라 독립 진단해야 한다.

이번 감사는 **실제 제출 정책을 수정하지 않았다**. dev200은 반복적으로 사용한 adaptive
자료이고 public 오류의 항목별 분해는 공개되지 않았다. 일반화 상승은 독립 데이터 또는
다음 public 제출에서 확인해야 한다.
