# EXP-C004R/C004RR v3 monetary relation dev200 결과

실행일: 2026-09-21

## 결론

**PASS.** Clean L41의 v3 owner만 source-grounded monetary relation으로 교체해 fast20,
independent holdout20, dev200에서 모두 같은 방향의 개선을 확인했다. 두 whitespace-loop 응답은
exact-task append-only recovery로 복구했으며 최종 invalid response는 0이다.

| cohort | baseline v3 TP/FP/FN/F1 | candidate v3 TP/FP/FN/F1 | Macro before → after |
| --- | --- | --- | --- |
| fast20 | 1/0/2 / .5000 | 3/0/0 / 1.0000 | .679167 → .700000 |
| holdout20 | 0/0/1 / .0000 | 1/0/0 / 1.0000 | .388889 → .430556 |
| dev200 | 2/1/6 / .3636 | 7/1/1 / .8750 | .779674 → **.800980** |

Dev200 Macro delta는 다음과 정확히 일치한다.

```text
(0.875000 - 0.3636363636) / 24 = 0.0213068182
0.7796736645 + 0.0213068182 = 0.8009804827
```

## 최종 artifacts

- semantic run:
  `outputs/clean-exp-c004r-v3-keyed-full-fast-v11/dev200/`
- recovery/final submission:
  `outputs/clean-exp-c004rr-v3-keyed-recovery-v1/`
- manifest:
  `experiments/manifests/clean_exp_c004r_v3_keyed_full_fast_v11.json`
- recovery manifest:
  `experiments/manifests/clean_exp_c004rr_v3_keyed_recovery_v1.json`

## 무결성

- organizer supplied documents inspected: 374/374; uninspected 0
- candidate notices/candidates: 61/100
- semantic specialist calls: 61
- recovery calls: 2; normal response replay 0
- keyed invalid after recovery: 0
- v3 positive without evidence: 0
- other 23 changed cells: 0
- evidence label mutations: 0
- active tests: 40 passed
- legacy import/execute/copy/generation: 0

Dev200 semantic run은 OpenRouter에서 321.889초였다. 두 upstream whitespace loops가 각각 8,192
completion tokens를 소모한 시간이 포함되며 evaluator vLLM runtime 근거로 사용하지 않는다.
Recovery는 2.818초였다.

## 구조적 결론

기존 r10의 v3 실패는 Gemma 자체의 독해 한계보다 출력 계약에 있었다.

1. qualification과 amount를 단일 source ID에 압축해 맞는 q/x도 provenance gate에서 잃었다.
2. 모델에게 숫자 비교를 맡겨 `1억원 < 327,272,727원` 같은 산술 FP가 생겼다.
3. candidate별 역할과 exact amount surface만 모델이 관찰하고 Python이 원 단위 정규화와 strict
   inequality만 계산하자 6 FN 중 5개를 회수했다.
4. Candidate-keyed object는 배열의 ID 중복/누락을 제거했다.

이는 “Python이 keyword로 법률판정을 한다”는 구조가 아니다. Python selector는 모든 문서에서
`실적+금액` exact span을 고재현율로 보존하고, Gemma가 참가자격/평가/서식 역할을 판정하며,
Python은 exact surface 검증·단위 변환·organizer metadata와의 부등식만 소유한다.

## 남은 오류와 다음 단계

- FN `PPS-DEV-059`: 실제 참가자격 `통근버스 운행 실적 2억원 이상`을 Gemma가
  BID_QUALIFICATION/mandatory YES로 맞혔지만 `AGGREGATE`로 분류했다. 현재 reducer가
  SINGLE_CONTRACT만 받는다. Organizer 항목표는 단일계약을 명시하지 않으므로 이 gate의 source
  concordance를 별도 감사해야 한다.
- FP `PPS-DEV-137`: 제안요청서의 `[첨부 제4호 서식] 최근 5년 이내 용역수행 실적`을 실제
  참가자격으로 오분류했다. Exact span에는 서식 heading이 존재하므로 role observation의
  재검증/contradiction 문제다.

두 오류는 서로 다른 원인이므로 한 실험에서 같이 고치지 않는다. 다음 우선순위는 먼저 v3
`SINGLE_CONTRACT` gate가 organizer source에 있는지 읽기 전용 감사하고, 확정 결함이면 offline
reducer replay로 FN 059와 전체 61 observations의 변화 상한을 계산하는 것이다. 그 뒤 FP 137은
FORM role verifier를 별도 최소 실험으로 다룬다.

