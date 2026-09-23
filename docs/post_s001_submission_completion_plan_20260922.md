# S001 제출 이후 완성 계획

작성일: 2026-09-22

2026-09-22 organizer 지역제한 금액 보완 공지를 반영해 개정했다. 공지의 source record와 현재
제출물 영향 감사는 `docs/organizer_notice_20260922_local_region_thresholds.md`에 있다.

## 1. 현재 기준

제출한 `pps_20260922_153225.zip`의 stored-response task-hash replay dev200 Macro는
`0.8151465658`이었다. 실제 public은 `0.6053527995`, runtime은 95분 27초다. 따라서 0.815는
일반화 추정치가 아니라 adaptive-development 회귀값으로만 사용한다. public 결과와 수학적
진단은 `docs/s001_public_generalization_diagnosis_20260923.md`를 따른다.

현재 구조는 완전 독립 24-owner가 아니다. v3와 v19는 active specialist가 최종 cell을 소유하고,
나머지 22개 항목은 기존 3-arm 실행의 결과를 사용한다. e는 최종 점수 최적화 대상이 아니라
양성 verdict의 원문 substring을 생성·검증하는 출력 계약으로 유지한다.

## 2. 실행시간의 수학적 진단

### 2.1 logical calls

```text
r10 200 + C24 200 + v19 owner 200 + v3 conditional 61 = 661 initial
```

기존 3-arm 600회보다 61회, 즉 `10.17%` 많다. v19 native 165회는 B 200회 위에 더한 것이
아니라 candidate notice의 B를 대체한다.

S006의 exact archive stored-response replay에서는 base invalid retry 18회, v3 invalid retry 2회,
conditional B fallback 2회가 추가되어 총 683 requests였다. 실제 evaluator 신규 생성에서는
invalid 회복 여부가 달라질 수 있으므로 661은 initial topology, 683은 dev 저장응답 replay의
관측 total로 구분한다.

### 2.2 token 근사

dev 저장 usage와 exact tokenizer count를 현재 routing에 대입하면 다음과 같다.

| 항목 | prompt tokens | completion tokens |
|---|---:|---:|
| 기존 L41 3-arm | 약 3.58M | 약 0.131M |
| S001 initial topology | 약 3.265M | 약 0.230M |

- prompt는 약 `8.7%` 감소한다.
- 저장 completion은 약 `76%` 증가한다.
- prompt+completion 단순 합은 약 `5.7%` 감소하지만, 이는 wall time 식이 아니다.

실제 시간은 다음처럼 봐야 한다.

```text
T = alpha * prompt_tokens + beta * completion_tokens
    + gamma * backend_batches + delta * recovery_calls
```

`alpha`, `beta`, `gamma`는 evaluator GPU와 vLLM scheduling에 의존한다. OpenRouter wall time으로
이를 추정하지 않는다. 특히 evaluator structured decoding은 `disable_any_whitespace=True`이므로,
OpenRouter에서 관찰된 장시간 공백 completion은 그대로 재현되지 않을 수 있다.

### 2.3 batch topology

dev200 schema grouping 기준 초기 backend batch는 대략 다음과 같다.

```text
r10 2 + C24 2 + B(no-candidate 35건) 1
+ v3 schema groups 4 + v19 schema groups 6 = 15 batches
```

기존 3-arm은 128 batch에서 6개였다. 따라서 logical call 수와 token 합이 비슷해도 schema별 batch
분절이 runtime overhead와 GPU utilization을 악화시킬 수 있다. 이번 제출의 완료 여부는 public
실행 결과가 가장 강한 증거다.

## 3. 이번 제출에서 추가로 검증해야 할 사항

1. **실제 완주 여부와 wall time**
   - 성공/timeout을 먼저 기록한다.
   - 가능하다면 runtime report의 arm별 requests, backend batches, retry calls, fallback B calls를
     보존한다.
2. **재시도 발생률**
   - initial invalid 비율 `p`일 때 retry 기대 호출은 상한상
     `N*p + N*p^2`가 아니라, 동일 task가 독립적으로 회복한다는 강한 가정이 없으므로 실제 attempt
     ledger로만 계산한다.
   - deterministic length failure라면 같은 task 2회 재시도는 회복률 0이고 시간만 늘린다.
3. **active/package source parity**
   - packager는 active module을 복사하지만 tracked submission copy가 별도로 존재한다.
   - 다음 패키지부터 ZIP 내부 각 module hash가 active source hash와 같은지 자동 검증한다.
4. **archive 자체 fault injection**
   - 현재 archive staged mock과 source-level batch/retry fault test는 각각 통과했다.
   - 다음 후보는 ZIP을 임시 해제한 코드 자체에 runner fault를 주입하여 두 검증을 한 경로로 합친다.
