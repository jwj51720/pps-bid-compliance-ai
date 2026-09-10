# EXP123 다중 호출 A0/A1 분석 결과

작성일: 2026-09-09 (dev / mac)

## 실행 범위

이 분석은 `scripts/audit_exp123_multicall.py`로 실행했다. dev-200의 notice와
organizer source/card만 읽었고, dev label·기존 prediction·외부 LLM·제출 runtime은
읽거나 호출하지 않았다.

재현:

```bash
.venv/bin/python scripts/audit_exp123_multicall.py \
  --output-dir outputs/exp123-multicall-audit-v1
```

전체 machine-readable 결과는 ignored
`outputs/exp123-multicall-audit-v1/exp123_multicall_audit.json`에, 사람이 읽는
보고서는 같은 경로의 `exp123_multicall_audit.md`에 있다.

## 확인된 EXP123 소유권

- 모든 v1–v24에는 card v6가 system prompt에 실제 렌더링된다.
- v2/v3/v21만 archived `frozen_rules.py`가 전체 `record["docs"]`를 읽어 final
  label/evidence를 덮어쓴다.
- 나머지 21개는 Gemma V/E가 final owner다.
- 모델에 넣는 ordered 4,000-character context는 dev-200의 공고문 200건을 모두
  포함하지만, 존재하는 규격서 56건·과업지시서 53건·제안요청서 56건은 모두 그
  뒤에서 omitted 된다. 이 사실은 EXP123 frozen rules가 full source를 읽는 세
  item에는 적용되지 않지만, 나머지 Gemma item에는 그대로 적용된다.
- **새로 확인한 rendered-input 불일치:** card v6의 v10–v13은 “제공된 경쟁제품
  조회”를 전제로 하지만 EXP123은 `competition_products_file: null`이므로 이 조회
  결과를 실제로 주입하지 않는다. v10/v11/v16/v18/v20은 “모든 문서” 부재검토를
  지시하지만 4k single input에서 첨부문서가 있는 dev-200 record에서는 그 조건을
  충족하지 못한다.

따라서 organizer minimum baseline만 보고 EXP123의 input gap을 논하면 안 된다.
특히 v2/v3/v21은 새 multi-call prompt의 “미처리 항목”이 아니다.

위 불일치는 EXP123 public score가 무효라는 뜻은 아니다. 그러나 B/C가 card v6를
그대로 재사용하면 모델에게 존재하지 않는 경쟁제품 조회 또는 보지 못한 전체문서를
확인하라고 다시 지시하게 된다. 따라서 B/C paid prompt 전에는 **CSV를 새로 넣을지**와
별개로, card 문구가 실제 supplied input만 언급하도록 versioned prompt-policy 결정을
명시해야 한다. 기존 CSV reinjection의 부정적 관측을 이유로 이 문제를 숨기거나,
반대로 곧바로 CSV를 다시 넣어서는 안 된다.

## 다중 호출 topology 결과

| 구조 | calls/notice | optimistic anchor | guarded anchor | 판정 |
| --- | ---: | ---: | ---: | --- |
| A: 3 disjoint semantic groups | 3 | 111.70분 | 140.20분 | submission 불가; analysis-only |
| B: triage → strict | 1–2 | 74.47분 | 93.47분 | 구현/fast probe 후보 |
| C: locator → final | 1–2 | 74.47분 | 93.47분 | 구현/fast probe 후보 |

optimistic은 EXP123 37분 14초를 call count에 선형 적용한 값이고, guarded는 EXP135
two-call 93분 28초를 anchor로 쓴 값이다. 어느 값도 vLLM performance proof가 아니다.

3-group A는 `qualification` (v1–v8,v21), `product_and_absence` (v10–v18),
`document_procedure_consistency` (v9,v19,v20,v22–v24)으로 label-blind하게
partition했다. 세 group은 24 item을 중복/누락 없이 한 번씩 갖고, 실제 3 fixture
message 모두에서 다른 group item이 섞이지 않았다. 그러나 group prompt마다 같은
4,000자 notice를 반복하므로 prompt char median은 각각 7,094 / 7,102 / 6,480자다.
이는 latency를 3배에 가깝게 만들기 때문에 EXP135의 재실행이 아니라 해도 제출 후보로
승격하지 않는다.

