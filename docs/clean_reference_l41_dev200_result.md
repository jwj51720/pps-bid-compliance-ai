# Clean reference L41 OpenRouter dev-200 result

실행일: 2026-09-21

manifest: `experiments/manifests/reference_l41_openrouter_dev200_v1.json`

output: `outputs/clean-reference-l41-openrouter-dev200-v1/`

## 결론

해시로 고정한 0.7+ 참고 제출 L41의 판정 구조를 새 `src/pps_ai` 계층에서 실행한 결과,
dev200 Macro positive-F1은 **0.779674**였다. 기존 프로젝트의 0.32대 상한이 Gemma 자체의
성능 한계였다는 해석은 기각된다. 가장 큰 차이는 all-24 카드 prompt가 아니라 다음 구조다.

- 다수 항목은 organizer source에서 만든 F1–F6 사실과 명시적 Python predicate가 소유한다.
- Gemma는 `r10` 잔여 의미판정, `B` v19, `C24` v24의 세 arm만 담당한다.
- 24개 항목마다 final owner가 하나이고 일반 OR merge가 없다.
- 전 문서를 semantic section 후보로 스캔하지만 Gemma에는 목적별 bounded exact span만 준다.
- evidence가 무효여도 V를 숨게 변경하지 않는다.

따라서 다음 개선의 기준선은 EXP171/231이 아니라 이 clean L41 graph여야 한다. 다만 reference의
dev 결합 가능성이 크므로 public 0.7+ 관측과 함께 보되, 아래 결함을 한꺼번에 고치지 않는다.

## 점수

| cohort | records | Macro positive-F1 |
| --- | ---: | ---: |
| dev200 | 200 | **0.779674** |
| fast20 | 20 | **0.679167** |
| independent holdout20 | 20 | **0.388889** |

holdout20은 양성이 없는 항목도 F1=0으로 평균하는 기존 metric 계약을 그대로 쓴다. 따라서
작은 panel 수치가 dev200보다 크게 낮은 것만으로 구조 전체가 붕괴했다고 해석하지 않는다.
다만 v3/v4/v9/v19/v23/v24의 holdout 일반화는 후속 독립 검증 대상이다.

## dev200 항목별 결과

| item | TP | FP | FN | F1 |
| --- | ---: | ---: | ---: | ---: |
| v1 | 7 | 0 | 0 | 1.0000 |
| v2 | 7 | 0 | 0 | 1.0000 |
| v3 | 2 | 1 | 6 | 0.3636 |
| v4 | 4 | 5 | 2 | 0.5333 |
| v5 | 7 | 0 | 0 | 1.0000 |
| v6 | 6 | 1 | 0 | 0.9231 |
| v7 | 7 | 0 | 0 | 1.0000 |
| v8 | 6 | 0 | 0 | 1.0000 |
| v9 | 3 | 5 | 3 | 0.4286 |
| v10 | 7 | 1 | 0 | 0.9333 |
| v11 | 3 | 0 | 3 | 0.6667 |
| v12 | 3 | 0 | 3 | 0.6667 |
| v13 | 5 | 1 | 1 | 0.8333 |
| v14 | 7 | 0 | 1 | 0.9333 |
| v15 | 6 | 0 | 0 | 1.0000 |
| v16 | 6 | 3 | 0 | 0.8000 |
| v17 | 6 | 7 | 0 | 0.6316 |
| v18 | 7 | 4 | 0 | 0.7778 |
| v19 | 5 | 10 | 1 | 0.4762 |
| v20 | 5 | 3 | 0 | 0.7692 |
| v21 | 6 | 0 | 0 | 1.0000 |
| v22 | 5 | 0 | 0 | 1.0000 |
| v23 | 4 | 1 | 1 | 0.8000 |
| v24 | 5 | 44 | 3 | 0.1754 |

가장 큰 명시적 누수는 v24의 44 FP다. 다음은 v3의 6 FN, v19의 10 FP, v17의 7 FP다.
반대로 v1/v2/v5/v7/v8/v15/v21/v22는 dev200에서 완전 일치했다. 이는 item-specific owner와
deterministic/hybrid 분해가 평균 점프의 주원인이라는 강한 증거다.