5. **fallback의 점수 위험**
   - run-level emergency CSV는 제출 실패를 막지만 모든 v를 0으로 내므로 품질 보장은 아니다.
   - 정상 완료율과 emergency 성공은 별도 지표로 보고한다.
6. **v5·v6·v7 공식 지역제한 금액 selector**
   - 현재 제출물은 지방계약을 5억원 또는 일부 2.3억원으로 단순화해 새 공지와 불일치한다.
   - 다음 후보는 시·도(세종 제외) 3.5억원, 교육청·학교·지방공기업 5억원, 세종·시·군·구
     5억원, 기술용역 3.3억원, 안전점검·정밀안전진단 1.5억원을 `입찰추정가격`과 비교해야 한다.
   - v2와 v14~v16의 2.3억원은 변경하지 않는다.
   - 초기 표본 37건 및 후속 S002 dev200 확정 65건에서 반사실 label 변화가 없었지만,
     public correctness를 위해 반드시 보수한다.

## 4. 다음 실험 우선순위

### P0. public 일반화 괴리를 먼저 분리하고 공식 selector 보수는 별도 준비한다

실제 95분 27초 완주는 runtime 식의 미지수에 대한 관측이다. 품질은 public 0.60535로 구조적
상승과 큰 local 괴리가 함께 확인됐다. 다음 제출에서 품질 prompt, runtime serialization,
organizer 금액 correction을 동시에 바꾸지 않는다. S004 분포 감사는 dev가 제한경쟁·협상·고액을
과대표집하고 소액수의·1억원 미만을 과소표집했음을 확인했다. S005는 첫 최소 ablation으로 v3
specialist만 제거해 dev counterfactual 0.79108과 61-call 감소를 고정했다. 아직 submission은 아니다.

정확한 우선순위는 다음과 같다.

1. original reference public score와 ZIP hash 대응 확인.
2. S005 v3-only revert의 public one-change ablation 여부 결정.
3. 모집단 다수인 소액수의·1억원 미만 strata에서 base owner의 activation/source-role 감사.
4. v5·v6·v7 공식 금액 correction은 위 ablation과 섞지 않고 별도 승격.

S007로 3번의 population funnel 감사를 수행했고 v16 source detector 누락을 확인했다. 이를 근거로
S008 V-only와 S009 관계 관측 full-source verifier를 각각 9-call micro로 실행했으나 의미 gate에
실패했다. 두 후보는 dev200으로 확장하지 않는다. 같은 micro에 세 번째 prompt 변형을 만들지 않고,
다음 품질 후보는 S005 v3-only revert의 one-change public ablation을 우선 검토한다.

### P0.5. v5·v6·v7 organizer correction

2026-09-22 S002 무호출 감사의 실제 결과는
`docs/clean_exp_s002_regional_threshold_audit_result.md`에 있다. 지방계약 dev116건 중
65건의 금액을 확정했지만 dev200 라벨 변화는 0건이었다. 비라벨 20,000건에서는 기존
source predicate에 금액만 바꾸면 11개 신규 양성이 발생했고 원문 역할 검토상 모두
참가자격 축이 아니거나 v6의 시·도 단위였다. 그러므로 아래 2번 threshold-only
counterfactual은 **진단**이지 제출 승격 근거가 아니다. 새 양성의 원문 참가자격 역할과
v6의 같은 조항 기초지역 관계를 독립적으로 증명해야 한다. source guard를 씌운 결과
20,000건에서 신규 변화가 0건이라 성능 개선도 아직 입증되지 않았다.

S002에서 공통 `regional_restriction_threshold` fact와 역할 보호 source view의 첫 버전을
구현했다. 출력은 기관유형, 용역유형, 적용금액, 각 사실의 organizer source span, 확정/불명
상태다. Python은 확정된 기관·용역 유형과 공식 표의 숫자를 대응시키는 일만 하고, 익명 기관명을
추측하거나 키워드만으로 기술용역을 법적으로 분류하지 않는다. 신규 view의 dev v6 positive
coverage가 4/6이므로 아직 제출 정책으로 승격하지 않는다.

후속 S003 8-call source-only 역할 micro는 `docs/clean_exp_s003_region_role_micro_result.md`에
기록했다. 역할 4/8, 참가자격 지역단위 2/5, invalid 1/8로 gate에 실패했다.
parser만 가진 quote 300자 제한과 prompt/schema 계약 불일치도 발견했다. 따라서 S003을
금액 selector의 신규 양성 guard나 최종 v owner에 사용하지 않는다.

검증은 다음처럼 변경을 분리한다.

