# Source-first / full-final feasibility v1

작성일: 2026-09-09 (dev / mac)

## 질문

1차가 모든 원문에서 source-grounded fact navigation만 수집하고, 2차도 4k anchor가 아닌
**모든 원문·metadata·CSV fact·cards**를 다시 보며 V/E를 판정하는 구조가 admission과
runtime 관점에서 가능한지 확인한다. 이는 EXP157과 다르다. EXP157의 final은 4k anchor라
최종 입력 완결 정책이 아니었다.

## 방법

`scripts/profile_source_first_full_final.py`가 EXP154의 exact Gemma chat template tokenizer로
provider/labels 없이 계산했다. Stage 1은 EXP154 complete-source admission의 208 calls를
그대로 쓴다. Stage 2에서는 `append_fact_inventory` navigation message까지 포함한 final
message로 다시 ordered complete-source pack을 만든다.

결과 artifact: ignored `outputs/source-first-full-final-feasibility-v1.json`.

## 결과

| Stage-2 navigation scenario | records | stage1 calls | final calls | total calls | final pass distribution |
| --- | ---: | ---: | ---: | ---: | --- |
| empty navigation (base packing check) | 200 | 208 | 208 | 416 | 1:193, 2:6, 3:1 |
| actual saved EXP157 fact inventory | 20 only | 22 | 23 | 45 | 1:18, 2:1, 3:1 |
| synthetic moderate: 7×1×160 chars | 200 | 208 | 215 | 423 | 1:187, 2:11, 3:2 |
| synthetic schema upper: 7×3×360 chars | 200 | 208 | 227 | 435 | 1:177, 2:19, 3:4 |

saved scenario의 의미는 실제 navigation이 fast20 final packing을 `22→23`으로만
늘렸다는 점이다. 20-record 결과를 200-record submission projection으로 사용하지 않는다.

## 결정

기술적으로는 final stage에 complete source를 유지할 수 있다. 하지만 dev-200 기준 최소
416 calls, realistic ledger upper 423–435 calls로 one-stage EXP154의 208 calls보다 약
2배다. 1,853 evaluation notices에 대한 vLLM 2-hour 제한에서는 runtime-risk가 높다.

따라서 이 architecture를 바로 submission candidate로 만들지 않는다. 다만 information
loss 없이 stage separation의 품질 가능성을 보려면, 먼저 fast20 전용 implementation에서
다음을 모두 고정해 검증할 수 있다.

1. stage1은 법률 판단/0/1을 내지 않는 source fact collector다.
2. stage2는 navigation이 없어도 complete source를 갖고, navigation null을 final 0으로
   사용하지 않는다.
3. exact stage2 dynamic packing 후 source/metadata/card/CSV coverage가 전수 PASS다.
4. fast20의 quality가 EXP154보다 의미 있게 높고 independent holdout에서도 유지될 때만
   runtime optimization 또는 submission feasibility를 검토한다.

이 순서를 건너뛰고 fact category/문구 상한을 dev label에 맞추어 늘리지 않는다.

## 원격 실행 중단 기록

구현·mock·semantic/admission gate를 통과한 뒤 OpenRouter fast20을 세 번 시도했으나,
모두 동일한 provider 오류로 완결하지 못했다.

| Config | concurrency | 성공 행 / 20 | 종료 사유 |
| --- | ---: | ---: | --- |
| EXP160 | 20 | 18 | `HTTP 402`: available credits given in-flight requests 초과 |
| EXP161 | 4 | 15 | 동일 |
| EXP162 | 1 | 13 | 동일 |

EXP162도 한 worker로 각 공고의 stage1→final을 순차로 수행했으므로, 이 결과는 단순 client
동시성 조절로 해결되지 않았다. 세 config는 모두 `lifecycle: invalidated`로 보존하며,
partial prediction은 품질 측정이나 후보 선별에 사용하지 않는다. 이는 full-final의 의미적
완결성 실패가 아니라 현재 원격 provider의 누적 credit/reservation 한도 실패다. 다음 검증은
로컬 vLLM runtime budget을 실제로 확보할 수 있을 때만 재개한다.
