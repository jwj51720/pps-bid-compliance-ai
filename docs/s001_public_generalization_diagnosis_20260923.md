# S001 public 일반화 진단

작성일: 2026-09-23

## 관측

제출물 `pps_20260922_153225.zip`의 결과는 다음과 같다.

| 구분 | 값 |
|---|---:|
| stored-response dev200 Macro positive-F1 | 0.8151465658 |
| public Macro positive-F1 | 0.6053527995 |
| local-public 차이 | -0.2097937663 |
| public/local 비율 | 0.7426232891 |
| 실행시간 | 95분 27초 |
| 120분 대비 사용률 | 79.5417% |

이 결과는 두 가지를 동시에 증명한다.

1. 기존 최고 public `0.2604457110`보다 `+0.3449070885` 높으므로, bounded source
   view·구조화 사실·명시적 item owner라는 큰 구조는 실제 평가에서도 강하게 작동했다.
2. dev200을 반복적으로 보고 고른 local `0.8151465658`은 public 성능의 신뢰할 수 있는
   추정치가 아니었다. 앞으로는 이를 **adaptive-development score**라고 부르고 독립 검증
   점수라고 부르지 않는다.

사용자가 2026-09-23 전달한 대회 막바지 leaderboard snapshot에서 5위권 점수는 대략
`0.75~0.78`이다. 현재 public과의 차이는 `0.1446472005~0.1746472005`다. 24항목 Macro에서
두 specialist만 완전히 고쳐 얻을 수 있는 최대 변화 `2/24=0.0833333333`보다도 크다.
따라서 상위권 도달은 v3/v19 또는 한두 규칙의 복구가 아니라 여러 owner에 공통된 precision/recall
누수 또는 실행 환경 차이를 찾아야 한다. 이 순위 구간은 사용자 제공 시점 관측이며 공식 artifact로
독립 검증한 값은 아니다.

## v3·v19만으로는 괴리를 설명할 수 없음

기준 L41 dev200은 `0.7796736645`였고 S001의 두 specialist가 추가한 local 증가는 다음과 같다.

```text
v3  contribution = (0.9411764706 - 0.3636363636) / 24 = 0.0240641711
v19 contribution = (0.7500000000 - 0.4761904762) / 24 = 0.0114087302
sum             = 0.0354729013
```

이는 관측 local-public 차이의 약 16.91%다. 두 item만 바꿀 때 Macro 변화의 절댓값은
수학적으로 `2/24 = 0.0833333333`을 넘을 수 없다. 따라서 동일 artifact의 원 reference
public이 `0.6053527995 + 2/24 = 0.6886861328`보다 높았다면, 현재 차이는 v3/v19
교체만으로 설명할 수 없다. 다음 중 하나 이상을 별도로 검증해야 한다.

- 전달받은 reference public 관측과 현재 hash-pinned ZIP의 대응이 정확하지 않음
- OpenRouter stored response와 evaluator offline INT8 vLLM generation 차이
- 통합 submission runtime이 정상 출력에서도 base 의미 동등성을 완전히 보존하지 못함
- invalid/retry/fallback이 base item에 관측 가능한 영향을 줌

public per-item 결과와 evaluator runtime report가 없으므로 이 네 원인을 현재 점수 하나로
식별할 수 없다.

2026-09-23 S006에서 실제 제출 ZIP을 동일 dev200 원문·ranking·저장응답으로 재실행했다.
base 600개, v3 61개, v19 165개의 task hash가 모두 일치했고 S001과 49열 cell difference가
0이었다. 따라서 위 후보 중 **통합 submission의 데이터 조립·merge·evidence/package 의미 차이**는
저장응답 조건에서 기각됐다. 남는 핵심 축은 dev/test 입력·표현 분포와 OpenRouter 대 evaluator
vLLM 신규 생성 차이다. 상세는 `docs/clean_exp_s006_archive_stored_response_parity_result.md`를 따른다.

## 확인된 과적합 경로

### 1. adaptive dev200

dev200은 항목당 양성이 5~8건뿐인데 오류 ID와 원문을 반복적으로 읽고 rule, candidate view,
reducer를 선택했다. fast20은 dev label을 사용해 모든 item 양성을 포함하도록 만들었고,
holdout20도 여러 실험 결과를 확인한 뒤에는 더 이상 독립 검증셋이 아니다. 두 panel 모두
동일 dev200의 부분집합이다.

