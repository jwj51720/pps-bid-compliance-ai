# Clean EXP-C007B v4 requirement view B1 result

작성일: 2026-09-21

상태: **PASS — source/admission gate**, paid final-owner 실험은 아직 미실행

## 결과

새 native v4 view는 frozen/legacy 구현 없이 모든 제공 문서를 label-blind로 스캔했다.

| 검사 | 결과 |
| --- | ---: |
| records | 200 |
| documents inspected | 374/374 |
| candidate notices | 109 |
| exact candidates | 446 |
| v4 positives with candidate | 6/6 |
| nonempty gold evidence covered | 5/5 |
| baseline errors with candidate | 7/7 |
| actual fixed-prompt tasks | 109 |
| overflow passes | 0 |
| prompt tokens min / p95 / max | 1,048 / 8,206 / 13,321 |
| prompt budget violations | 0 |
| LLM calls / final decisions | 0 / 0 |

초기 350자-before/650자-after window는 candidate-only 최대 14,165 tokens라 fixed prompt를 더하면
위험했다. label을 보지 않고 admission만 근거로 after window를 500자로 줄였다. 이후에도 양성
candidate 6/6, nonempty evidence 5/5, 오류 candidate 7/7 coverage가 유지됐고 실제 fixed prompt
포함 최대가 13,321로 내려갔다. 따라서 문서 split이나 후보 overflow 없이 공고당 최대 한 번의
v4 specialist call로 실행 가능하다.

## exact rendered input 검토

다음 실제 system/user/schema를 직접 읽었다.

- short:
  `outputs/clean-exp-c007b-v4-requirement-view-audit-v1/rendered_inputs/short_PPS-DEV-061__p01.json`
- attachment:
  `outputs/clean-exp-c007b-v4-requirement-view-audit-v1/rendered_inputs/attachment_PPS-DEV-03__p01.json`
- largest:
  `outputs/clean-exp-c007b-v4-requirement-view-audit-v1/rendered_inputs/largest_PPS-DEV-11__p01.json`

검토 결론:

- candidate ID, doc type/ID, exact offsets와 원문이 모두 보인다.
- 참가자격, 평가/가점, 서식, 계약 후 이행조건의 역할 구분이 명시돼 있다.
- 특정 발주기관군, 좁은 특정사업, 일반 유사실적, 민간·동등 허용, 구체적 필요가 서로 다른
  field로 보존된다.
- final v4를 모델에 직접 묻지 않고 candidate별 사실만 출력한다.
- largest 공고의 평가표·서식·과업 중 우연히 등장한 `실적`도 누락하지 않되 role로 배제할 수 있다.
- semantic-contract 자동 검사도 PASS다.

## 구조적 의미

기존 단일 `q/r/e/id`와 달리 새 schema는 다음 관계를 같은 candidate key에 묶는다.

```text
role + mandatory + restriction + allowance + necessity + exact positive quote
```

따라서 서로 다른 문서의 참가자격과 평가표, 허용 문구, 필요 사유를 교차 결합할 수 없다.
negative candidate는 quote를 출력하지 않아 19개 후보가 있는 최대 공고에서도 completion 낭비를
줄인다. positive predicate에 들어가는 후보만 1~500자 exact quote가 필수다.

## 남은 semantic conflict

organizer 항목명에는 “고시금액 이상”이 있으나 dev 양성 6건 중 4건은 일반 2.3억원 미만이다.
새 relation prompt는 이 충돌을 임의 해결하지 않고 금액 scope를 관계 관측에서 분리했다. 이는
source view와 relation schema를 검증하는 데는 타당하지만, 완결된 final v4 정책이라고 부르기에는
부족하다.

다음 유료 단계는 동일 response에서 다음 두 reducer를 별도 0-call replay할 수 있도록 설계한다.

1. relation-only diagnostic: role/restriction/allowance/necessity의 표현력 측정
2. organizer-title gate: human-readable 입찰추정가격과 적용 threshold를 포함한 완결 정책

두 결과를 섞어 하나의 성공으로 보고하지 않는다. fast20과 holdout20에서 relation observation의
품질을 먼저 확인한 뒤, threshold 충돌을 어떤 canonical 계약으로 해석할지 별도 결정한다.

## 재현

```bash
.venv/bin/python scripts/preflight_experiment.py \
  --config experiments/manifests/clean_exp_c007b_v4_requirement_view_audit_v1.json \
  --output outputs/clean-exp-c007b-v4-requirement-view-audit-v1/preflight.json
.venv/bin/python scripts/audit_v4_requirement_view.py
.venv/bin/python -m pytest -q
```

- manifest preflight: PASS, undeclared difference 0
- tests: 80 passed
- output:
  `outputs/clean-exp-c007b-v4-requirement-view-audit-v1/`

