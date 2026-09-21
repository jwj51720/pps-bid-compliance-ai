# EXP-C002R v24 multi-observation preflight

검토일: 2026-09-21

## 결론

EXP-C002R은 유료 fast20 실행 전 무과금 gate를 통과했다. 선택 manifest가 계획한 v2 view/schema/
reducer를 실제로 가리키며, undeclared policy change는 없다. dev200 전체 tokenizer admission,
source provenance, rendered-input review, fast20 mock을 통과했다.

이 승인은 fast20 20회의 v24-only 호출에 한정한다. fast20 성능 gate를 통과하기 전에는 holdout20
또는 dev200 유료 실행을 승인하지 않는다.

## 1. 선택된 구현

- manifest:
  `experiments/manifests/clean_exp_c002r_v24_multi_observation_v2.json`
- base manifest:
  `experiments/manifests/reference_l41_openrouter_dev200_v1.json`
- owner change:
  `v24 llm.C24 -> hybrid.native_v24_multi_observation_v2`
- source view:
  `all-documents-table-aware-balanced-exact-windows-v2`
- reducer:
  `typed-atomic-set-and-value-comparison-v2`
- per-axis source budget: 6,850 characters
- maximum observations per axis: 8
- provider/model/generation/tokenizer budget: canonical base와 동일

`scripts/preflight_experiment.py` 결과는 PASS였다. 차이는 선언한 다음 네 경로에만 있었다.

- `layers.views`
- `layers.decisions`
- `layers.assembly`
- `v24_policy`

## 2. legacy와 label 경계

새 구현과 test를 검색한 결과 `legacy` 또는 `pipeline_v1_20260921` import/실행/경로 참조는 0개다.
view와 decision module은 dev label을 읽지 않는다. `labels_path`는 experiment runner가 호출 종료 후
metrics를 계산할 때만 사용한다.

새 active 파일은 다음과 같다.

- `src/pps_ai/views/v24_multi_observation.py`
- `src/pps_ai/decisions/v24_multi_observation.py`
- `src/pps_ai/v24_multi_experiment.py`
- `scripts/run_v24_multi_observation_experiment.py`
- `tests/test_v24_multi_observation.py`

## 3. source coverage와 provenance

dev200 전체 preflight 결과:

- notices: 200
- organizer-provided documents inspected: 374/374
- uninspected documents: 0
- exact source candidates: 1,945
- candidate의 doc ID/type/order/start/end와 실제 원문 substring 불일치: 0
- candidate가 발견됐지만 해당 문서에서 하나도 prompt에 선택되지 않은 axis-document: 0
- axis-document states:
  - `NOT_FOUND`: 614
  - `FOUND_SELECTED`: 860
  - `UNOBSERVED`: 22

`UNOBSERVED` 22개는 문서 자체의 미관측이 아니다. 같은 문서·축에서 앞선 exact candidate가 이미
선택된 뒤 source budget 때문에 후순위 중복/추가 candidate 일부가 생략된 상태다. 후보가 있는 모든
문서·축은 최소 하나 이상 선택됐다. 이 제한은 source coverage artifact에 명시적으로 남으며,
후속 성능 해석에서 완전한 full-source pass로 부르지 않는다.

view budget을 4,800에서 시작해 label을 보지 않고 generic noise term과 tokenizer admission만으로
조정했다. VAT/계약금액 일반 용례와 단독 `면허`처럼 organizer field 대조값이 아닌 후보를 제거하고,
overlap window를 2,000자 안에서 병합했다. 6,900자는 최대 prompt 14,995로 budget을 넘었으므로
채택하지 않았고, 6,850자를 최종 선택했다.

## 4. exact tokenizer admission과 call topology

dev200의 v24 task 200개를 실제 Gemma tokenizer로 계산했다.

- admitted: 200/200
- overflow: 0
- prompt tokens min: 839
- prompt tokens p95: 9,687
- prompt tokens max: 14,255
- prompt tokens sum: 1,016,853
- configured prompt budget: 14,848
- logical v24 calls: 200, 즉 공고당 1회

canonical L41의 다른 두 owner call은 이번 실험에서 재호출하지 않는다. 결과 CSV는 baseline의
v1-v23/e1-e23을 읽어 고정하고 v24/e24만 교체한다. submission 관점의 call topology는 기존 공고당
3회와 동일한 owner 수를 전제로 한다.

## 5. rendered message 사람 검토

다음 ignored artifact의 exact system/user message와 JSON schema를 직접 읽었다.