## B/C에 대한 정확한 구현 계약

### B: triage → strict

1차 triage는 final violation label이나 evidence가 아니라 각 v의 route state만 낸다.
`명시근거`, `부재검토`, `불명확`, `해당없음` 외 값은 invalid다.

- v10/v11/v16/v18/v20은 triage가 `해당없음`으로 종료하지 않는다. 전체문서 부재
  판정이므로 final stage로 항상 route한다.
- `명시근거`·`부재검토`·`불명확`은 final stage로 route한다.
- `해당없음`을 final 0으로 쓰는 것은 fast/holdout에서 positive coverage를 별도
  보고한 뒤에만 허용한다.
- malformed/missing triage item은 final stage에 route한다.
- final stage만 V/E와 source-substring evidence를 소유한다.
- final stage parse failure의 recovery call까지 있으면 worst case 3 calls가 되므로,
  그 비율과 runtime을 submission admission에 명시한다.
- EXP123 frozen v2/v3/v21 override는 final stage 뒤 동일하게 적용한다.

### C: locator → final

1차 locator는 non-absence item에 원문 unchanged substring 또는 `찾지못함`만
반환한다. 이것은 navigation signal이지 evidence나 final label이 아니다.

- absence v10/v11/v16/v18/v20은 locator outcome과 무관하게 final stage로 route한다.
- non-absence `찾지못함`을 final 0으로 쓰는 것도 B와 같은 positive-coverage gate가
  필요하다.
- final stage는 original 4k notice context를 항상 다시 받고, locator text는
  non-authoritative 보조 문맥으로만 받는다.
- EXP123 frozen v2/v3/v21 override는 final stage 뒤 동일하게 적용한다.

## 다음 구현 순서

1. B와 C의 strict JSON schema, routing/merge, malformed fallback을 **서로 독립된
   versioned config**로 구현한다. 아직 A group config를 제출용으로 구현하지 않는다.
2. API 호출 전에 short/truncation/attachment fixture의 triage, locator, final message
   template를 모두 export하고 읽는다.
3. mock으로 item routing, full-24 recovery, evidence validation, EXP123 frozen override
   순서를 검증한다.
4. 그 뒤 B와 C를 각각 EXP123-compatible fast panel에서 실행한다. 이때 dev label은
   design이 아니라 평가에만 사용한다.

이 결과는 B/C가 성능상 유리하다는 증거가 아니다. 단지 두 구조는 runtime상 탐색할 수
있고, A 3-group unconditional design은 현재 runtime guard에서 제외된다는 증거다.

## EXP123 오류 형태 후속 감사 (2026-09-09)

`scripts/audit_exp123_failure_modes.py`는 EXP120 dev-200 output에 archived
EXP123 v2/v3/v21 replacement만 적용해 EXP123의 기록된 local macro F1
`0.317797`을 재현했다. 전체 결과는 ignored
`outputs/exp123-failure-modes-v1/report.md`에 있다. gold label/evidence는
예측이 끝난 뒤 오류 분류에만 사용했다.

| 오류 형태 | 건수 | 다중 호출에 주는 의미 |
| --- | ---: | --- |
| 4k 안 gold source가 보인 FN | 19 | 문서 확장이 아니라 output-scope/판정 분리의 후보 |
| gold source가 4k 밖인 FN | 5 | source coverage 후보이나, full split/group 곱셈을 정당화하지는 않음 |
| whole-notice 부재 범위가 불완전한 FN | 10 | absence item은 locator 또는 triage에서 0 종료 금지 |
| gold evidence가 없는 FN | 47 | 이 audit만으로 위치/문서 coverage 원인을 주장할 수 없음 |
| FP | 47 | gold source가 없으므로 이 audit은 원인을 단정하지 않음 |

따라서 B/C의 stage-1 `해당없음`이나 locator `찾지못함`을 final 0으로 쓸 때는,
특히 위 19+5+10 유형과 evidence 없는 positive를 포함한 **positive coverage**를
실제 stage-1 output으로 별도 측정해야 한다. 이 표의 v별 수치를 card 또는 새
Python rule로 전환하지 않는다.