S001 정책을 고정했다고 가정한 notice bootstrap 3,000회의 순진한 95% 구간은 약
`0.7512~0.8511`이었다. public `0.6054`는 이 범위 밖이다. 이 bootstrap은 adaptive selection을
반영하지 않아 실제 불확실성을 과소평가한다. 즉 단순한 200건 표본오차만으로 괴리를
설명하기 어렵고, 선택 과적합·입력 분포·생성 환경 차이를 함께 봐야 한다.

### 2. dev 오류를 본 뒤 승격한 specialist

- v3 마지막 reducer는 알려진 FN `PPS-DEV-059`를 분석한 뒤 AGGREGATE를 허용했고 정확히
  그 한 셀을 고쳤다. organizer source상 정당한 변경일 수 있어도 선택 과정은 dev-adaptive다.
- v19는 dev 오류 11건의 발급자·의무시점·역할을 검토한 schema/reducer다. fast의 양성 1건과
  holdout의 음성 1건을 통과했지만 holdout에는 v19 양성이 없어 recall 일반화를 검증하지 못했다.

### 3. base deterministic owner의 lexical 결합

실행 시 dev label이나 `PPS-DEV-*` ID를 직접 조회하는 경로는 발견되지 않았다. 그러나 base
solver가 사용하는 다수 owner는 `run_v*_experiment`에서 선택된 exact phrase, 예외 목록,
BGE score bridge, cross-item veto를 final label에 사용한다. 이는 runtime label leakage가 아니라
model-selection leakage와 표현 분포 과적합 위험이다.

특히 위험한 계열은 다음이다.

- BGE score와 특정 query/code군을 동시에 요구하는 제품 bridge
- 공고문 same-line 또는 좁은 lexical window만으로 역할을 확정하는 detector
- v10/v11 결과로 v16/v17/v18을 다시 veto하는 cross-item 결합
- metadata 또는 candidate 부재를 실제 비적용·부재로 취급하는 판정
- dev 오류 하나를 없애도록 선택된 예외 phrase 또는 역할 veto

## 유지할 구조와 제거 대상

public `0.6054`는 전체 구조를 폐기할 근거가 아니다. 아래는 유지한다.

- organizer 문서 전체의 source scan과 exact provenance
- 금액·날짜·코드의 기계적 구조화
- item별 단일 final owner와 writer trace
- V와 evidence 검증의 분리
- 문서×item-group 곱셈이 없는 bounded call topology
- 실제 95분 27초에 완주한 batch/runtime 골격

반면 owner별 요소를 다음 세 등급으로 다시 분류한다.

1. **source-invariant:** organizer 자료로 완전히 증명되는 exact join·산술·날짜 계산.
2. **semantic candidate only:** 역할·적용성·예외처럼 후보화는 가능하지만 Python final label로
   확정하면 위험한 요소.
3. **adaptive heuristic:** dev 오류를 본 뒤 선택한 threshold·phrase·cross-item 결합. 제거 또는
   독립 의미판정 대상으로 우선 검토.

## 다음 검증 순서

1. S004와 S007 zero-call audit로 dev200과 organizer 비라벨 20,000건의 입력분포, specialist route,
   제품·기업범위 Python predicate funnel을 비교한다.
2. owner risk ledger로 24개 item의 final owner를 위 세 등급과 source provenance로 분류한다.
3. 첫 제출 ablation은 한 번에 하나만 바꾼다. v3/v19 동시 제거, 지역금액 보정, base owner
   정리는 서로 다른 실험이다.
4. exact reference public 점수·ZIP hash가 확보되면 `0.6886861328` 경계를 이용해 generation과
   specialist 효과를 분리한다.
5. 더 이상 dev200 한 셀 개선을 승격 사유로 사용하지 않는다. 비라벨 20,000건의 stratified
   source review와 organizer truth-condition provenance를 통과한 일반식만 후보가 된다.

