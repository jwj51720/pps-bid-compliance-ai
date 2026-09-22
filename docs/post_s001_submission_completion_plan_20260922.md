# S001 제출 이후 완성 계획

작성일: 2026-09-22

2026-09-22 organizer 지역제한 금액 보완 공지를 반영해 개정했다. 공지의 source record와 현재
제출물 영향 감사는 `docs/organizer_notice_20260922_local_region_thresholds.md`에 있다.

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
6. **v5·v6·v7 공식 지역제한 금액 selector**
   - 현재 제출물은 지방계약을 5억원 또는 일부 2.3억원으로 단순화해 새 공지와 불일치한다.
   - 다음 후보는 시·도(세종 제외) 3.5억원, 교육청·학교·지방공기업 5억원, 세종·시·군·구
     5억원, 기술용역 3.3억원, 안전점검·정밀안전진단 1.5억원을 `입찰추정가격`과 비교해야 한다.
   - v2와 v14~v16의 2.3억원은 변경하지 않는다.
   - dev200의 확정 marker 37건에서는 반사실 label 변화가 없었지만 public correctness를 위해
     반드시 보수한다.

## 4. 다음 실험 우선순위

### P0. 제출 결과를 기록하되 공식 selector 보수는 병행 준비한다

이번 결과는 runtime 식의 미지수에 대한 실제 관측이다. 결과를 받기 전에 품질 prompt와 runtime
serialization을 동시에 바꾸면 원인을 분리할 수 없다. 다만 organizer가 새로 확정한 v5·v6·v7
금액은 선택적 prompt 실험이 아니라 source correction이므로, 무호출 coverage audit과 구현 계획은
즉시 진행한다. 실제 제출 후보에서는 runtime 변경과 별도 manifest로 검증한다.

### P0.5. v5·v6·v7 organizer correction

가장 먼저 공통 `regional_restriction_threshold` fact를 설계한다. 출력은 기관유형, 용역유형,
적용금액, 각 사실의 organizer source span, 확정/불명 상태다. Python은 확정된 기관·용역 유형과
공식 표의 숫자를 대응시키는 일만 하고, 익명 기관명을 추측하거나 키워드만으로 기술용역을 법적으로
분류하지 않는다.

검증은 다음처럼 변경을 분리한다.

1. no-call dev200 coverage audit: 기관유형·용역유형·가격 operand coverage.
2. 기존 v5·v6·v7 source predicate를 고정한 threshold-only offline counterfactual.
3. 불명 유형만 필요하다면 typed observation의 micro diagnostic.
4. fixed fast20 → independent holdout20 → dev200 regression.

이 correction의 최소 gate는 기존 TP 보존, 새 FP 0, unknown을 임의 label로 바꾼 건 0이다. 로컬
F1 상승이 없어도 organizer source 일치 자체가 승격 사유가 된다. 단, v5·v6·v7의 다른 Python
휴리스틱 결함까지 같은 변경에서 고치지 않는다.

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

예를 들어 각 단계 생존확률을 보수적으로 0.5로 놓고 `m=8`이면 기대 호출은
`8 + 10 + 5 + 25 = 48`이다. 완성 전까지 호출을 전혀 하지 않고 dev200 200회를 실행하는 것보다
실패 후보의 비용과 시간을 크게 줄인다. 최종 통과 후보는 누적 최대 248회를 쓰지만, 그때는 이미
두 독립 panel의 근거가 있다.

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

현재 다음 행동은 제출 결과 기록과 v5·v6·v7 no-call coverage audit이다. timeout이면 P1을 병행하고,
완주하면 공식 selector correction을 먼저 고정한 뒤 P2의 v24 무호출 audit와 v9 최소 owner 설계로
진행한다.
