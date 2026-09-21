# Clean EXP-C007 v4 requirement-relation Phase A result

작성일: 2026-09-21

## 결론

Phase A는 **PASS**다. 유료 호출과 final label 변경 없이 frozen r10의 v4 관측 200건을 exact
source에 재연결했다. v4의 현재 한계는 관련 원문이 입력에 없어서가 아니라 단일 `q/r/e/id`가
요구의 역할과 관계를 충분히 보존하지 못해서 생긴다는 근거가 확인됐다.

따라서 기존 `e`를 reducer에 단순 추가하거나 2.3억원 gate를 Python hard rule로 넣지 않는다.
다음 유효 후보는 v4 하나에 한정된 requirement-instance observation이다.

## 실행과 재현

```bash
.venv/bin/python scripts/preflight_experiment.py \
  --config experiments/manifests/clean_exp_c007_v4_requirement_relation_phase_a.json \
  --output outputs/clean-exp-c007-v4-requirement-relation-phase-a/preflight.json
.venv/bin/python scripts/audit_v4_provenance_phase_a.py
.venv/bin/python -m pytest -q
```

- preflight: PASS, undeclared difference 0
- tests: 70 passed
- LLM calls: 0
- final label changes: 0
- output: `outputs/clean-exp-c007-v4-requirement-relation-phase-a/`

## 무결성 결과

| 검사 | 결과 |
| --- | ---: |
| input / labels / baseline / r10 responses | 각각 200/200 |
| v4 parse-valid | 200/200 |
| non-null source IDs | 36 |
| prepared source pool 연결 | 36/36 |
| 같은 notice 제공 문서의 exact substring | 36/36 |
| review packets | 11 |

입력, label, baseline, r10 response directory, hash-pinned reference ZIP의 SHA-256은
`audit_report.json`에 저장했다. label은 view와 응답을 모두 연결한 뒤 metric과 review 대상
선택에만 사용했다.

## counterfactual

| 정책 | TP | FP | FN | v4 F1 | C005D 대비 Macro 변화 |
| --- | ---: | ---: | ---: | ---: | ---: |
| C005D / stored `q AND r` | 4 | 5 | 2 | 0.533333 | 0 |
| stored `q AND r AND NOT e` | 2 | 2 | 4 | 0.400000 | -0.005556 |

`e`는 구체적 필요성 전반이 아니라 민간·해외·동등 실적 허용 여부를 묻는다. 실제 양성 중
`e=Y`가 2건이므로 이를 veto로 쓰면 recall이 크게 감소한다. frozen reducer가 `e`를 쓰지 않은
것은 코드상 dead output이지만, 그 사실만으로 `e`를 final predicate에 연결할 수는 없다.

일반 2.3억원 gate도 현재 organizer 관측과 충돌한다. v4 양성 6건 중 4건(`042, 053, 059,
062`)의 입찰추정가격이 2.3억원 미만이다. 따라서 이 gate를 기계적으로 적용한 recall 상한은
`2/6 = 0.333333`이다. 이는 threshold를 label에 맞춰 제거한다는 뜻이 아니다. 항목명의
“고시금액 이상”과 organizer label 사이의 충돌이 해소되기 전까지 어느 방향도 hard rule로
승격하지 않는다는 결론이다.

## source review에 나타난 표현 손실

아래 분류는 오류 원인을 찾기 위한 label-informed review이며, notice ID나 문구를 새 selector,
keyword 또는 correction table에 넣는 근거가 아니다.

| 오류군 | notice | 확인된 문제 |
| --- | --- | --- |
| role 오인 | 109, 123, 137 | 제안 평가표 또는 실적증명 양식을 실제 참가자격으로 `q=Y` 처리 |
| restriction miss | 042 | 실제 참가자격과 특정 대상·방식 실적이 source에 있지만 `r=N` |
| issuer relation miss | 053 | 실제 참가자격과 공공기관 발주실적 제한이 source에 있지만 `r=N` |
| generality/allowance 혼동 | 10 | 참가자격은 맞지만 넓은 수행주체·관련사업 범위를 과도한 특정실적으로 압축 |
| necessity 미표현 | 04 | 참가자격의 좁은 전문실적은 잡았지만 계약 목적상 필요 여부를 현재 schema가 표현하지 않음 |

특히 FN 두 건도 선택 source가 정확한 참가자격 조항이었다. 즉 high-recall source admission을
늘리는 것만으로 해결될 문제가 아니다. 반대로 세 role FP는 관련 source 자체는 정확히 들어갔지만
그 문서 역할을 잃었다. 기존 7-category navigation이나 단일 `id`를 반복 호출하는 방식보다,
각 실적 요구를 독립 인스턴스로 만들고 role/restriction/allowance/necessity를 같은 인스턴스에
묶는 방식이 필요한 이유다.

## 다음 결정

C007 Phase B 설계 gate는 통과했다. Phase B는 다음 경계를 지킨다.

1. v4 owner만 교체하고 다른 23개 final cell은 완전히 고정한다.
2. Python은 모든 제공 문서에서 실적 요구 후보와 provenance를 만들되 의미 역할을 결정하지 않는다.
3. Gemma는 후보별 `role`, `restriction`, `allowance`, `necessity`만 typed observation으로 낸다.
4. exact source/schema 검증 실패 또는 후보 부재는 baseline v4로 fail-closed한다.
5. 금액 threshold는 이번 실험에 섞지 않는다. 별도의 organizer-contract 해석 문제로 남긴다.
6. fast20 → independent holdout20 → dev200 순서를 지킨다.

Phase B 유료 실행 전 source coverage, rendered-input 세 종류, tokenizer admission, mock, 24-item
semantic-input contract를 별도 문서로 승인해야 한다.

