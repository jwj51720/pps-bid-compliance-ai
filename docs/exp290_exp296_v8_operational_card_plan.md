# EXP290–296 — v8 중복제한 operational card, V/E 대 V-only

작성: 2026-09-15, dev / mac

## Source audit와 기존 관찰

주최 측 항목표의 v8은 `중복제한 (실적+지역)`이고 비고는 `지방 + 소액수의 가능`이다.
organizer 법령 source를 다시 대조하면 현재 effective card의 `허용 조합`은 실제 판정에
필요한 다음 경계를 충분히 표현하지 않는다.

1. 국가·지방 제한경쟁에서 지역제한과 실적제한을 같은 입찰자의 실제 참가자격으로 함께
   요구하는 것은 원칙적으로 금지된다.
2. 국가·지방 시행규칙은 지역제한과 특수한 기술·공법이 필요한 공사의 기술/동종공사실적
   제한 결합을 허용한다. 단순히 공고가 `특수`라고 쓰거나 실적을 요구한다는 이유만으로 이
   예외를 추정하지 않는다.
3. 지방 2인 이상 견적 수의계약은 수의계약 운영요령상 지역제한과 계약목적 달성에 필요한
   추가 제한을 함께 둘 수 있으므로 그 결합 자체는 v8=0이다. 그 실적제한 자체의 적법성은
   특수한 기술 필요 등을 보는 별도 항목의 문제다.
4. 실적이 적격심사·특별신인도·제안서 평가의 배점자료일 뿐 입찰 참가 가능 여부를 닫지
   않으면 v8의 실적제한이 아니다. 지역명·사업장·현장 설명도 본점/영업소 참가제한이 아니면
   지역제한이 아니다.

dev200 gold positive 6건(DEV05, 11, 42, 48, 54, 71)은 모두 참가자격에 지역과 완료 실적을
함께 요구한다. 현재 EXP208의 대표 FP는 서로 다른 0-condition을 보여 준다.

- DEV10: 지역은 참가자격이지만 이행실적은 적격심사 평가다.
- DEV059: 두 조건 모두 참가자격이지만 지방 소액수의 견적의 허용 결합이다.
- DEV175: 지역은 참가자격이지만 실적은 특별신인도 평가다.

EXP208의 source-after relation checklist는 v8을 dev200 `0 -> .500`으로 올렸지만 여전히
`TP/FP/FN = 3/3/3`이다. 기존 7-category navigation은 참가자격·실적·지역 문자열을 모을 수
있어도 이 세 절차 역할과 예외를 card가 operational하게 지시하지 않는다. 반면 과거
`v8_composite_merge`는 문서 관찰을 Python conjunction label로 바꾸므로 현재 정책상 재사용하지
않는다.

## 가설

v8 card 하나만 다음 순서로 고치면, 새 schema나 Python label rule 없이 Gemma가 실제 참가자격
결합과 평가용 실적, 지방 소액수의 허용 결합을 구분할 수 있다.

1. 지역 본점/영업소 제한이 실제 입찰 참가자격인지 확인한다.
2. 완료된 동종 공사·물품·용역 실적의 최소 금액·규모·건수를 실제 참가자격으로 요구하는지
   확인한다.
3. 두 제한이 같은 입찰자에게 모두 AND로 적용되는지 확인한다. 문서나 문단이 달라도 최종
   참가자격이 함께 적용되면 동일 결합이다.
4. 적격심사·특별신인도·제안서 평가용 실적은 제외한다.
5. 지방 금액기준 2인 이상 견적 수의계약이면 허용된 결합으로 0이다. 그 실적요건 자체가
   허용되는지는 v8에서 다시 판정하지 않는다. 그 밖에는 국가·지방 제한입찰의 명시적
   특수기술 공사 예외가 실제 확인될 때 0이며, 예외 사실이 불명확하면 자동으로 0이나 1을
   만들지 않는다.

## Controlled arms

- EXP290: EXP205를 base로 v8만 활성화하고 relation mode를 제거한 existing-card V/E attention
  control. 허용 변경은 `prompt.active_items`, `prompt.profile`, `prompt.mode`뿐이다.
- EXP291: EXP290 대비 v8 card artifact만 corrected version으로 교체한 V/E.
- EXP292: EXP291 대비 output contract만 labels-only로 바꾼 V-only.
- EXP293/294: 각각 EXP291/292의 policy-identical frozen holdout20.
- EXP295: fast와 holdout을 모두 통과한 winner만 dev200으로 확장한다.
- EXP296: dev200 winner의 v8 field만 현재 local-quality composition에 교체하는 offline merge다.

모든 arm은 card·human-readable metadata·제품 fact 정책·모든 exact-token admitted 원문·model
parameter를 유지한다. raw law, 사례, gold label, document×v grouping, Python phrase/legal/label
rule은 넣지 않는다. V-only가 label 성능에서 승리하면 evidence recovery를 별도 serialization-only
후속으로 검증한다. evidence 후속은 source exact substring만 연결하고 v8 label을 생성·변경할 수
없으며, 그 후속이 label을 보존한다는 paired 검증 없이는 submission 후보가 아니다.