1. no-call dev200 coverage audit: 기관유형·용역유형·가격 operand coverage.
2. 기존 v5·v6·v7 source predicate를 고정한 threshold-only offline counterfactual.
3. 역할·지역단위 구분의 표현 가능성을 4~8-call source-only micro로 진단한다.
4. fixed fast20 → independent holdout20 → dev200 regression.

이 correction의 최소 gate는 기존 TP 보존, 새 FP 0, unknown을 임의 label로 바꾼 건 0이다.
기관 금액뿐 아니라 신규 양성의 참가자격 역할·지역단위가 source-grounded하게 확인되어야 한다.
로컬 F1 상승이 없어도 공식 금액과 source role이 함께 정확하면 승격 사유가 된다. 단,
v5·v6·v7의 다른 Python 휴리스틱 결함까지 같은 변경에서 고치지 않는다.

### P1. timeout이면 serialization-only runtime 실험을 최우선한다

첫 후보는 v3/v19의 의미 필드와 reducer를 그대로 두고 schema만 공통 compact serialization으로
바꾸는 것이다. candidate 수마다 달라지는 keyed schema를 공통 schema로 만들 수 있으면 specialist
backend batches의 이론적 목표는 다음과 같다.

```text
v3: 4 -> 1 batch
v19: 6 -> 2 batches
전체: 15 -> 8 batches
```

이 실험의 allowed change는 serialization과 parser뿐이다. selector, prompt 의미, reducer, evidence,
base owner를 바꾸지 않는다. fast20과 holdout20에서 semantic output과 final verdict의 동등성,
malformed rate, completion tokens를 확인한 뒤 dev200으로 간다.

두 번째 후보는 v3/v19 후보 notice의 겹침 54건만 하나의 두-section specialist call로 합치는 것이다.

```text
v3 candidate 61, v19 candidate 165, overlap 54, union 172
현재 specialist calls 226 -> union calls 172
전체 initial calls 661 -> 약 607
```

이는 prompt topology도 바꾸므로 공통 serialization이 충분하지 않을 때만 별도 실험한다. 두 변경을
한 실험에 섞지 않는다. 목표는 `<= 610 initial calls`, `<= 8 backend batches`, 현재 v3/v19
final cell 불변이다.

### P2. 완주하면 품질은 item별 기대 Macro 이득으로 선택한다

현재 dev200에서 각 item을 완벽하게 고쳤을 때의 이론적 Macro 상한은 다음과 같다.

| item | 현재 F1 | 최대 Macro 상승 |
|---|---:|---:|
| v24 | 0.1754 | +0.03436 |
| v9 | 0.4286 | +0.02381 |
| v4 | 0.5333 | +0.01944 |
| v17 | 0.6316 | +0.01535 |
| v11 | 0.6667 | +0.01389 |
| v12 | 0.6667 | +0.01389 |

그러나 상한이 예상 이득은 아니다.

- **v24:** 최대 headroom은 가장 크지만 기존 실험에서 organizer operational truth가 네 축 비교만으로
  설명되지 않았다. 새 유료 호출보다 먼저 dev200 FP 44/FN 3의 label-blind source/metadata 관계표와
  organizer 항목표의 operational scope를 감사한다. 기존 multi-observation 변형을 반복하지 않는다.
- **v9:** 다음 신규 owner의 1순위다. truth condition이 특정 모델·규격 요구의 역할 관계로 비교적
  작고, 최대 Macro headroom이 두 번째로 크다. source-only audit에서 후보 recall과 문서 유형별
  coverage를 먼저 증명한 뒤 가장 작은 typed observation으로 fast→holdout→dev200을 진행한다.
- **v4:** parent scope는 fast 성공 후 holdout FN, allowance-axis는 fast FP로 기각됐다. 동일 prompt를
  더 다듬는 실험은 중단한다. 역할 분류 불안정성을 해결하는 새로운 증거가 있을 때만 재개한다.
- **v17:** 제품 코드·제품 역할·CSV 특이사항의 relation owner가 필요하다. metadata 코드 부재를
  비대상 증명으로 쓰지 않으며, v9 다음 후보로 둔다.
- **v11/v12:** 둘 다 recall 손실형이라 source absence/제품 적용 사실이 final prompt에 실제로 들어가는지
  semantic-input audit부터 수행한다.

점수 후보의 비교식은 다음으로 고정한다.

```text
DeltaMacro = (F1_candidate - F1_current) / 24
runtime_efficiency = DeltaMacro / added_initial_calls
token_efficiency = DeltaMacro / added_prompt_tokens_million
```

추가 호출 owner는 `DeltaMacro > 0`뿐 아니라 제출 2시간 제약 안에서 양의 efficiency를 가져야 한다.

