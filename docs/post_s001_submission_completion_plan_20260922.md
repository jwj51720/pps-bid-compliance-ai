# S001 제출 이후 완성 계획

작성일: 2026-09-22

## 1. 현재 기준

제출한 `pps_20260922_153225.zip`의 로컬 품질 기준은 stored-response task-hash replay 기준
dev200 Macro positive-F1 `0.8151465658`이다. 200행 49열은 C005D final과 cell 단위로 일치한다.
이는 품질 조합 검증이며 evaluator vLLM wall time 또는 public score 검증은 아니다.

현재 구조는 완전 독립 24-owner가 아니다. v3와 v19는 active specialist가 최종 cell을 소유하고,
나머지 22개 항목은 기존 3-arm 실행의 결과를 사용한다. e는 최종 점수 최적화 대상이 아니라
양성 verdict의 원문 substring을 생성·검증하는 출력 계약으로 유지한다.

## 2. 실행시간의 수학적 진단

### 2.1 logical calls

```text
r10 200 + C24 200 + v19 owner 200 + v3 conditional 61 = 661
```

기존 3-arm 600회보다 61회, 즉 `10.17%` 많다. v19 native 165회는 B 200회 위에 더한 것이
아니라 candidate notice의 B를 대체한다.

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

## 4. 다음 실험 우선순위

### P0. 제출 결과가 나오기 전에는 현재 policy를 다시 바꾸지 않는다

이번 결과는 runtime 식의 미지수에 대한 실제 관측이다. 결과를 받기 전에 품질 prompt와 runtime
serialization을 동시에 바꾸면 원인을 분리할 수 없다.

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

## 5. 완성 기준

다음 submission을 완성 후보라고 부르려면 모두 만족해야 한다.

1. fixed fast20 → independent holdout20 → dev200 순으로 품질 검증.
2. 200행 49열, evidence substring, ID/NFC 검증 100%.
3. active/package module hash parity 100%.
4. initial/retry/fallback logical calls와 schema별 backend batches 기록.
5. exact staged ZIP mock 및 archive-level batch failure/invalid 2-round fault test.
6. evaluator와 같은 vLLM 설정의 GPU smoke 또는 실제 제출 완주 증거.
7. emergency output 경로와 정상 품질 경로를 별도 상태로 기록.
8. 한 실험에는 quality owner, serialization, topology 중 하나만 변경.

현재 다음 행동은 제출 결과를 기록하는 것이다. timeout이면 P1, 완주하면 P2의 v24 무호출 audit와
v9 최소 owner 설계로 진행한다.