## Gates

각 paid 단계 전에 base/allowed preflight, exact tokenizer admission/source provenance, exact mock,
49열/ID/evidence validation, short/attachment/longest 및 positive rendered review, active-v8 semantic
contract를 완료한다. fast20은 `configs/dev_fast_panel_v1.json`만 사용한다.

fast의 유일한 v8 positive DEV042를 회복하고 existing-card control보다 FP/F1이 개선돼야 holdout으로
간다. holdout20에는 v8 positive가 없으므로 specificity만 평가한다. 두 cohort를 통과한 arm만
dev200을 실행하며, 최종 판단은 v8 TP/FP/FN, macro composition delta, malformed/evidence, calls와
runtime을 함께 본다. 같은 prompt 반복 투표는 이미 일반화에 실패했으므로 arm에 포함하지 않는다.

## Fast20 실행 전 검증

2026-09-15에 EXP290–292의 유료 호출 전 검증을 완료했다.

- preflight는 EXP290에서 `prompt.active_items/profile/mode`, EXP291에서
  `prompt.decision_cards_path`, EXP292에서 `prompt.output_mode`만 선언된 변화로 확인했다.
- corrected artifact는 `data/derived/decision_cards_v21_v8_operational.json`이며 incumbent 대비
  v8 한 필드만 바뀐다. builder/unit test는 평가용 실적, same-bidder AND, 지방 2인 이상 견적
  수의계약 결합, 특수기술 공사 예외를 포함하는지 검증한다.
- dev200 exact-token profile은 세 arm 모두 notices/calls 200, source documents 374/374,
  omission 0, overflow 0이다. 최대 DEV11은 existing V/E 29,517, corrected V/E 29,905,
  corrected V-only 29,831 / budget 30,268 token이다. 결과는
  `outputs/exp290-preflight/admission-dev200.json`부터 `exp292-preflight`까지 보존했다.
- exact fast20 mock은 각 `outputs/exp-290...-mock`부터 `exp-292...-mock`에 있으며 모두 20개
  unique ID, 49 ordered columns, validation warning 0이다.
- positive DEV042의 active-v8 semantic-input contract는 세 arm 모두 PASS했다. 결과는
  `outputs/exp290-semantic-audit`부터 `exp292-semantic-audit`까지 보존했다.
- rendered short DEV062, positive DEV042, long DEV169, attachment DEV194를 직접 읽었다.
  system에는 v8 item/card와 output contract가 있고 user에는 필요한 human-readable metadata,
  실제 공고문·첨부문서의 source boundary와 원문 전체가 있다. active-item 축소로 dev200 전체가
  한 context에 들어가므로 실제 overflow fixture는 없으며 longest DEV11 admission으로 대체했다.
- 위 4건에서 EXP291/292 user message SHA-256은 각각 일치했다. 즉 corrected V/E와 V-only는
  source·metadata 입력이 동일하고 system의 출력 계약만 다르다.

따라서 EXP290–292 fast20 provider 실행 요건은 충족됐다.

## Fast20 결과와 최종 판정

| 실험 | card/output | TP/FP/FN | v8 F1 | completion | 결론 |
| --- | --- | ---: | ---: | ---: | --- |
| EXP290 | existing V/E | `1/1/0` | `.666667` | 829 | control |
| EXP291 | operational V/E | `1/1/0` | `.666667` | 669 | 동률, FP 대상만 변경 |
| EXP292 | operational V-only | `1/1/0` | `.666667` | 160 | label 동률, evidence 손실 |

세 arm 모두 유일한 positive DEV042를 찾았다. existing card의 FP는 DEV049였다. 이 공고는
지역제한과 실적증명서 요구가 함께 있지만 실적 문구가 입찰 참가를 닫는 최소실적 조건인지
불명확하다. operational card는 DEV049를 0으로 고쳤지만, 실적제한이 전혀 없고 지역제한만 있는
DEV039를 새 FP로 만들었다. 즉 더 명시적인 AND 조건도 누락 사실의 환각을 막지 못했고 순수
TP/FP/FN 개선은 없었다.

EXP290/291/292는 모두 20 calls, parse error 0이고 각각 20.6/20.4/20.2초였다. V-only는 completion을
크게 줄였지만 긴 source prompt를 읽는 시간 때문에 wall time 이득이 없었다. EXP292의 positive
두 건은 e8를 생성하지 않아 validation warning 2개이며, evidence recovery를 붙일 이유가 되는
label gain도 없다.

**최종 판정: fast gate 실패로 EXP293/294 holdout과 EXP295 dev200을 실행하지 않는다.** 이 카드
문구는 source-correct 통합 artifact 후보로 보존하되 성능 정책으로 승격하지 않는다. FP 문구를
추가해 다시 조이는 dev-fit prompt, Python AND label gate, 과거 `v8_composite_merge`, 동일 prompt
반복 투표는 후속으로 사용하지 않는다.