S010은 v3 source view를 20,000건에 직접 실행해 이 우선순위를 보강했다. dev의 v3 route는
30.50%, 모집단은 20.42%였고, route된 candidate 중 평가 문구는 dev 62.0% 대 모집단 75.12%,
추정가격을 넘는 금액 표면은 48.0% 대 58.56%였다. hash 고정 모집단 route 표본 8건도 모두
평가/서식 역할이었다. 반면 AGGREGATE candidate 자체의 비율은 32.0% 대 30.69%로 안정적이어서
알려진 한 dev FN 때문에 AGGREGATE만 금지하는 rollback은 근거가 없다. 따라서 다음 public
식별 후보는 lexical reducer 보정이 아니라 S005 v3 specialist 전체 단독 제거다. 상세는
`docs/clean_exp_s010_v3_population_morphology_audit_result.md`에 기록했다.

S011은 반대 방향의 과잉수정을 막았다. v16/v17/v18 final expansion은 dev 추가 precision이 각각
62.5%/41.67%/60.0%였고 F1 개선에 필요한 임계 14.29%/14.29%/12.5%보다 충분히 높았다.
v17은 FP가 TP보다 많아도 낮은 initial recall 때문에 F1에는 유효했다. 모집단 funnel까지 결합하면
이 owner들을 통째로 초기 R2로 되돌릴 근거는 부족하다. 즉 일반화 대응은 “Python을 많이 제거”가
아니라 source-role 결함과 수학적 취약성이 동시에 확인된 overlay를 하나씩 제거하는 방식이다.
상세는 `docs/clean_exp_s011_python_owner_stage_attribution_result.md`를 따른다.

S012에서 두 번째 adaptive overlay인 v19도 같은 원칙으로 감사했다. native owner는 dev에서 base B의
FP 10건을 4건으로 줄이고 FN 1건을 제거했으며, 11개 전이 중 1→0 여덟 건이 모두 FP 교정이었다.
모집단 candidate는 자기서약·서식형 비율이 dev와 거의 같고, 외부 공급확약+입찰 표면은 dev보다
적었다. 수작업 표본도 단순 lexical positive가 아니라 발행자·역할·시점 분해가 필요한 문맥이었다.
따라서 v19의 public 성능을 입증한 것은 아니지만, 현재 분포 증거는 whole-owner 제거를 지지하지
않는다. 첫 public one-change 식별 후보는 S005 v3-only revert로 유지한다. 상세는
`docs/clean_exp_s012_v19_population_morphology_audit_result.md`를 따른다.

S013은 가장 큰 단일 headroom의 v24를 감사했다. C24의 precision은 10.20%이고 49개 positive 중
44개가 FP였다. FP 절반 이상은 네 축 모두 source/metadata comparison surface가 있었고 budget
UNOBSERVED는 FP에 농축되지 않았다. 즉 입력 누락보다 복합 문구의 우선순위와 operational annotation
범위를 direct verdict가 과잉 해석한 문제가 크다. 지역 evidence는 0 TP/13 FP였고 모집단은 지역
candidate와 복수 candidate가 dev보다 각각 12.67%p, 10.645%p 많았다. exact evidence 없는 v24
positive 네 건을 0으로 내리면 로컬 Macro가 약 `+0.000552` 오르지만, v15의 같은 상태 두 건은
모두 TP이고 C24 quote도 정규화하면 source에 대응했다. 따라서 이는 일반 correction이 아니라
dev-adaptive veto라서 기각한다. v24 prompt 재튜닝도 중단한다. 상세는
`docs/clean_exp_s013_v24_operational_surface_audit_result.md`를 따른다.

S014는 organizer 20,000건의 계약방법·1억원·첨부 분포로 S001 dev 오류를 post-stratification했다.
Macro는 0.81515에서 0.79539로 내려갔지만 실제 public 0.60535와의 차이 대부분은 설명하지 못했다.
더 중요한 one-change 비교에서 v3 specialist는 revert보다 weighted F1이 `0.9204 vs 0.2668`, v19
native는 base B보다 `0.6064 vs 0.3720`이었다. v10/v16/v17/v18 refinement도 각각 initial보다
우세했다. 따라서 최근 구조를 걷어내는 rollback은 기대 일반화 전략이 아니다. 다음은 weighted
precision이 가장 취약한 v17의 direct/<1억 relation guard와 evaluator generation robustness를
서로 분리해 검증한다. 상세는 `docs/clean_exp_s014_covariate_shift_stress_result.md`를 따른다.

