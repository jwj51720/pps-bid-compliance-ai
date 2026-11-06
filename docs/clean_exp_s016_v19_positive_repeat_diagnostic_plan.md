# S016 — v19 양성-only 동일 task 반복 진단 계획

작성일: 2026-09-23

상태: **계획 고정 — 유료 호출 전 preflight 필요**

## 2026-09-23 유료 호출 전 검토 기록

- manifest preflight: PASS, undeclared differences 0
- selected task hash: C005D dev200와 10/10 exact match
- source coverage: selected 10건의 모든 제공 문서 inspected, uninspected 0
- tokenizer admission: min 1,705 / max 5,500 / budget 14,848 tokens
- semantic-input contract: 10/10 PASS
- mock: PASS, 10개 response 격리·병합·평가·CSV 생성 완료
- 실제 rendered-input 사람 검토:
  - short:
    `outputs/clean-exp-s016-v19-positive-repeat-diagnostic-v1/rendered_inputs/selected_PPS-DEV-033__p01.json`
  - attachment:
    `outputs/clean-exp-s016-v19-positive-repeat-diagnostic-v1/rendered_inputs/selected_PPS-DEV-23__p01.json`
  - largest:
    `outputs/clean-exp-s016-v19-positive-repeat-diagnostic-v1/rendered_inputs/selected_PPS-DEV-162__p01.json`
- 검토 결론: 세 메시지 모두 외부 발급자 적용 전제, 입찰 전 발급·보유 및 입찰·제안과
  동시 제출이라는 1 조건, 단순 목록·가능업체·시점 없음·계약 후 제출·지위증명·자기확약의
  0 조건, candidate별 source ID와 변경 없는 실제 원문을 포함한다. 서로 다른 candidate의 관계를
  합치지 말라는 지시와 source-only/no-final-label 계약도 명시돼 있다.
- overflow: selected 10건은 모두 단일 complete task이므로 overflow sample이 존재하지 않는다.
  largest 5,500 tokens도 예산 안이며 누락 pass가 없다. C005D 원 preflight의 overflow도 0이다.

따라서 아래 유료 호출 전 계약은 모두 충족됐고 8개 새 호출을 진행할 수 있다.

## 진단 질문

S001의 public `0.6053527995`와 dev200 `0.8151465658` 사이의 차이를 전체 구조의 실패로
간주하지 않는다. S015에서 동일 v19 task의 독립 생성 17쌍 중 response 문자열은 16쌍이
달랐지만 최종 V는 1건만 달랐다. 그 1건은 dev primary가 만든 false positive
`PPS-DEV-051`이었다. 따라서 다음의 가장 작은 질문만 검증한다.

> 첫 호출에서 v19=1인 공고만 같은 source-only 관측 task로 한 번 더 읽히고, 두 호출이
> 모두 양성일 때만 1로 유지하면 불안정한 FP를 줄이면서 TP를 보존할 수 있는가?

이는 새 prompt, 새 card, Python 문구 판정, dev-fit 예외 규칙이 아니다. 모델의 같은 판단을
독립 생성으로 한 번 확인하는 call-topology 진단이다.

## 고정 기준과 허용 변경

- base config:
  `experiments/manifests/clean_exp_s015_exact_repeat_stability_audit_v1.json`
- `allowed_policy_changes`:
  - `v19_positive_repeat_diagnostic`
- prompt/schema/model/provider parameter: C005D와 byte-identical task
- primary v19 owner/reducer/evidence resolver: 변경 없음
- 다른 23개 V/E: S001 final row를 byte-identical 계승
- 새 Python label rule: 없음
- 새 호출 대상은 primary v19 positive라는 **모델 출력 상태**로만 선택한다.

## 사전 고정 표본과 호출 수

C005D dev200 primary positive 10건을 결과 확인 전에 고정한다.

```text
PPS-DEV-23__p01
PPS-DEV-033__p01
PPS-DEV-034__p01
PPS-DEV-035__p01
PPS-DEV-036__p01
PPS-DEV-037__p01
PPS-DEV-051__p01
PPS-DEV-098__p01
PPS-DEV-162__p01
PPS-DEV-190__p01
```

- `PPS-DEV-036`, `PPS-DEV-051`: 이미 존재하는 exact-task 독립 repeat를 재사용한다.
- 나머지 8건: 새 OpenRouter 호출을 정확히 한 세대씩 수행한다.
- semantic parse가 실패한 task만 같은 task로 최대 2회 추가 생성한다.
- transport retry와 semantic retry를 구분해 기록한다.
- 각 새 task 완료 때 append-only response와 `intermediate_report.json`을 원자적으로 남긴다.