### P3. 이미 결론난 native owner는 기계적으로 통합하지 않는다

- v22 native는 dev200 F1 1.0이지만 현재 base v22도 F1 1.0이어서 즉시 추가하면 점수 이득 0,
  runtime 비용만 증가한다.
- v2 native N008은 F1 0.8235와 invalid 20건으로 현재 base F1 1.0보다 낮아 통합하지 않는다.
- v3/v19는 현재 결과를 유지하되 no-candidate/fallback을 순수 native라고 부르지 않는다.

## 5. 빠른 API 중간결론 운영 규칙

남은 기간에는 완성될 때까지 유료 호출을 미루지 않는다. 대신 작은 표본을 임의 선택해 결론을
과장하지 않도록 다음 evidence ladder를 고정한다.

### 5.1 호출 단계

1. **0-call preflight:** source coverage, provenance, exact tokenizer admission, rendered input,
   semantic contract, isolated output path를 끝낸다.
2. **micro diagnostic 4~8 calls:** 새로운 schema·serialization·관계축이 실제로 표현되는지만 본다.
   label 성능 결과로 부르지 않는다. malformed, 누락 필드, token runaway가 하나라도 있으면 즉시
   수정하고 다시 micro를 남긴다.
3. **fixed fast20:** `configs/dev_fast_panel_v1.json`의 20건을 반드시 실행한다. 이 단계부터 TP/FP/FN과
   Macro를 기록한다.
4. **independent holdout20:** fast의 사전 gate를 통과한 후보만 실행한다.
5. **dev200:** holdout gate까지 통과한 한 후보만 확장한다.

각 API response는 도착 즉시 append-only checkpoint에 저장한다. 5건마다 intermediate report에
completed calls, invalid, prompt/completion tokens, 누적 runtime, 현재 affected-item TP/FP/FN을
기록한다. 중단해도 마지막 checkpoint에서 재개한다.

### 5.2 기대 호출 수

micro 크기를 `m<=8`, 각 gate 생존확률을 `p_m, p_f, p_h`라고 하면 한 후보의 기대 호출은
다음과 같다.

```text
E[C] = m + 20*p_m + 20*p_m*p_f + 200*p_m*p_f*p_h
```

예를 들어 각 단계 생존확률을 가정값 0.5로 놓고 `m=8`이면 기대 호출은
`8 + 10 + 5 + 25 = 48`이다. 이 값은 **후보 1건당 공고 1개에 신규 모델 호출 1회**일 때만
성립한다. item group이나 overflow 때문에 공고당 평균 `g_f, g_h, g_d`회가 필요하면
`E[C] = m + 20*g_f*p_m + 20*g_h*p_m*p_f + 200*g_d*p_m*p_f*p_h`로 다시 계산한다.
가정값 0.5는 관측 생존율이 아니며, 실제 예산은 mock에서 측정한 context×group 수와
completion token 상한을 사용한다. 최종 통과 후보가 1-call이면 누적 최대 248회지만,
그때는 이미 두 독립 panel의 근거가 있다.

### 5.3 빠른 결론과 과적합 통제

- 한 item에서 동시에 비교할 prompt/schema variant는 최대 2개로 제한한다.
- micro panel은 source/transport 진단 전용이며 F1 승격 근거로 쓰지 않는다.
- fast20은 탈락과 후보 순위 결정용이고 canonical 승격은 holdout20과 dev200을 요구한다.
- fast 실패 후 같은 panel에 맞춘 세 번째 문구 변형을 만들지 않는다. 실패 유형을 source omission,
  relation schema, serialization, reducer 중 하나로 먼저 분류한다.
- 공식 source correction은 점수 실험과 구분한다. threshold correction과 prompt/runtime 변경을 같은
  manifest에 넣지 않는다.

## 6. 완성 기준

다음 submission을 완성 후보라고 부르려면 모두 만족해야 한다.

1. fixed fast20 → independent holdout20 → dev200 순으로 품질 검증.
2. 200행 49열, evidence substring, ID/NFC 검증 100%.
3. active/package module hash parity 100%.
4. initial/retry/fallback logical calls와 schema별 backend batches 기록.
5. exact staged ZIP mock 및 archive-level batch failure/invalid 2-round fault test.
6. evaluator와 같은 vLLM 설정의 GPU smoke 또는 실제 제출 완주 증거.
7. emergency output 경로와 정상 품질 경로를 별도 상태로 기록.
8. 한 실험에는 quality owner, serialization, topology 중 하나만 변경.
9. v5·v6·v7 공식 지역제한 금액 selector와 v2·v14~v16의 2.3억원 selector가 서로 분리돼 있음.
10. 모든 API 단계가 5-call checkpoint와 중간 TP/FP/FN·invalid·token/runtime 기록을 남김.