1. short complete:
   `outputs/clean-exp-c002r-v24-multi-observation-v2/dev200/rendered_inputs/short_PPS-DEV-077.json`
   - 2,254 tokens
   - friendly metadata 7개와 네 축 candidate가 모두 존재한다.
   - metadata의 지역제한 없음과 공고의 명시적 bidder-location 제한을 region candidate가 보존한다.
2. attachment:
   `outputs/clean-exp-c002r-v24-multi-observation-v2/dev200/rendered_inputs/attachment_PPS-DEV-01.json`
   - attachment가 있는 공고이며 7,453 tokens
   - 공고문과 과업지시서의 금액 후보를 모두 source ID/type/offset와 함께 보존한다.
   - 계약방식, bidder location, mandatory industry와 직접생산 문구가 같은 원문 span에 있어도
     schema가 역할별로 분리하도록 명시한다.
3. largest/overflow-source:
   `outputs/clean-exp-c002r-v24-multi-observation-v2/dev200/rendered_inputs/largest_PPS-DEV-11.json`
   - 14,255 tokens로 가장 큰 admitted prompt다.
   - 공고문·과업지시서·제안요청서의 후보가 모두 존재한다.
   - source 전체를 그대로 넣으면 긴 공고지만 table-aware candidate admission 후 budget 안에 있다.
   - 금액 table, 경쟁방식/협상방식, 지역, 업종 candidate와 provenance가 모두 읽을 수 있다.

세 message 공통 검토 결과:

- raw metadata JSON과 internal status는 없다.
- 적용계약법, 조달방식, 공고게시일자 같은 불필요한 raw field는 없다.
- 별도 법령 원문·법령 요약·case RAG는 없다. 실제 공고 원문 안의 법령 인용은 source text이므로
  그대로 유지한다.
- 최종 `y`, `different`, violation field는 schema에 없다.
- 각 축은 복수 observation 배열이며 한 후보만 고르라는 지시는 없다.
- source ID 없이 원자값을 출력할 수 없다.

## 6. v24 semantic-input contract

이번 유료 호출에서 active하게 재판정되는 항목은 v24 하나다. v1-v23은 baseline cell을 그대로
복사하므로 새 prompt contract의 대상이 아니다.

| contract element | rendered input의 exact 위치 | 판정 |
| --- | --- | --- |
| 적용범위 | system 첫 문단 + user의 모든 제공 문서 exact 후보 | 충족 |
| 1 조건 | system의 동일 organizer field용 원자값 역할 + Python typed comparison | 충족 |
| 핵심 0 조건 | amount/contract/region/industry 역할 분리 규칙 | 충족 |
| 금액 metadata | user `예산금액`, `추정가격` | 충족 |
| 계약 metadata | user `계약방법` | 충족 |
| 지역 metadata | user `지역제한 여부`, `제한지역` | 충족 |
| 업종 metadata | user `업종제한 여부`, `제한업종` | 충족 |
| notice source | source ID/doc type/doc ID/offset/exact text | 충족 |
| 복수값 표현 | 축별 array, region/codes/names 하위 array | 충족 |
| evidence provenance | reducer가 axis-matching source ID와 원문 substring을 재검증 | 충족 |

Python reducer는 다음 기계적 연산만 한다.

- 숫자의 구두점 제거와 integer 비교
- organizer 계약방법의 네 경쟁방식 canonicalization
- organizer placeholder에서 광역 지역명을 읽고 지역 집합 비교
- 4자리 organizer 업종코드 집합 비교
- source ID/axis와 출력 원자값의 source substring 검증
- positive evidence exact substring 및 500자 제한 검증

문장 역할과 공식 요구인지 여부는 Gemma observation이 소유한다.

## 7. mock과 tests

- active pytest: 26 passed
- fast20 mock records: 20
- logical calls: 20
- structured fallback: 0
- output: 49 ordered columns
- non-v24 changed cells: 0
- v24 positive without evidence: 0

mock evidence validator가 보고한 `v15: 1` positive-without-evidence는 immutable baseline cell에 이미
존재하는 상태이며 C002R owner와 무관하다. post-validation 단계에서도 v1-v23/e1-e23이 baseline과
완전히 같은지 다시 검사하도록 runner에 assertion을 넣었다.

## 8. 유료 실행 승인 범위

다음 command의 fast20 실행만 승인한다.

```bash
.venv/bin/python scripts/run_v24_multi_observation_experiment.py \
  --config experiments/manifests/clean_exp_c002r_v24_multi_observation_v2.json \
  --cohort fast20
```

승격 조건은 계획대로 `TP>=1`, `FP<=3`, fallback 0, non-v24 changed cells 0이다. 하나라도 실패하면
결과를 기록하고 중단한다.
