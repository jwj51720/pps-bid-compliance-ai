# EXP-120 공개 제출 이후 BFS 마일스톤

## 확정된 기준점

2026-09-05에 제출한 `pps_20260905_170543.zip`은 다음 정책이다.

- Gemma 4 26B A4B IT 단일 호출
- 순서 보존 공고문 문맥 4,000자
- decision cards v6
- 24개 `V/E` 동시 출력과 Python 원문-substring evidence 검증
- 16,384 token model length, 1,536 output-token reserve, batch size 128

| 기준 | Dev-200 macro positive-F1 | 공개 리더보드 | Dev 대비 차이 |
|---|---:|---:|---:|
| EXP-109 공식 V/E baseline | 0.223498 | 0.210360 | -0.013138 |
| EXP-120 card v6 | 0.248932 | **0.244317** | **-0.004615** |

이 제출은 dev-200이 이 정책군의 공개 리더보드 선택 기준으로 쓸 만큼 정렬됐다는
증거다. EXP-120은 앞으로의 모든 판단 정책의 고정 control이다. 다만 하나의 공개
제출은 test 분포 전체의 보장은 아니므로, 작은 cohort의 최고점이나 사후 threshold는
정책 승격 근거가 될 수 없다.

## 연구 원칙

1. Control과 treatment 사이에는 해석 가능한 한 가지 변화만 둔다.
2. 탐색은 사전 고정된 32-notice 층화 cohort에서 하고, 통과 후보만 독립 32-notice
   holdout으로 확인한다. 둘 다 통과할 때만 dev-200으로 승격한다.
3. 개별 항목의 문자 수, 키워드 빈도, 특정 dev ID에 맞춘 cutoff는 사용하지 않는다.
   모든 rule은 organizer source에 있는 의미적 조건과 완전 coverage/negative audit를
   가져야 한다.
4. final path는 매 notice의 실제 원문을 포함한 Gemma 호출을 적어도 한 번 수행하고,
   evidence는 항상 Python이 원문 substring으로 검증한다.
5. Luna는 최종 추론 대체제가 아니라 permitted teacher, error analyst, casebook
   constructor로만 쓴다. 호출 수와 달러 상한은 실험 config에 고정한다.

## BFS 분기와 승격 기준

| Branch | 한 가지 변화 | 근거와 위험 | 탐색 → 승격 gate |
|---|---|---|---|
| A. 출력 계약 | EXP-120의 `V/E`를 `V-only`, 또는 `V + 짧은 source anchor ID`로 교체 | evidence 생성이 판단 attention을 소모할 수 있다. 반대로 과거 flat V-only는 판단 신호를 잃었다. | 동일 input 32 paired; anchor-ID arm의 valid evidence 100%, macro-F1 +0.02 이상, recall 비감소 → 독립 32 holdout에서도 같은 방향 → dev-200 |
| B. 조건부 e-prime | 첫 판단 뒤 불확실/양성 후보만 판단용 source fact를 추출해 재판정 | 전역 extract→adjudicate와 전역 e-prime은 이미 recall 실패했다. 따라서 전체 두 단계화는 금지한다. | trigger 정의는 label-blind; changed cell 순증 정답 +3 이상, 새 hard-negative FP ≤1, runtime projection 통과 → holdout → dev-200 |
| C. 짧은 공식 법령 문맥 | card v6 대신 항목별 조건·예외를 포함한 고정 official-law excerpt | Luna official ledger는 강한 신호였으나 Gemma 16건 transfer는 약했다. broad law injection은 과거 실패했다. | card-only와 같은 32 paired; 두 독립 cohort에서 모두 macro-F1 상승, absence FP 증가 없음, budget 통과 → dev-200 |
| D. 구조화 casebook | 20k 공고문에서 Luna가 만든 source-grounded 사례를 item/doc-type별로 제한 retrieval | generic case RAG는 8건 신호가 16건에서 재현되지 않았다. 템플릿 유사도만으로 label transfer 금지. | source hash/prompt/model/validation을 보존; no-case 대조군 대비 두 cohort 모두 개선, retrieval이 raw source evidence를 대체하지 않음 → dev-200 |
| E. 결정적 합성 | 완전 관측이 입증된 source predicate만 EXP-120의 해당 항목에 교체 | v2/v3/v21 외 넓은 keyword/rule은 과적합 위험이 높다. | predicate positive coverage 100%, meaningful negative audit, 다른 23개 cell 불변, dev-200 전체 개선 → 제출 후보 |

## 다음 실행: A — 출력 계약의 고립된 비교

### 질문

현재 EXP-120의 판단 성능은 evidence를 문장으로 생성하는 과정에 의존하는가, 아니면
source anchor를 제한적으로 요구하면서 V 판단 부담을 줄일 수 있는가?

### 고정 요소

- model, temperature, seed, card v6, 4,000-character ordered notice input
- 24개 항목의 정의와 label order
- same record IDs, same evidence resolver, same positive-class macro-F1
- schema/transport retry policy

### 세 arm

1. **Control:** 현재 EXP-120 V/E output.
2. **A1:** 24개 binary V만 출력. 이는 diagnostic arm이며 evidence 없이 제출 후보가 될 수 없다.
3. **A2:** V와 positive item별 Python-generated source anchor ID만 출력한다. 모델은 original
   source 후보 중 하나만 고르고, Python이 ID에서 unchanged evidence를 복구한다.

`A2`만이 제출 승격 대상이다. 후보 source unit은 문서/line 기반의 unchanged span이며,
500 characters를 넘으면 admissible segment를 사전에 만들고 source offset을 보존한다.
그 어떤 model rationale도 evidence로 쓰지 않는다.

### Cohort와 의사결정

- 탐색 32건은 모든 활성 label positive, absence-item, long/short notice, document topology를
  층화한 versioned manifest로 고정한다. 선정 로직과 ID hash를 실행 전에 기록한다.
- 첫 32건에서 A2가 control보다 macro-F1 `+0.02` 이상, recall 비감소, valid non-absence
  evidence 100%, malformed recovery 후 실패율 2% 이하일 때만 독립 holdout 32건으로 간다.
- holdout에서도 방향이 유지되면 dev-200 paired confirmation을 한다. dev-200에서 control 대비
  `+0.015` 이상이고 1,853-notice runtime projection이 2시간 이내일 때만 제출 후보로 만든다.
- 그 외 결과는 실패 또는 부분성공으로 기록하고, output contract를 재문구화해 반복하지
  않는다. 부분성공은 changed-cell error dossier가 하나의 해결 가능한 원인을 보일 때만
  한 번 repair한다.

## 보류 및 금지

- 4,000자보다 큰 임의 char cutoff, document split/OR merge, broad full-law injection,
  generic case RAG, unconditional e-prime, 또는 V-only를 그대로 제출하는 것은 현 시점에서
  승격하지 않는다.
- 동일 cohort에서 prompt를 여러 번 바꿔 최고점을 고르는 방식, 800건 반복, labels를
  casebook prompt에 주입하는 방식은 금지한다.
- 최종 Gemma 경로를 Luna만으로 대체하거나 learned weight/model을 만드는 방식은 금지한다.

## 제출 및 통합 gate

새 후보는 `incubator`에서 dev-200 artifact, per-label metrics, runtime projection, evidence
validation, exact staged-zip mock test를 갖춘 뒤에만 root integration proposal로 이동한다.
현재 root와 dev-wsl 외부 dev 작업은 수정하지 않는다. dev 병합 시에는 이 문서와
`incubator/AGENTS.md`를 기준으로 path, API transport, submission interface만 호환성
검토하며 실험 정책을 자동 병합하지 않는다.