S002·S003은 제출 정책으로 승격하지 않았다. S004는 큰 모집단 shift를 확인했고 S005는 v3-only
revert counterfactual을 완성했다. 현재 행동은 S005를 무조건 제출하는 것이 아니라 original
reference public 대응을 확인하고, base owner의 저가·소액수의 strata source-role 감사를 통해
0.605→0.75 구간을 설명할 공통 누수를 찾는 것이다. 검증되지 않은 역할 guard와 새 지역금액을
S005에 섞지 않는다.

S008/S009의 v16 full-source verifier는 micro gate에서 source role을 안정적으로 구분하지 못해
기각했다. S010의 20,000건 v3 morphology 감사에서는 모집단 routed candidate가 dev보다 평가·서식
역할과 추정가격 초과 금액 표면을 더 많이 포함함을 확인했다. AGGREGATE 비율은 안정적이므로
reducer에 single-contract 조건을 다시 넣지 않고, S005 specialist 전체 단독 제거만 public 식별
후보로 유지한다. 동시에 한 item 최대효과가 `1/24`임을 감안해 v24와 저가/소액수의 owner의
공통 구조 감사는 계속한다.

S011 stage attribution 결과, v10/v16/v17/v18을 initial deterministic stage로 되돌리는 wholesale
rollback은 local F1 손실이 크고 expansion precision의 안전여유도 충분해 기각했다. v12~v14 역시
대체 owner 없이 0으로 지우지 않는다. 다음 일반화 감사 순서는 v19 specialist morphology와
호출비용이며, public ablation은 여전히 한 번에 v3 또는 v19 하나만 변경한다.

S012 v19 감사도 완료했다. candidate route는 모집단에서 76.10%로 dev 82.50%보다 약간 낮고,
자기서약·서식 후보 구조는 거의 동일했다. 외부 공급확약의 입찰 문맥은 모집단에서 더 적었다.
native v19가 dev에서 제거한 8개 positive는 모두 FP였고, 동일 notice의 저장 total token은 base B보다
약 35.3% 적었다. v19-only rollback은 현재 우선 제출 후보에서 제외한다. 다음 public 식별 제출은
한 변경만 가진 S005 v3-only revert이며, 이와 동시에 v24/저가·소액수의 owner 개선을 섞지 않는다.

S013 v24 감사에서는 C24의 44 FP가 source omission에 집중되지 않았고, direct verdict가 복합
계약·지역·업종 문구를 과잉 불일치로 읽는 문제가 확인됐다. 특히 region evidence는 dev 0 TP/13 FP,
population region candidate surface는 dev보다 12.67%p 많았다. v24 prompt-only 재튜닝과 기존
multi-observation 확장은 중단한다. evidence resolution 실패 positive를 label 0으로 내리는 안도
v15 TP를 잃고 C24의 source-grounded quote를 잘못 제거하므로 기각한다. evidence 복구는 V 불변의
별도 serialization/evidence 변경으로만 검토한다.

S014 post-stratification 결과에 따라 S005 v3-only revert의 지위를 수정한다. v3 specialist는
population weight를 적용해도 r10보다 F1이 `0.9204 vs 0.2668`로 훨씬 높았다. v19 native와 Python
refinement도 각 rollback보다 우세했다. 따라서 S005는 정책 식별용 diagnostic일 뿐 다음 기대품질
제출 후보가 아니다. 다음 품질 실험은 v17 direct/<1억 FP의 relation precision guard이며, public
괴리의 대부분이 coarse mix로 설명되지 않으므로 evaluator generation robustness 감사도 별도로 한다.

S015 exact-repeat 감사에서 specialist response 문자열은 v3 50%, v19 94.1%가 달랐지만 final V
불일치는 각각 0/10, 1/17이었다. 따라서 typed reducer는 유지한다. 단 v19 불일치 한 건이 실제
FP였으므로 positive-only 동일-task confirmation을 S016 8개 신규 호출로 진단한다. base r10/B/C24는
repeat artifact가 없어 이후 작은 고정 panel로 별도 측정한다.

S016/S016R positive-only repeat는 v19 TP 6개를 모두 보존하고 FP 2개를 제거해 item F1을
`0.75→0.85714`로 높였다. 다만 Macro 효과는 `+0.00446`, 예상 test 추가 호출은 약 85개이며
첫 wave 뒤 두 번째 순차 wave가 필요하다. 현 95분 27초 제출에는 runtime margin을 먼저 증명해야
하므로 즉시 통합하지 않는다. provider가 단일 JSON fence를 반환한 6건은 serialization-only
adapter로 0-call 복구됐으므로, 재시도보다 parser recovery를 먼저 적용하는 것이 효율적이다.
다음 우선순위는 r10/B/C24의 hash-fixed exact-repeat panel로 base generation variance가 public
괴리의 큰 부분을 설명할 수 있는지 측정하는 것이다.