S015는 동일 tokenizer task hash의 독립 OpenRouter 생성 pair를 비교했다. v3는 response content가
10건 중 5건 달랐지만 final V는 10/10 같았다. v19는 content가 17건 중 16건 달랐고 final V는
16/17 같았다. 유일한 불일치는 실제 FP인 `PPS-DEV-051`이었다. typed reducer가 생성 변동을 크게
흡수하는 구조적 성공은 확인됐지만, v19 dev F1에는 generation variance가 섞여 있고 base
r10/B/C24에는 repeat 증거가 전혀 없다. 다음은 v19 primary-positive 10건의 positive-only repeat
진단이며, 상세는 `docs/clean_exp_s015_exact_repeat_stability_audit_result.md`를 따른다.

S016/S016R은 v19 primary-positive 10건을 동일 task로 재확인했다. 새 8건 중 6건은 provider가
schema-valid JSON을 Markdown fence로 감싸 strict parse가 실패했으나, 별도 0-call
serialization-only replay에서 내부 JSON과 reducer를 그대로 보존해 모두 복구했다. consensus는
TP 6/6을 유지하면서 FP 4건 중 2건을 제거해 v19 F1 `0.75→0.85714`, Macro
`0.81515→0.81961`이 됐다. 반복 검증의 구조적 가능성은 확인됐지만 개선 폭은 public-local gap의
약 2.13%이고, test에서 약 85개 추가 호출과 두 번째 순차 wave가 예상된다. adaptive dev 결과와
95분 runtime을 고려해 즉시 submission 정책으로 승격하지 않는다. 상세는
`docs/clean_exp_s016r_json_fence_replay_result.md`를 따른다.

S017/S017R은 label/response를 보지 않고 두 source strata의 중앙 token 공고를 골라 r10/B/C24
6개 exact task를 반복했다. B/C24 네 건은 raw content까지 같았고, r10 두 건은 content가 달랐다.
r10 한 건의 JSON fence를 0-call 복구한 뒤에도 single/joint S001 V/E changed cell은 0, Macro delta는
0이었다. 따라서 작은 micro 범위에서는 base generation variance가 final로 전파된 증거가 없고 이를
public gap의 우선 원인으로 올리지 않는다. 2공고 표본은 전체 600task나 evaluator vLLM을 면책하지
않는다. 다음은 rollback이 아니라 v17 direct/<1억 relation/cross-item owner 감사다. 상세는
`docs/clean_exp_s017r_base_json_fence_replay_result.md`를 따른다.

S018은 v17 final positive 13건과 비라벨 20,000건의 같은 source detector를 직접 감사했다.
dev FP 7건 중 두 건에서는 소기업 전용 참가조건과 이번 계약에 적용되는 우선조달 예외를 각각
기존 owner가 놓쳤다. 두 건만 이상적으로 바로잡아도 raw Macro 이득은 `+0.00310`이고,
비라벨 broad/no-small 후보 1,702건의 고정 해시 표본 16건에서도 소기업 전용 네 건·예외
문장 두 건이 broad hit로 잡혔다. 반대로 dev TP 한 건에는 경쟁제품 코드와 제2조의3 문구가
함께 있어 코드/단어 veto는 위험하다. 따라서 제거 대상은 v17 owner 전체가 아니라
`표면 hit를 실제 참가범위·제품 적용성·예외 적용으로 승격하는 가정`이다. source-only 역할
관측과 원문 대조를 별도 v17 후보로 설계한다. 상세는
`docs/clean_exp_s018_v17_source_relation_audit_result.md`를 따른다.

현재 S001은 **public-validated structural baseline 0.6053527995**다. local 0.815는 회귀 검사에는
사용할 수 있지만 일반화 기대값이나 새 정책 승격 기준으로 사용하지 않는다.

S023은 이 구분의 직접적인 수학적 이유를 보였다. Python-only direct owner 여섯 개 중
다섯 개의 dev F1이 이미 1이므로, 잘못된 모집단 양성을 줄이는 보수적 변경이라도
dev200에서 한 TP를 건드리면 점수는 하락한다. 여섯 항목의 dev Macro 기여는
0.24679로 public 괴리보다 크지만 실제 public item별 기여는 미식별이다. 따라서
dev subset의 점수 상승을 필수 승격 gate로 두면 과적합 제거 후보를 구조적으로
탈락시킨다. 상세는 `docs/clean_exp_s023_dev_saturation_generalization_gate_result.md`.
