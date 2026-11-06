# EXP-C006 v9 target-role relation Phase A 계획

작성일: 2026-09-21

상태: offline observability audit 승인, 유료 호출 미승인

## 선택 이유

새 baseline C005D dev200은 `0.8151465658`이고 v9는 TP 3, FP 5, FN 3, F1
`0.4285714286`이다. 다른 23개 item을 고정하면

```text
Macro_new = 0.8151465658 + (F1_v9_new - 0.4285714286) / 24
```

이다.

| v9 목표 TP/FP/FN | v9 F1 | 예상 Macro | delta |
|---|---:|---:|---:|
| 4 / 3 / 2 | 0.615385 | 0.822931 | +0.007784 |
| 5 / 3 / 1 | 0.714286 | 0.827051 | +0.011905 |
| 6 / 2 / 0 | 0.857143 | 0.833004 | +0.017857 |
| 6 / 0 / 0 | 1.000000 | 0.838956 | +0.023810 |

v24는 최대 기여가 더 크지만 organizer-listed 4개 축으로 설명되지 않는 양성 2건, independent
positive holdout 부재, 이미 실패한 role-pair/proof intervention 때문에 현재 유료 재실험이
금지돼 있다. v4의 완전교정 기여는 `+0.019444`로 v9보다 작고 과거 specialist/verifier 결과가
fast/holdout에서 일관되지 않았다.

v9는 fast20과 independent holdout20에 각각 양성 1건이 있다.

- fast20 baseline: TP 0 / FP 0 / FN 1 (`PPS-DEV-051`)
- holdout20 baseline: TP 0 / FP 1 / FN 1 (`PPS-DEV-050`, FP `PPS-DEV-110`)

따라서 recall과 precision을 고정 cohort에서 단계적으로 검증할 수 있다.

## 아직 증명되지 않은 가설

현재 r10은 모델명 언급을 직접 v9 0/1로 압축한다. 오류가 다음 requirement instance 관계의 손실에서
온다는 가설을 검토한다.

```text
specific target surface
+ role = NEW_PURCHASE_REQUIRED
+ mandatory = YES
+ equivalent_or_substitute_allowed = NO
+ concrete legal/compatibility exception = NO
```

다음은 별도 0 관계다.

- 기존 설치환경·보유장비 설명
- 단순 예시·참고·평가자료
- 특정 모델과 동등 이상품 또는 실질 대체품 허용
- 호환성, 대체품 부재, 생명·건강·안전·보건위생 등 source에 구체적으로 연결된 예외
- 모델처럼 보이는 영문 토큰이 재질·규격 단위·문서 식별자일 뿐인 경우

이 관계가 실제 오류 원문을 설명한다는 증거 없이 여러 v에 공통 schema를 만들거나 유료 호출을
하지 않는다.

## Phase A 범위

Phase A는 label-blind source view와 offline audit만 만든다. final v9 label을 계산하지 않고 Gemma도
호출하지 않는다.

1. organizer 항목표 v9와 versioned card의 적용범위·1 조건·핵심 0/예외를 source ledger에 고정한다.
2. 모든 200개 공고의 모든 supplied document를 검사한다.
3. 특정 제조사·상표·규격·모델 후보와 그 주변의 필수성·동등품·호환성·예외 문맥을 unchanged
   span으로 보존하는 high-recall candidate view를 만든다.
4. Python candidate admission은 표면형 탐색만 하며 NEW_PURCHASE/EXISTING/EXAMPLE,
   mandatory/equivalent/exception 의미나 최종 v9를 결정하지 않는다.
5. dev200의 gold positive 6건과 C005D 오류 8건에서 candidate coverage와 관계 관측 가능성을
   평가한다. gold label/evidence는 selector 생성이 아니라 사후 coverage 측정에만 쓴다.
6. 특히 비어 있지 않은 gold evidence가 4k context 밖에 있던 `PPS-DEV-09`, `012`, `023`의
   규격서 source가 exact candidate로 보존되는지 검사한다.
7. fast positive `051`, holdout positive `050`, holdout FP `110`, 나머지 FP `104/108/152/180`,
   FN `052`를 사람이 full source와 함께 읽어 relation failure ledger를 작성한다.

## Phase A 산출물

- clean module: `src/pps_ai/views/v9_targets.py`
- clean audit entrypoint: `scripts/audit_v9_target_role_phase_a.py`
- unit tests: source order, all-document inspection, exact span/hash, overlap merge, no label access
- ignored output:
  `outputs/clean-exp-c006-v9-target-role-phase-a/`
  - `source_coverage.json`
  - `candidate_ledger.json`
  - `error_review_packets/`
  - `observability_report.json`
- tracked result:
  `docs/clean_exp_c006_v9_target_role_phase_a_result.md`

## Phase A gate

다음을 모두 만족해야만 typed observation 실험을 별도 계획한다.

- supplied documents inspected: 374/374
- all six v9 positives have at least one relevant exact candidate
- all nonempty gold evidence relevant to v9 is contained in or traceably adjacent to a candidate
- fast positive 051과 holdout positive 050 모두 relation operands가 실제 source에 관측 가능
- FP/FN 8건의 오류 중 다수가 단순 keyword 유무가 아니라 role/mandatory/equivalent/exception
  관계 차이로 설명됨
- candidate count와 token upper bound가 notice-level one-call 또는 명시적 overflow로 완전 수용 가능
- notice ID, gold evidence 문구, 특정 제조사/모델 목록을 admission regex나 final rule에 넣지 않음

gate를 통과하지 못하면 v9 LLM schema를 만들지 않는다. 특히 특정 error notice의 모델명을 Python
예외로 넣거나, 첨부 문서를 다시 누락하거나, 여러 문서 pass를 OR label merge하는 구조로 우회하지
않는다.

## Phase B가 승인될 경우의 최소 형태

각 candidate마다 Gemma가 source-only로 다음만 구조화한다.

- target role: `NEW_PURCHASE / EXISTING_ENVIRONMENT / EXAMPLE_OR_REFERENCE / OTHER / UNKNOWN`
- specificity: manufacturer/trademark/model/specification surface
- mandatory purchase/use
- equivalent/substitute actually allowed
- compatibility or no-substitute fact
- concrete statutory necessity fact
- exact quote

Python은 organizer truth condition의 명시식만 계산하고, unresolved positive evidence는 baseline v9로
fail-closed한다. fast20은 TP 1, FP≤1, invalid 0을 요구하고, holdout20은 TP 1, FP≤1, invalid 0을
요구한다. 두 cohort가 모두 같은 방향일 때만 dev200을 실행한다. 이 Phase B 조건은 Phase A 결과
뒤 별도 fully resolved manifest/plan으로 다시 승인해야 한다.
