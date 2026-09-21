# EXP-C006 v9 target-role relation Phase A 결과

작성일: 2026-09-21

상태: **STOP — observability gate 실패, 유료 호출 금지**

## 기계적 source coverage

label-blind view를 먼저 전체 dev200에 생성한 뒤 label과 C005D baseline을 사후 대조했다.

- records: 200
- supplied documents inspected: 374/374
- uninspected documents: 0
- candidate notices: 183
- exact candidates: 580
- v9 positives with any candidate: 6/6
- nonempty gold evidence exact candidate coverage: 3/3
- C005D v9 error notices with any candidate: 8/8
- LLM calls / final label decisions: 0 / 0
- tests: 67 passed

candidate-only rendered token은 min/p95/max `30 / 8,872 / 14,029`였다. 14,848 budget을 직접
넘는 notice는 없지만, max notice에는 fixed semantic prompt와 schema를 넣을 공간이 819 token밖에
없다. 따라서 Phase B를 했다면 적어도 명시적 overflow packing이 필요하며, 이 수치만으로 one-call
admission이 증명됐다고 볼 수 없다.

## 사람 검토에서 확인한 구조

관계형 역할 구분은 일부 false positive를 잘 설명했다.

- `PPS-DEV-104`, `152`: 기존 전동차에 장착된 원제품과 동일한 순정부품을 요구하는
  existing-environment/compatibility 관계다.
- `PPS-DEV-108`, `110`: 특정 제품·모델 표면은 있지만 공고가 동일·동등 이상 제품을 실제로
  허용한다.
- `PPS-DEV-180`: RAD8 표면이 반복되지만 라돈 측정이라는 건강·안전 목적과 형식승인 조건이
  함께 존재한다.

따라서 단순 모델명 keyword보다 target role, equivalent allowance, compatibility, concrete necessity를
분리하는 observation은 의미가 있다.

## gate를 깨뜨린 반증

그러나 organizer card의 기존 truth condition으로 gold label을 일관되게 재현할 수 없었다.

### 1. fast20 유일 양성은 실제 특정 모델 operand가 없다

`PPS-DEV-051`은 organizer raw record상 공고문 D0 하나만 있고 `무탈락=true`, `완전관측=true`다.
공고문에는 이동형 X선 투시장치의 일반 분류명 `C-ARM`과 “공고 규격서와 동등 이상 물품” 조건은
있지만, supplied source 안에 특정 제조사·상표·모델 또는 실제 규격서가 없다. 즉 Phase B가 요구할
`specific target surface` operand를 input에서 관측할 수 없다.

이 notice를 TP로 만들기 위해 `C-ARM`을 특정 모델로 취급하거나 참조만 된 미제공 규격서를 있다고
가정하면 organizer 항목명을 벗어나며 dev-fit rule이 된다. 따라서 fast20 TP=1 승격 gate를 정당하게
통과할 수 없다.

### 2. 동등품 허용은 positive와 negative에 모두 나타난다

- gold positive `PPS-DEV-09`, `050`, `051`에는 동등규격·동등 이상품 허용 문구가 있다.
- gold negative `PPS-DEV-108`, `110`에도 동등 이상품 허용 문구가 있다.

따라서 card의 “동등 이상품을 실제 허용하면 0”을 그대로 hard reducer로 쓰면 알려진 양성을
잃고, 반대로 무시하면 알려진 false positive를 복구하지 못한다. source scope나 typed schema만의
문제가 아니라 operational annotation과 compact legal condition 사이의 미해결 충돌이다.

### 3. 안전·건강 예외도 현재 label을 단독 설명하지 못한다

RAD8 건강측정 notice `180`은 음성이지만, 소방장비 notice `12/23`은 특정 모델 gold positive다.
“안전 관련이면 0” 같은 Python 예외는 source에 적힌 구체적 불가피성 관계를 생략할 뿐 아니라
positive도 훼손한다.

## 결론

Phase A의 exact-source selector는 coverage 도구로는 성공했지만, 계획한 v9 truth condition의
observability gate는 실패했다. 특히 independent validation에 반드시 필요한 fast positive 051이
supplied input만으로 재현 불가능하다. 다음을 하지 않는다.

- v9 typed observation paid fast20
- notice/model명별 Python 예외
- `C-ARM`을 특정 모델로 강제하는 규칙
- 미제공 attachment를 추정하는 prompt
- equivalence/health 문구를 label에 맞춰 임의로 무시하는 reducer

C005D `0.8151465658`은 그대로 quality baseline이다. v9는 organizer가 operational annotation을 더
명확히 하거나 독립 positive cohort가 생기기 전까지 닫는다.

## 재현 경로

- code: `src/pps_ai/views/v9_targets.py`
- script: `scripts/audit_v9_target_role_phase_a.py`
- ignored output: `outputs/clean-exp-c006-v9-target-role-phase-a/`
- source ledger hashes:
  - item table: `368cb41f376d8ad7edbbdf181542e6e959de356f7f70d86e72943325ecad61d9`
  - v30 card: `65c885daa2ad707d0df34a1787eb30a2be653a824ce01e7c452e16b1ac6c18e5`
