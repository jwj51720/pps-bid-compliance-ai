# Clean EXP-C007 v4 requirement-relation Phase A plan

작성일: 2026-09-21

## 1. 목적과 기준선

현재 로컬 품질 기준선은 `clean-exp-c005d-v19-dev200-promotion-v1`이다.

- dev200 Macro positive-F1: `0.8151465658238104`
- v4: TP 4 / FP 5 / FN 2 / F1 `0.5333333333333333`
- v4 오류: FP `04, 10, 109, 123, 137`; FN `042, 053`
- 다른 23개 항목은 이번 Phase A에서 변경하지 않는다.

전체 점수는 24개 항목 F1의 산술평균이므로 v4만 바뀔 때

```text
Delta Macro = (F1_new(v4) - 0.5333333333333333) / 24
```

이다. 완전 교정 시 이론상 `+0.0194444444`, 예상 Macro `0.8345910103`이다.
하지만 먼저 이미 저장된 v4 관측이 그 교정을 표현할 수 있는지 0-call로 검증한다.

## 2. 선행 관찰과 가설

Frozen r10은 v4에 다음 네 값을 출력한다.

- `q`: 실적이 실제 참가자격인가
- `r`: 특정 기관군 또는 불필요하게 특정한 실적인가
- `e`: 민간·해외·동등 실적 허용 예외가 있는가
- `id`: 양성/Y 사실을 대표하는 단일 source section

Frozen reducer는 `q AND r`만 사용하고 `e`를 사용하지 않는다. 그러나 저장된 dev200 응답을
직접 집계하면 단순 `q AND r AND NOT e`는 TP/FP/FN `2/2/4`, F1 `0.4`가 된다. 현재보다
Macro가 약 `0.005556` 하락한다. `e=Y`인 현재 true positive가 3건이라서 `e`를 빠진 부정
조건으로 해석할 수 없기 때문이다.

또한 v30 카드에는 일반 물품·용역의 입찰추정가격 `2.3억원` gate가 있으나, dev200 v4 양성
6건 중 `042, 053, 059, 062` 네 건은 입찰추정가격이 2.3억원 미만이다. 따라서 이 gate를
기계적으로 적용하면 dev200 recall의 이론적 상한은 `2/6`이다. 이는 threshold를 무시하겠다는
결론이 아니라, organizer 항목명과 관측 label의 충돌을 해결하지 않은 채 Python hard gate나
prompt instruction으로 승격하지 않는다는 뜻이다.

Phase A 가설은 다음과 같다.

> v4의 남은 오류는 단일 `q/r/e/id`가 서로 다른 요구 인스턴스와 문서 역할을 한 셀에
> 압축하면서 생긴다. 특히 참가자격, 평가표, 증빙 양식, 구체적 허용 필요성, 민간·동등실적
> 허용을 분리하지 못한다. 먼저 저장 응답과 exact source를 연결해 이 표현 한계를 입증해야
> 하며, 입증되기 전에는 새 prompt나 reducer를 만들지 않는다.

## 3. Phase A: offline provenance replay

### base와 허용 변경

- quality base: `clean-exp-c005d-v19-dev200-promotion-v1`
- response source: `clean-reference-l41-openrouter-dev200-v1/responses/r10`
- frozen artifact: hash-pinned `dist/reference/submit.zip`, isolated loader로만 읽는다.
- `experiment.base_config`:
  `experiments/manifests/clean_exp_c005d_v19_dev200_promotion_v1.json`
- `allowed_policy_changes`: 없음
- LLM calls: 0
- final label changes: 0
- legacy import/실행/복사/생성: 0

Phase A는 새 판정 정책이 아니라 관측 가능성 감사다. label은 모든 source view와 저장 응답을
연결한 뒤 오류 선택·지표 계산에만 사용한다.

### 산출물

1. 200개 r10 response의 v4 `q/r/e/id` parse ledger
2. `id`를 frozen prepared source pool의 exact section으로 연결한 provenance ledger
3. 모든 gold positive와 baseline error에 대한 review packet
4. 다음 counterfactual confusion matrix
   - baseline C005D
   - stored `q AND r`
   - stored `q AND r AND NOT e`
   - 일반 2.3억원 hard gate의 recall ceiling
5. 입력·label·baseline·response directory·reference ZIP의 hash/coverage

`id=null`은 source 불일치가 아니라 관측 부재로 기록한다. `id`가 존재할 때 pool에 없거나
원문 document에 귀속되지 않으면 Phase A는 실패한다.

### gate

Phase A PASS 조건:

- 입력/label/baseline/r10 response ID가 정확히 200건으로 일치
- r10 v4 parse-valid 200/200
- non-null source ID가 prepared pool에 100% 연결
- 연결 section이 같은 notice의 제공 문서에 100% 귀속
- counterfactual과 오류 review packet이 재현 가능하게 저장
- `pytest` 전체 통과

## 4. Phase B 승격 조건

Phase A source review에서 최소 두 종류 이상의 오류가 아래처럼 실제로 확인될 때만 Phase B를
설계한다.

1. `q` role 오류: 평가표·가점·증빙 양식을 참가자격으로 오인
2. `r` relation 오류: 일반 동종 실적과 특정기관/특정명칭 실적을 혼동
3. necessity 오류: 계약 목적상 구체적 필요가 있는 좁은 실적 제한을 무조건 위반으로 오인
4. multi-instance 오류: 한 문서의 서로 다른 실적 조항을 단일 `id`로 압축

Phase B가 필요하면 v4 하나에만 다음 최소 schema를 쓴다.

```text
requirement_id
source_id
role = QUALIFICATION | EVALUATION | FORM | EXAMPLE | UNKNOWN
restriction = ISSUER_CLASS | SPECIFIC_WORK | GENERAL_SIMILAR | NONE | UNKNOWN
allowance = PRIVATE_ALLOWED | EQUIVALENT_ALLOWED | NOT_STATED | UNKNOWN
necessity = CONCRETE | NOT_STATED | UNKNOWN
```

Gemma는 source-only typed observation만 만들고 final `v4`를 직접 내지 않는다. Python은 exact
source와 enum/schema를 검증하되 문장 역할·필요성을 keyword로 판정하지 않는다. 한 요구
인스턴스가 `QUALIFICATION`이고 제한 관계가 명확하며 허용/필요성 조건까지 organizer 계약에
부합할 때만 final predicate를 계산한다. selector 미탐지는 baseline v4로 fail-closed한다.

## 5. Phase B 이후 검증 순서

1. fully resolved manifest와 `allowed_policy_changes` 작성
2. exact rendered message 세 종류와 24-item semantic-input contract 감사
3. tokenizer admission, source coverage/provenance, mock, isolated output 확인
4. fast20: baseline v4 TP/FP/FN `2/0/1`; 최소 TP 2 유지, FN 증가 0, 다른 v 변화 0
5. holdout20: baseline v4 `0/0/1`; 최소 FN 0 또는 구조적 실패를 기록, 다른 v 변화 0
6. dev200: 최소 F1 `>0.533333`, 목표 TP/FP/FN `>=5/<=2/<=1`

목표 `5/2/1`이면 v4 F1은 `10/13 = 0.769231`, 예상 전체 Macro는 약 `0.824975`다.
Phase A 결과가 이 schema를 정당화하지 못하면 유료 호출 없이 C007을 중단한다.