S017/S017R의 label-blind 2-notice/6-task base repeat에서는 JSON fence 복구 후에도 final S001
V/E 변화가 0이었다. 따라서 base 전체에 repeat-confirmation을 추가하는 방향은 효과 근거 없이
runtime만 늘리므로 중단한다. generation variance는 evaluator vLLM에서 미해결이지만 다음 품질
실험의 우선순위는 아니다. 다음은 S014 weighted 하락 1위이면서 S011 rollback보다 current가 우세한
v17의 direct/<1억 relation precision을 source-only로 감사한다.

S018 v17 source 감사에서 실제 역할 결함이 확인됐다. dev FP의 소기업 전용/적용 예외 사례와
비라벨 hash 표본의 같은 패턴을 근거로, 다음 후보는 v17의 참가 가능 범위·실제 구매대상과
CSV 특이사항·이번 계약 적용 예외를 **관계별로** 관측하게 한다. 코드나 조문 문자열의 존재만으로
Python이 v17을 0으로 만드는 방식은 dev TP 반례 때문에 기각한다. 기존
`src/pps_ai/views/v17_full_source.py`는 원문 전체 버전과 원문을 축약하는 relation-view 버전이
혼재하므로, 새 호출 전에 최종 원문 완결성·3종 rendered input·semantic contract·token admission·
mock·call topology를 다시 확인한다. 한 item의 oracle Macro 상한이 작으므로 v17만 반복 보정하지
않고, 같은 관계 오류가 있는 다른 owner를 **각 item의 truth condition 증명 후** 독립적으로
탐색한다. 상세는 `docs/clean_exp_s018_v17_source_relation_audit_result.md`를 따른다.

S018의 cross-owner 재검토에서 v16 FP 3건과 v18 FP 4건에는 v17형 broad false hit가 없었다.
따라서 v17 관계 보정의 효과를 v16/v18로 곱해 추정하지 않는다. v18의 한 공고에는 소기업
참가조건이 원문에 있는데 detector의 small hit가 비어 있어 반대 방향의 누락을 별도 점검한다.
이 결과는 공통 schema 확장의 근거가 아니라 owner별 오류축 분해의 근거다.

## 2026-09-23 S019 이후 우선순위 재설정

위의 `v17 다음 품질 후보` 표현은 개별 항목 결함을 찾던 당시의 우선순위다. 사용자의 현재 목표는
0.815 로컬 대 0.605 public 괴리에서 **Python 전략 전체의 일반화 위험을 비라벨 20,000건으로
검사하고, 정당화되는 과적합 요소를 덜어내는 것**이다. S019의 frozen direct-owner 전수 검사에서
v1/v2/v5/v6/v7/v8도 dev 양성 경로가 모집단에 비해 2.01~17.65배 농축됐다. S007의
v12~v16 제품·범위 후보와 함께 보면 한 item의 미세수정이 아니라 여러 owner군의 표본 선택과
source-role 취약성이 우선 문제다. S019 결과와 수학적 한계는
`docs/clean_exp_s019_python_policy_population_audit_result.md`를 따른다.

다음 순서는 (1) direct 지역·실적, 제품·absence, base-dependent Python override를 owner군으로
나눠 hash 고정 비라벨 원문 역할을 블라인드 감사하고, (2) 확인된 **공통적인 역할 오독**만
대체/강등 후보로 만들고, (3) 각 변경을 별도 one-change ablation에서 검증하는 것이다.
모집단 발화율 이동만으로 final 1을 삭제하거나 Python 전체를 끄지 않는다. S014의 coarse
post-stratification이 public 격차의 약 9.42%만 설명했고, S011/S014의 전면 rollback도 손해였기
때문이다. 공식 지역금액 selector 보정, prompt/generation 안정성, timeout은 분리된 축으로 둔다.

S020은 실제 source-role의 첫 넓은 표본 감사다. v1의 허용/일반등록, v5의 평가·납품처,
v6의 운반거리 평가를 참가자격 제한으로 읽은 사례를 hash 고정 비라벨 표본에서 확인했다.
v7/v8은 같은 크기 표본에서 즉각적인 역할 오독 근거가 약했다. 여섯 direct item은 기본 Gemma
대체 owner가 없는 Python-only 칸임도 확인했다. 따라서 **Python 제거=기본 모델 복귀**라는
가정은 틀리고, 제거 전에 대체 의미 판정의 정확도와 호출시간을 입증해야 한다. 첫 one-change
후보는 v5 source-role 검증으로 한정하고, 공식 금액 보정과 분리한다. 전체 근거는
`docs/clean_exp_s020_direct_owner_source_role_audit_result.md`에 있다.

