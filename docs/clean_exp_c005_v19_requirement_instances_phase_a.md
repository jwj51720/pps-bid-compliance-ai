# EXP-C005 v19 requirement-instance Phase A 검증

실행일: 2026-09-21  
결론: **PASS — 고정 fast20 provider 실행 승인**

## 구현 경계

- 구현 commit: `764b689` (`exp-c005: add v19 requirement instance pipeline`)
- manifest:
  `experiments/manifests/clean_exp_c005_v19_requirement_instances_v1.json`
- manifest SHA-256:
  `d0a6a383b781ce75467254c18d846331ebc081e83dd1ca7d6cfe7e86f74830ff`
- C004S base submission SHA-256:
  `28c18cd6bc524dfa937898ada46363c04236d392f28c71297d1ce7373b50680f`
- active code는 `src/pps_ai`와 clean script만 사용한다. 새 코드/테스트에서 legacy 문자열과 import는
  0건이다.
- frozen L41은 C004S의 저장 final row를 받는 격리 baseline 역할만 하며 C005 판단 코드로
  import하거나 복제하지 않았다.

## policy preflight

`scripts/preflight_experiment.py`가 PASS했다. C004S 대비 effective differences는 선언한 다음 경로뿐이다.

- `layers.views`
- `layers.decisions`
- `layers.assembly`
- `v19_policy`
- `runtime.expected_calls_per_record`

Provider model, temperature, token limit, source data, v3 owner와 reducer, 다른 23개 owner, evidence
validation은 변하지 않는다.

## dev200 source/provenance/tokenizer audit

경로:
`outputs/clean-exp-c005-v19-requirement-instances-v1/dev200/`

| 항목 | 결과 |
| --- | ---: |
| notices | 200 |
| supplied documents inspected | 374 / 374 |
| uninspected documents | 0 |
| candidate notices | 165 |
| exact candidates | 372 |
| v19 gold-positive selector coverage | 6 / 6 |
| logical candidate passes | 165 |
| natural overflow passes | 0 |
| prompt token min / p95 / max | 1,336 / 6,725 / 9,344 |
| prompt budget | 14,848 |

모든 candidate는 doc_id, 문서 유형, document order, 원문 offset, exact text SHA-256을 가진다.
공고문 → 규격서 → 과업지시서 → 제안요청서 → 예외공표서의 organizer order는 입력 record의
순서를 그대로 보존한다. 후보가 없는 35건은 source absence로 확정하지 않고 C004S v19를
유지한다.

Dev200에는 실제 overflow가 없다. 이를 overflow 사례인 것처럼 표시하지 않았다. 대신
`tests/test_v19_requirement_experiment.py`가 제한 budget에서 세 candidate를 두 pass로 나누고
ID 순서와 coverage를 하나도 잃지 않는지를 검증한다.

## rendered-input human review

읽은 exact rendered paths:

- short complete:
  `outputs/clean-exp-c005-v19-requirement-instances-v1/dev200/rendered_inputs/short_PPS-DEV-077__p01.json`
- attachment:
  `outputs/clean-exp-c005-v19-requirement-instances-v1/dev200/rendered_inputs/attachment_PPS-DEV-04__p01.json`
- largest:
  `outputs/clean-exp-c005-v19-requirement-instances-v1/dev200/rendered_inputs/largest_PPS-DEV-063__p01.json`
- FN/FP error panel 11건:
  같은 디렉터리의 `error_panel_PPS-DEV-*.json`

사람이 읽은 결론:

1. system은 final v19를 요구하지 않고 candidate별 사실만 요구한다.
2. 외부 이행보장, 지위·진품 증명, 입찰자 자기확약의 역할 경계가 명시돼 있다.
3. 입찰 전 보유, 입찰/제안 동시 제출, 적격심사·계약 후 제출이 독립 field로 보존된다.
4. user에는 compact organizer truth condition과 실제 공고 exact span, doc_id/type/offset/hash가 있다.
5. attachment 사례는 공고문·과업지시서·제안요청서 세 문서를 모두 검사하고 네 candidate를
   순서대로 렌더했다.
6. largest 사례는 candidate 6개, 9,344 tokens로 budget 안이며 schema key도 6개와 일치한다.
7. FN `PPS-DEV-036`은 제조사 A/S확약서의 입찰 마감 전 보유와 계약 후 제출을 한 candidate에
   함께 보존한다.
8. FP `PPS-DEV-050`은 적격심사 시 제출, `096`은 제출 가능 표현, `152`는 제조자/대리점
   증명, `158`은 계약상대자의 자기확약이 각각 같은 candidate 안에서 구별 가능하다.

`semantic_contract.json`은 rendered task 14개에서 적용 전제, 두 1 조건, 네 핵심 0 조건,
candidate ID completeness, no-final-label contract를 모두 PASS했다.

## exact mock

Dev200 mock 경로:
`outputs/clean-exp-c005-v19-requirement-instances-v1/dev200-mock/`

- 200 unique rows, ordered 49 columns
- 165 mock structured responses, invalid 0
- non-v19 changed cells 0
- evidence validator label mutation 0
- C005 v19 positive-without-evidence 0
- candidate가 없는 35건만 명시적 baseline fallback

Mock의 v19 label은 모두 neutral observation이라 quality 결과가 아니다. Mock Macro `.783897`은
전략 성능으로 사용하지 않는다.

Fast20 preflight/mock도 동일하게 PASS했다.

- 20 notices, candidate notices 17, exact candidates 40
- candidate calls 17, overflow 0
- token max 6,552
- invalid 0, non-v19 changed cells 0, C005 positive-without-evidence 0
- output:
  `outputs/clean-exp-c005-v19-requirement-instances-v1/fast20-mock/`

## tests와 명령

```bash
python -m pytest -q
python scripts/preflight_experiment.py \
  --config experiments/manifests/clean_exp_c005_v19_requirement_instances_v1.json
python scripts/run_v19_requirement_experiment.py \
  --config experiments/manifests/clean_exp_c005_v19_requirement_instances_v1.json \
  --cohort dev200 --preflight-only
python scripts/run_v19_requirement_experiment.py \
  --config experiments/manifests/clean_exp_c005_v19_requirement_instances_v1.json \
  --cohort dev200 --mock
python scripts/run_v19_requirement_experiment.py \
  --config experiments/manifests/clean_exp_c005_v19_requirement_instances_v1.json \
  --cohort fast20 --preflight-only
python scripts/run_v19_requirement_experiment.py \
  --config experiments/manifests/clean_exp_c005_v19_requirement_instances_v1.json \
  --cohort fast20 --mock
```

Regression suite: **52 passed**.

## paid gate

가설에 필요한 source view, keyed schema, reducer, owner-only merge, tokenizer admission, rendered
review, semantic contract, exact mock가 모두 구현·선택됐다. 따라서 다음 한 단계만 허용한다.

```bash
python scripts/run_v19_requirement_experiment.py \
  --config experiments/manifests/clean_exp_c005_v19_requirement_instances_v1.json \
  --cohort fast20
```

17 candidate calls만 실행한다. 결과가 계획의 `TP>=1, FP<=1`, invalid/fallback gate를 통과하지
못하면 holdout을 실행하지 않는다.
