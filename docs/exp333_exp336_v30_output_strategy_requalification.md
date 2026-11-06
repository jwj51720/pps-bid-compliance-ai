# EXP333–336 — v30 source-concordant 입력에서 V/E와 반복 V-only 재검증

작성: 2026-09-18, dev / mac

## 왜 기존 기각 실험을 한 번만 재검증하는가

EXP323–326은 당시 `semantic-complete`라고 부른 v26에서 V/E, V-only, V-only draft→V/E,
V-only×2→V-only resolver를 비교했고 V/E가 이겼다. 그러나 2026-09-18 전수 source 감사에서
v3·v4의 organizer 정의 충돌과 v5·v6·v7·v9·v12·v14·v15의 누락/오류가 확인됐다. 특히
금액 selector, 공사 분기, 예외 적용범위처럼 실제 label을 바꿀 수 있는 결함이므로, 기존 결과는
`판정에 필요한 정보가 온전히 들어간 상태에서의 V-only 검증`이라는 전제를 충족하지 못한다.

따라서 v30을 기준으로 네 arm을 **한 번만** 동일 fast20에서 재자격화한다. 이는 draft 수,
투표법, wording을 탐색하는 재시도가 아니다. v30에서도 V-only가 이기지 못하면 이 family는 다시
종료한다.

## 비교 arm과 변경 통제

| EXP | 구조 | base | allowed policy changes |
| --- | --- | --- | --- |
| 333 | one-stage V/E control | EXP332 | card path only |
| 334 | one-stage V-only | EXP333 | `prompt.output_mode` only |
| 335 | V-only draft → full-source V/E final | EXP333 | `staged_run(.mode)` only |
| 336 | V-only draft×2 → V-only resolver | EXP334 | `staged_run(.mode)` only |

모든 arm은 v30 card, human-readable metadata actual values, condition-aware product fact,
exact-tokenizer adaptive full source, 기존 source-pack merge, temperature/seed/provider를 유지한다.
Python voting, label override, 법률 rule, evidence 생성은 넣지 않는다. EXP334/336의 evidence blank는
label-quality diagnostic의 알려진 한계다.

## 사전 완결성 gate

- dev200 exact admission: 200 notices, 374 supplied docs, 243 contexts, supplied-doc omission 0.
- actual-value delivery: 200/200 및 243/243 PASS; upstream unavailable external docs 10개 별도 기록.
- exact rendered audit v2: 062/194/143/049/046의 v1–v24 PASS. 143은 실제 3 contexts를 각각
  렌더링해 card/metadata/product fact와 source union을 확인한다.
- exact fast20 mock: 20 rows, 49 columns, validation PASS.
- regression suite: 278 passed.

## 평가·승격 규칙

1. 우선 EXP333과 EXP334로 출력 계약 자체의 label effect를 비교한다.
2. EXP335/336은 여러 read가 single arm보다 실제 label F1을 높이는지 확인하는 마지막
   requalification이다. 각 저장 draft와 resolver를 따로 채점해 어느 단계가 변화를 만들었는지
   분해한다.
3. fast20 결과는 순위 결정용이다. V-only 계열이 V/E보다 높고 positive recall/FP가 함께
   납득 가능한 경우에만 independent holdout20을 만든다.
4. fast와 holdout 방향이 일치한 정책만 dev200으로 확장한다.
5. V-only가 승리할 때만 source-grounded evidence recovery를 별도 가설로 설계한다. label gain
   없이 e 후처리를 만들지 않는다.
6. runtime은 품질과 별도 gate다. 다중 arm은 submission 후보가 아니라 quality upper bound이며,
   120분 내 call topology가 성립해야만 제출 구조로 검토한다.

## 결과

### Fast20

| EXP | 구조 | Macro positive-F1 | positives | runtime | prompt / completion tokens | evidence validity |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 333 | one-stage V/E | `.142361` | 13 | 129.2s | 529,266 / 16,632 | 1.0 |
| 334 | one-stage V-only | `.088889` | 12 | 47.5s | 526,999 / 4,968 | 0 (의도적 blank) |
| 335 | V-only draft → V/E | `.123611` | 13 | 131.8s | 1,065,061 / 25,457 | `.923077` |
| 336 | V-only×2 → V-only resolver | `.144444` | 13 | 133.3s | 1,591,767 / 15,304 | 0 (의도적 blank) |

저장 stage를 label과 다시 대조한 결과:

- EXP335 draft `.085417`(positive 9) → V/E final `.123611`.
- EXP336 draft1 `.106250`(positive 10), draft2 `.106250`(positive 9) → resolver
  `.144444`(positive 13).
- 즉 resolver가 단일 draft보다 일부 양성을 회복했지만, EXP333 V/E 대비 차이는 `+.002083`에
  불과하며 입력 token은 약 3.0배다. EXP334/335는 control보다 명확히 낮다.

single V-only와 draft→V/E는 확장하지 않는다. EXP336의 아주 작은 우위가 변동인지 확인하기 위해
policy-identical independent holdout에서 EXP337 V/E와 EXP338 consensus만 비교한다. holdout에서
방향과 오류구성이 재현되지 않으면 dev200 및 evidence algorithm을 진행하지 않는다.

### Independent holdout20

사전 검증은 두 arm 모두 통과했다. holdout은 20 notices / 41 supplied documents이며
17건×1, 2건×2, 1건×3 = 24 source contexts, supplied-document omission 0이다. short/attachment와
overflow `PPS-DEV-082`(3 contexts), `PPS-DEV-27`(2 contexts)의 exact rendered audit에서 모든
context의 24 cards/필수 metadata/product fact와 source union이 PASS했다.

| EXP | 구조 | Macro positive-F1 | positives | runtime | prompt / completion tokens |
| --- | --- | ---: | ---: | ---: | ---: |
| 337 | one-stage V/E | **`.125000`** | 5 | 80.1s | 482,506 / 20,972 |
| 338 | V-only×2 → V-only resolver | `.111111` | 4 | 111.8s | 1,450,973 / 13,598 |

EXP338의 저장 draft1과 draft2는 각각 `.083333`이고 positive도 각각 2개뿐이었다. resolver가
`.111111`/positive 4로 일부 회복했지만 V/E보다 낮았다. fast의 `+.002083`은 holdout에서
`-.013889`로 반전됐고 prompt token은 약 3배다.

## 최종 결정

- v30처럼 source-concordance를 전수 보수한 입력에서도 single V-only는 V/E보다 크게 낮았다.
- 반복 V-only의 미세 fast 우위는 independent holdout에서 재현되지 않았다.
- 따라서 EXP334–336/338은 dev200으로 확장하지 않고, V-only용 evidence 후처리도 만들지 않는다.
  후처리는 label 성능이 이긴 뒤의 문제인데 그 선행조건이 성립하지 않았다.
- 이 결과로 `V-only라서 e 생성에 attention을 빼앗기지 않아 정확도가 오른다`는 일반 가설은
  다시 기각된다. 다만 item-local 특수 사례(v20 등)의 과거 연구 상한과는 구분한다.
- 다음 성능 병목은 출력 serialization이 아니라, 한 all-24 호출에서 18개 이상의 positive item이
  거의 all-zero가 되는 attention/decision execution이다. 다음 후보는 동일 prompt 반복이 아니라
  source-grounded applicability/관계 사실을 한 번 구조화하고 final이 원문과 재대조하는 bounded
  architecture여야 한다.
