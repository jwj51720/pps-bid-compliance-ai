# Clean EXP-C007B v4 requirement-instance owner plan

작성일: 2026-09-21

## 1. 가설

C007 Phase A에서 v4 관련 원문은 오류 7건 모두 기존 view에 들어갔지만, 단일 `q/r/e/id`가
참가자격·평가·양식·허용범위·구체적 필요성을 같은 요구 단위로 보존하지 못했다. C007B는 모든
제공 문서에서 실적 요구 후보를 label-blind exact span으로 만들고, Gemma가 **후보별 요구
인스턴스**의 역할과 제한 관계만 구조화하도록 한다.

Python은 후보 admission, source 검증, enum/schema 검증, 명시 predicate 계산만 담당한다.
notice/model-specific keyword, correction table, 금액 threshold, 문장 역할 판정 규칙을 넣지 않는다.

## 2. 기준선과 수학적 기대값

- quality base: C005D dev200 Macro `0.8151465658238104`
- v4 base: TP 4 / FP 5 / FN 2 / F1 `0.5333333333333333`
- v4 완전 교정 상한: Macro `0.8345910102682548`

다른 23개 항목을 고정하면 다음과 같다.

| v4 TP/FP/FN | v4 F1 | 예상 Macro | base 대비 |
| --- | ---: | ---: | ---: |
| 4/4/2 | 0.571429 | 0.816734 | +0.001587 |
| 4/2/2 | 0.666667 | 0.820702 | +0.005556 |
| 5/2/1 | 0.769231 | 0.824976 | +0.009829 |
| 6/1/0 | 0.923077 | 0.831386 | +0.016239 |
| 6/0/0 | 1.000000 | 0.834591 | +0.019444 |

fast20 base는 TP/FP/FN `2/0/1`, holdout20 base는 `0/0/1`이다. fast의 FN과 holdout의 FN은 서로
다른 공고이므로 두 panel 모두에서 recall 방향이 맞아야 dev200으로 승격한다.

## 3. 실험 통제

- `experiment.base_config`:
  `experiments/manifests/clean_exp_c005d_v19_dev200_promotion_v1.json`
- 허용 변경:
  - v4 final owner만 `hybrid.r10 -> hybrid.native_v4_requirement_instances_v1`
  - v4 전용 source view, prompt, schema, reducer
  - v4 candidate notice에 한정된 conditional calls
- 고정:
  - 다른 23개 final label/evidence
  - v3/v19 owner와 recovery
  - model, temperature, completion limit, seed
  - retrieval, product facts, metadata facts
  - evidence validator와 CSV exporter
- legacy/frozen code는 새 v4 구현에서 import·실행·복사하지 않는다. C005D stored final row는
  comparison/fallback 입력일 뿐 새 v4 의미 판단 코드가 아니다.

## 4. 단계 B1: label-blind source observability

유료 호출 전에 active native view만 구현한다.

- 모든 제공 문서를 순서대로 전부 스캔한다.
- organizer item의 일반 표면인 `실적`, `수행경험`, `납품경험`, `이행경험` 주변 exact span을
  수집한다.
- 각 후보에 notice ID, doc ID/type/order, exact offsets, document SHA-256을 보존한다.
- 후보 수 제한을 두지 않는다. tokenizer admission 결과가 나쁘면 label을 보지 않고 span/window
  정책을 조정한다.
- 후보가 없음을 v4=0으로 바꾸지 않는다.

B1 gate:

- documents inspected 100%
- nonempty gold evidence exact coverage 100%
- 모든 gold positive에 candidate 존재
- 모든 baseline error에 candidate 존재
- prompt fixed context를 포함한 exact tokenizer budget 내이거나, label-blind overflow pack 정책을
  먼저 설계
- LLM calls 0, final label decisions 0

## 5. 단계 B2: typed observation

각 candidate마다 다음을 정확히 한 번 출력한다.

```text
source_id
role = BID_QUALIFICATION | EVALUATION | FORM | CONTRACT_PERFORMANCE | OTHER | UNKNOWN
mandatory = YES | NO | UNKNOWN
restriction = ISSUER_CLASS | SPECIFIC_WORK | GENERAL_SIMILAR | NONE | UNKNOWN
allowance = BROAD_OR_PRIVATE_ALLOWED | EQUIVALENT_ALLOWED | NOT_STATED | UNKNOWN
necessity = CONCRETE | NOT_STATED | UNKNOWN
quote
```

의미:

- `role`은 입찰 참가 박탈 조건과 평가 가점/양식/계약 후 조건을 구별한다.
- `restriction`은 특정 발주기관군, 불필요하게 좁은 특정 사업·대상·방식, 일반 동종실적을
  구별한다.
- `allowance`는 같은 요구 인스턴스에서 민간·해외·동등·광범위 실적을 실제 허용하는지 나타낸다.
- `necessity`는 계약 목적상 좁은 범위가 필요한 구체적 운영·안전·호환 사유가 source에
  명시됐는지만 나타낸다. 모델의 일반 추론으로 필요성을 발명하지 않는다.
- `quote`는 candidate exact substring이어야 한다.

Gemma는 final v4를 출력하지 않는다. 모든 candidate key가 정확히 한 번 존재하지 않거나 quote가
검증되지 않으면 해당 notice는 baseline v4로 fail-closed한다.

## 6. reducer 계약

positive proof는 같은 candidate에서 다음이 모두 확인될 때만 성립한다.

```text
role == BID_QUALIFICATION
AND mandatory == YES
AND restriction IN {ISSUER_CLASS, SPECIFIC_WORK}
AND allowance == NOT_STATED
AND necessity == NOT_STATED
AND exact quote is valid
```

negative proof는 모든 admitted candidate가 valid하고, 실제 실적 관련 candidate가 하나 이상이며,
그 후보들이 명시적으로 평가/양식/계약 후 조건이거나 일반·허용·구체적 필요 관계로 분류되어
positive predicate가 하나도 없을 때만 허용한다. `UNKNOWN`, 후보 없음, overflow 미관측이 하나라도
있으면 baseline v4를 유지한다.

금액 gate는 C007에서 organizer item title과 dev label이 충돌했으므로 이 실험에서 제외한다.
이를 넣거나 빼는 효과는 별도 정책 실험으로만 다룬다.

## 7. 검증 순서와 승격 gate

1. B1 source audit와 unit tests
2. exact rendered system/user/schema 검토
   - short complete
   - attachment notice
   - largest/overflow notice
3. 24-item semantic-input contract audit
4. mock: shape, parse recovery, evidence, non-v4 cell identity
5. fast20 paid run
   - TP `>=2`, FP `=0`, FN `<=1`
   - 목표 `3/0/0`
6. holdout20 paid run
   - FP `=0`
   - 목표 `1/0/0`
7. dev200
   - 최소 F1 `>0.533333`
   - 목표 TP/FP/FN `>=5/<=2/<=1`
   - 다른 23개 label/evidence changed cells 0

fast 또는 holdout에서 malformed, source-invalid, unrelated-cell change가 하나라도 있으면 dev200을
실행하지 않는다. B1이 coverage/admission gate를 통과하기 전에는 B2 prompt도 유료 실행하지 않는다.