선정은 primary 출력만 보았고 truth는 선정에 사용하지 않았다. 다만 이 10건은 이미 여러 번
검토된 dev200이므로 결과는 adaptive diagnostic이다.

## 판정과 수학적 게이트

primary positive에 대해 repeat가 valid이고 reducer도 1일 때만 consensus=1로 둔다. primary
negative는 이번 진단에서 변경하지 않는다. dev200 v19 기준은 `TP/FP/FN=6/4/0`,
`F1=0.75`다.

다음 조건을 모두 만족해야 **후속 fixed-policy 검증으로만** 진행한다.

1. 10개 repeat가 모두 semantic-valid이다.
2. TP repeat-positive가 6개 중 5개 이상이다. 즉 recall 손실은 최대 1 TP다.
3. FP repeat-positive가 4개 중 3개 이하이다. 즉 최소 1 FP를 제거한다.
4. consensus v19 F1이 `0.75`보다 높다.
5. evidence는 기존 exact/unique-whitespace resolver로만 복원되며 새 근사 매칭은 없다.

가능한 최소 통과점 `TP=5, FP=3, FN=1`의 F1은

```text
2*5 / (2*5 + 3 + 1) = 0.7143
```

이므로 2~4번을 동시에 만족하려면 실제로는 그보다 더 좋은 조합이 필요하다. 예를 들어
`6/3/0`이면 `0.80`, `5/2/1`이면 `0.7692`다. 이 게이트는 작은 표본의 우연을 일반화
증거로 오인하지 않기 위한 최소 조건이지 public 개선 보증이 아니다.

## 유료 호출 전 계약

다음을 모두 PASS한 뒤에만 8개 호출을 실행한다.

1. manifest diff에서 undeclared change 0.
2. 10개 task hash가 C005D dev200 preflight와 exact match.
3. 각 selected notice의 모든 문서가 source view에서 inspected.
4. 각 task가 Gemma tokenizer 14,848-token 예산 이내.
5. 10개 실제 rendered messages/schema/source IDs를 별도 저장하고 사람이 읽는다.
6. v19 적용 전제, 1 조건, 핵심 0 조건/예외, 필요한 문서가 모두 rendered input에 존재.
7. 다른 23개 item은 새 prompt를 만들지 않고 S001 stored row를 그대로 사용함을 기록.
8. mock run에서 response isolation, resume, reducer, metrics, output path가 동작.

이 실험은 v19에만 대한 intentionally partial diagnostic이다. 24개 item의 완결 전략 결과나
새 canonical submission이라고 부르지 않는다.

## 비용·제출시간 해석

dev에서 v19 candidate task는 165개이고 primary positive는 10개이므로 양성 확인 비율은
`10/165 = 6.06%`다. S012가 추정한 test native task `1410.133`에 같은 비율을 적용하면
추가 호출은 약 `85.46`개다. 호출 수뿐 아니라 첫 wave 뒤에만 대상을 알 수 있어 두 번째
순차 wave가 생긴다. 따라서 품질 게이트를 통과해도 95분 27초였던 제출에 곧바로 넣지 않고,
별도 evaluator-runtime 예산 검토가 필요하다.

## 결과별 다음 행동

- gate 통과: 같은 정책을 사전 고정한 비-dev panel에서 검증하고 runtime 모델을 작성한다.
- TP 손실 우세: consensus AND를 기각하고 specialist relation/reducer 자체를 개선한다.
- FP 제거 없음: 반복 호출을 기각하고 base r10/B/C24의 exact-repeat panel로 원인을 옮긴다.
- malformed 발생: label 효과보다 serialization/recovery 안정성을 먼저 다룬다.

## 실행 명령

```bash
python scripts/preflight_experiment.py \
  --config experiments/manifests/clean_exp_s016_v19_positive_repeat_diagnostic_v1.json
python scripts/run_v19_positive_repeat_diagnostic.py \
  --config experiments/manifests/clean_exp_s016_v19_positive_repeat_diagnostic_v1.json \
  --preflight-only
python scripts/run_v19_positive_repeat_diagnostic.py \
  --config experiments/manifests/clean_exp_s016_v19_positive_repeat_diagnostic_v1.json \
  --mock
python scripts/run_v19_positive_repeat_diagnostic.py \
  --config experiments/manifests/clean_exp_s016_v19_positive_repeat_diagnostic_v1.json
```