S021은 기존 regex source view를 v5 강등 gate로 시험했지만 기각했다. dev 7 TP는 모두
보존했으나 비라벨 42 양성 중 13건을 제거했고, S020 hash 표본에서는 진짜 참가자 본점 제한
표면 두 건을 제거하면서 평가 가점 한 건을 남겼다. 원문 역할 표면의 표본 F1은 0.857에서
0.727로 낮아졌다(대회 라벨 F1이 아님). 따라서 기존 view를 그대로 label veto로 쓰지 않는다.
다음은 전체 원문/section 문맥을 읽는 대체 관측의 정확도와 runtime을 작은 고정 panel에서
먼저 검증한다. `docs/clean_exp_s021_v5_existing_role_guard_result.md`.

## 2026-09-23 목적 재확인: 20,000건으로 Python 전략의 과적합 위험을 덜어내기

S022/S022R은 v5의 원문 역할 관측이 작은 고정 panel에서 가능함을 보였지만, 최초 strict
parser의 invalid 3/24를 0-call source quote replay로 복구한 **진단**일 뿐이다. 역할 음성은
2건, blind 비라벨 8건은 모두 역할 양성이어서 최종 v5 gate의 일반화는 검증되지 않았다.
`docs/clean_exp_s022_v5_role_probe_result.md`를 따른다. v5만 계속 다듬는 것은 현재 목적과
맞지 않는다.

이후의 우선 과제는 **2만 건에서 Python final-decision 전략 전체의 과적합성 노출을 진단하고,
원문상 잘못된 가정이 확인된 요소를 안전하게 제거·대체하는 것**이다. dev 0.815와 public
0.605의 차이는 적응적 선택 과적합의 강한 경고지만, 이 차이 하나만으로 Python이 얼마나
기여했는지 식별할 수 없다. 비라벨 20k는 activation·공고 유형·첨부·원문 역할 분포를 정확히
셀 수 있으나 TP/FP/F1은 셀 수 없다. public test와 동일 분포라는 보장도 없다. 따라서
"20k 발화율이 낮다/높다 → 규칙 삭제"는 금지한다.

판정 단위는 작은 문구가 아니라 owner군의 **최종 1을 만드는 논리**다. S019/S020/S007과
기존 S010/S012/S013/S018을 같은 표에 정렬해 (a) exact source/organizer fact인지,
(b) 역할·적용성·부재를 Python이 final label로 승격하는지, (c) 그 승격이 어떤 모집단
stratum에서 반복되는지, (d) 제거 시 대체 의미판정이 존재하는지를 비교한다. 우선 비교군은
direct 지역·실적(v1/v2/v5~v8), 제품·기업범위·부재(v10~v18/v20), base verdict 후
Python override(v4/v21~v23), 그리고 대조군인 typed specialist(v3/v19)다. 확인된
원문 역할 오류는 **문제 경로의 증거**이지 곧바로 label 0 veto는 아니다.

| owner군 | 현재 정량 증거 | 현재 결론/빈틈 |
|---|---|---|
| direct 지역·실적 | S019의 dev/pop final-1 RR 2.01~17.65; S020에서 v1/v5/v6 역할 오독 | 실제 오류가 있으나 대체 owner 부재. S022의 v5 역할 탐침은 음성 일반화 미검증. |
| 제품·기업범위·부재 | S007에서 v12/v13/v14/v16 후보 RR 1.86~4.35; 20k organizer clause와 source detector 불일치 597/352건 | 제품 적용성·참가범위·부재 승격이 위험. 단순 metadata veto나 전체 rollback은 반례가 있음. |
| model 후 Python override | v4/v21~v23의 final writer는 확인됨; 같은 경로의 20k 최종 발화율은 아직 없음 | 저장 model response가 필요한 경로를 구분해 무호출 가능 범위부터 확인. 미측정을 안전성으로 해석하지 않음. |
| typed specialist 대조군 | S014 재가중에서 v3/v19 유지가 revert보다 우세; S015~S017 반복 final 대부분 안정 | Python 전체가 문제라는 가정의 반례. evaluator와 remote 생성 차이는 별도 미식별. |

이 표의 RR은 **규칙 노출 비율**이지 오류 위험비가 아니다. 특히 제품군의 후보 RR은 BGE 전
상한이므로 direct final-1 RR과 같은 분모의 precision 수치처럼 비교하지 않는다.

