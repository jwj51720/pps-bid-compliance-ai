# S002 — 지방계약 지역제한 금액·원문 역할 무호출 실험

기준 manifest: `experiments/manifests/clean_exp_s002_regional_threshold_audit_v1.json`

상태: **진단 실험 PASS, 제출 정책 미승격**. 새 API 호출은 0회다. 공식 공지의 금액을
source-grounded fact로 옮기고 현 제출 S001에 반사실 적용했지만, 기존 source predicate를
금액만 바꿔 재사용하면 비라벨 공고에서 명백한 역할 오탐이 발생한다.

## 가설과 변경 통제

- base: `clean_exp_s001_integrated_v3_v19_v1.json`
- 허용: `layers.facts`, `layers.views`, `layers.decisions`,
  `regional_threshold_policy`만.
- 공지 보정 대상은 **지방계약 v5·v6·v7**이다. 국가계약과 v2·v14~v16의 별도
  금액 선택기는 바꾸지 않았다. 실제 공고의 지역제한 여부 및 근거는 공고 문서의
  참가자격 조항에서 확인해야 한다.
- exact source predicate 비교를 위해 hash-pinned L41 loader만 사용했다.
  `legacy/pipeline_v1_20260921` import·실행은 없다. 이 단계는 frozen predicate
  의존을 제거한 독립 최종 owner 구현이 아니므로 clean-room 전환 완료라고 주장하지 않는다.
- 새 prompt/LLM/merge/serialization 변경은 없어서 tokenizer·rendered prompt 유료 gate는
  이번 **0-call audit**에 해당하지 않는다. 새 유료 prompt 실험 전에는 별도로 완료해야 한다.

## dev200 결과

| 구분 | 건수 |
|---|---:|
| 전체 | 200 |
| 지방계약 | 116 |
| 공식 금액 확정 | 65 |
| 기관 유형 등 불명 — 기존 셀 유지 | 51 |
| 국가계약 — 보정 비대상 | 84 |
| 확정 3.3억/3.5억/5억 | 1 / 5 / 59 |
| v5·v6·v7 최종 라벨 변화 | 0 |

S001 대비 dev200 Macro positive-F1은 동일한 `0.8151465658`이다. v5
`TP/FP/FN=7/0/0`, v6 `6/1/0`, v7 `7/0/0`도 동일하다. fixed fast20과
independent holdout20 역시 기존 S001 결과와 셀 단위 동일하다. 이는 새 공지에
맞는 경계 사례가 dev200에 없다는 뜻이지, 기존 금액 선택기가 맞았다는 뜻이 아니다.

신규 source view는 dev 양성에서 v5 참가자격 후보를 `7/7`건 찾았다. v6은
`4/6`, v7은 `6/7`뿐이다. 따라서 신규 detector로 기존 양성을 일괄 교체하면
재현율이 깨진다. S002는 새 양성에만 role guard를 걸고 기존 양성은 보존했다.
금액 비교는 v5 `price >= threshold`, v6·v7 `price < threshold`로
경계값 양쪽을 단위 테스트했다. 가격은 organizer `입찰추정가격` 정수 원 단위다.

## 비라벨 20,000건 스트레스 테스트

지방계약 12,485건 중 금액 branch 확정 8,936건, 불명 3,549건이다. 기존
금액 gate와 공식 금액 gate가 다른 notice-item은 v5 18, v6 606, v7 18건이다.
기존 source predicate까지 그대로 재사용하면 실제 셀 변화는 v5 `0→1` 2건,
v6 `0→1` 9건이다.

변화 11건의 원문 후보를 전부 검토했다.

- v5의 2건은 지역업체 참여도/가점 등 **평가** 문맥이지 참가자격 제한이 아니다.
- v6의 9건 중 6건은 배출현장·운반거리·낙찰 후 지역업체 이용 등 참가자격이
  아니고, 3건은 지역 참가자격이지만 **시·도 단위**라서 시·군·구 축소 위반이 아니다.
- 이 검토는 비라벨 source의 역할 판독이지 대회 정답 라벨이 아니다.

새 양성에만 `참가자의 본점/주된 사무소/영업소 소재지 제한` source clause를
요구하고, 신규 v6 양성에는 같은 clause 안의 기초지역 표식을 추가로 요구하자
위 11건의 라벨 변화는 **0건**이 됐다. 숫자 보정 자체는 source-correct하지만
기존 source predicate를 그대로 쓰는 후보는 FP 위험으로 기각한다. 보호 gate는
반대편의 FN 위험이 있어 아직 승격하지 않는다.

## 재현 및 남은 검증

```bash
python scripts/preflight_experiment.py --config experiments/manifests/clean_exp_s002_regional_threshold_audit_v1.json
python scripts/audit_regional_thresholds.py
python scripts/audit_regional_threshold_unlabeled.py
python -m pytest -q
```

무호출 산출물은 `outputs/clean-exp-s002-regional-threshold-audit-v1/`에
`preflight.json`, `fact_ledger.json`, `audit_report.json`,
`submission.counterfactual.csv`, `unlabeled_coverage.json`,
`unlabeled_predicate_change_review.json`으로 격리했다. 비라벨 source 원문은
Git에 넣지 않는다.

다음 유료 단계는 임의의 200-call 확장이 아니라, ① dev의 v6 누락 2건과
② 비라벨 경계 11건을 기준으로 동일 조항의 **참가자격 역할·기초지역 역할**
표현 가능성을 확인하는 4~8-call source-only micro다. 먼저 exact rendered
input 세 종류와 v5/v6 semantic-input contract, tokenizer admission, mock,
응답 체크포인트/중간 report를 구현해야 한다. micro는 schema·역할 표현
진단일 뿐 F1 결과로 부르지 않는다. 통과 후보만 fixed fast20 → 독립 holdout20
→ dev200으로 확대한다. evaluator vLLM 2시간 완주와 제출 ZIP 동작은 여전히
검증되지 않았다.