## 실행 무결성

- input/label ID: 200건 exact join을 유료 호출 전에 검사
- logical calls: 600 (`r10=200`, `B=200`, `C24=200`)
- prompt token 합: 3,576,667; 최대 `r10=11,590`, `B=10,399`, `C24=6,831`
- OpenRouter usage: prompt 3,577,692, completion 130,749, reported chat cost $0.427178
- finish reason: `stop=591`, `length=9`
- frozen assembly fallback: `r10=0`, `B=0`, `C24=9`
- evidence: invalid substring 제거 0, label mutation 0, positive-without-evidence `v15=2`, `v24=4`
- output: 200 unique IDs, 49 ordered columns
- retrieval: BGE-M3, 615 catalog rows, label-blind top-10, 200 queries
- reference ZIP SHA-256:
  `a06feff77ffbc4a6f2a47cd0e2d322f341f652ca865d1b9cf53919012c8ca216`
- final manifest SHA-256:
  `4d2d23d23e46ca021bef939347bf43dbfb911de3a5e41ab149054c4bb385abbb`
- active tests: `8 passed`

첫 실행은 393응답 후 OpenRouter `in_flight_budget_exhausted` 402에서 멈췄다. transport
concurrency를 64에서 8로 낮추고 해당 402의 `Retry-After`를 재시도하도록 수정했다. 이후 잔액
부족 402에서 한 번 더 멈췄고, 충전 후 checkpoint를 재사용해 남은 207개만 완료했다. 최종
report의 227.644초는 마지막 resume 구간만 측정한다. 최초 응답부터 최종 report까지 관측된
벽시계 범위는 09:53:47–10:15:48 약 22분이며 중간 credit 대기를 포함한다. evaluator vLLM
runtime 근거로 사용하지 않는다.

## 입력 coverage와 제한

source ledger에는 200건의 모든 organizer document가 순서·type·SHA-256과 함께 존재한다.
foreign-document span은 0건이었다. short/attachment/largest prompt를 직접 읽어 F facts,
source ID/offset, exact source text, C24 meta가 실제 message에 렌더링됨을 확인했다.

다만 5개 공고는 제공 첨부 중 하나가 semantic candidate를 만들지 못했다. 원문 파일 누락이나
token truncation이 아니라 frozen selector recall 한계다. 또한 이 baseline은 다음 결함을
의도적으로 보존한다.

- v4가 추출한 예외 `e`를 final reducer가 사용하지 않는다.
- 여러 deterministic rule이 전 문서가 아니라 공고문만 검색한다.
- C24 9건이 completion length로 fallback했다.
- v24가 dev200에서 극심한 positive 과다판정을 보인다.
- OpenRouter 실행은 evaluator의 local vLLM/int8 결과와 완전히 같다고 주장할 수 없다.

## 다음 실험 우선순위

1. **v24 단독 교정**: C24 length와 44 FP를 분리한다. max-token 변경과 semantic 판정 변경을
   같은 실험에 섞지 않는다.
2. **v3 recall**: 6 FN이 source-view omission, r10 원자상태, final conjunction 중 어디서
   발생했는지 writer trace로 분해한다.
3. **v19 precision**: 10 FP의 whole-proposition source를 검토하되 B schema를 먼저 넓히지 않는다.
4. **deterministic owner 일반화 감사**: dev 완전일치 항목은 public 성과의 핵심일 수 있지만
   dev-specific 문자열 결합 여부를 organizer-source provenance와 blind 사례로 점검한다.
5. correction은 항상 L41 clean baseline manifest 대비 단일 owner/단일 policy change로 실행한다.

이번 결과는 “Gemma에게 판정 정보를 더 많이 넣는 것”보다, **입력을 구조화하고 항목별 final
owner를 명시하며 결정론적으로 표현 가능한 truth condition을 모델에서 빼는 것**이 훨씬 큰
개선이었다는 결론을 뒷받침한다.