삭제 gate의 수학도 명시한다. 한 item의 현재 `TP=T, FP=F, FN=N`에서 양성 예측을
`x`개 TP와 `y`개 FP만큼 제거하면 F1이 오를 필요충분조건은
`T*y > x*(T+F+N)`이다. 비라벨 20k에서는 `x,y`를 모르므로 이 조건을 직접
검증할 수 없다. 특히 대체 owner가 없는 direct Python 항목을 끄면 검증된 dev TP까지
잃는다. 후보 제거는 blind source-role 감사에서 오류 구조를 입증하고, 대체 owner 또는
보수적 observation 경로를 만든 뒤, 한 owner씩 고정 fast panel→dev의 다른 holdout subset→
dev200 순으로 **회귀·malformed·runtime**을 테스트한다. 이미 선택에 사용한 이 세
cohort는 독립 검증도, 포화 item에서 F1 상승을 요구할 수 있는 selection gate도 아니다.
S023의 수학적 분석을 적용해 blind source-role audit와 가능한 독립 라벨/한 변경 public
평가를 일반화 판정으로 분리한다.

다음 실행 순서: (1) 기존 20k 감사 결과를 owner군별 공통 오류·노출·대체경로 ledger로
통합하고 빠진 final-override 경로를 무호출 점검한다. (2) 여러 owner에 반복되는
`역할 표면→법적 적용` 또는 `탐지 부재→법적 부재` 승격 중 하나를, source와 대체 가능성으로
우선 선택한다. (3) 가장 작은 영향을 받는 owner 한 개에서 controlled ablation을 하고,
이득이 재현될 때만 같은 원리를 다음 item으로 넓힌다. 개별 v5 문구 조정이나 전체 Python
rollback을 진행 순서로 삼지 않는다. 점수뿐 아니라 malformed·근거 유효성·추가 호출·
120분 runtime 여유를 함께 기록한다.

S023에서 direct Python 여섯 항목 중 다섯 항목의 dev F1이 이미 1.0임을 확인했다.
이들 항목에서 기존 양성을 하나라도 제거하면 dev F1은 반드시 떨어진다. 따라서
“dev200 점수가 오르지 않았으니 역할 오독 제거 실패”라는 판정은 수학적으로 부적절하다.

## 2026-09-23 제출/신규 로컬 측정 정정

S025의 ZIP은 기존 제출 S001과 내부 파일이 모두 같아서 제출 후보에서 철회했다.
S026 v1 역할 검증 micro는 malformed 9/22와 기존 역할 음성 구분 실패로 기각했다.
그 뒤 하루 한 번의 실제 제출을 위해 **S005의 v3-only revert**를 S027 ZIP
`dist/pps_20260923_163852.zip`으로 패키징했다. 이는 일반화 개선이 확인된
승격이 아니라 public에서 v3 specialist 효과를 식별하는 한 변경 ablation이다.
S027 저장응답 replay 0.7910823947은 신규 로컬 생성 점수가 아니다. 사용자 지적에
따라 ZIP 자체를 신규 OpenRouter Gemma 응답으로 실행한 S028 dev200 Macro는
**0.7894287115**다. 총 639회(초기 600, retry 37, fallback 2), 전송 오류 0,
C24 unresolved 14건이며 200행/49열·원문 evidence 유효성 검사를 통과했다.
이는 기존 S001 adaptive dev 0.8151465658보다 낮다. public 개선 여부와 evaluator
시간은 여전히 미검증이다. 자세한 값은
`docs/s027_20260923_v3_base_submission_candidate.md`와
`docs/clean_exp_s028_s027_fresh_dev200_plan.md`를 따른다.
반대로 source-role 개선만으로 public F1 상승을 주장하는 것도 금지한다. 상세는
`docs/clean_exp_s023_dev_saturation_generalization_gate_result.md`를 따른다.

S024는 여섯 direct owner가 공고문 밖에서 놓치는 **predicate 후보**를 전 문서에 대해
무호출로 셌다. 비라벨 20k의 첨부-only notice-item pair는 v1/v2/v5/v6/v7/v8 순서로
30/164/9/17/11/9건이었다. 그러나 고정 원문 표본에는 참가 허용·평가표·서식·가점·
운반거리와 실제 참가조건이 섞여 있었다. dev의 유일한 첨부-only v1 후보도 정답 0이었다.
따라서 `공고문만`은 source coverage 결손이고 `모든 첨부 hit를 OR`도 FP 위험이다.
다음 대체 경로는 문서 범위 전체를 유지하면서 실제 참가자격/평가/서식/이행/예외의
역할을 분리해야 한다. 상세는
`docs/clean_exp_s024_direct_attachment_coverage_result.md`를 따른다.
