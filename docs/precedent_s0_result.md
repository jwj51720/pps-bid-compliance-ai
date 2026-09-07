# 무라벨 선례 전략 S0 결과

계획: [strategic_self_label_precedent_plan.md](strategic_self_label_precedent_plan.md)

## 결론

무라벨 20k에 대한 **현재의 lexical/card 기반 case retrieval은 S1 Luna self-label로
승격하지 않는다.** 두 무비용 audit 모두 “문서 종류나 공통 단어가 맞는다”는 약한
신호는 보였지만, 실제 항목 판정에 필요한 trigger의 의미적 일치까지 보이지 못했다.
따라서 316개 후보를 Luna로 라벨링하는 비용을 쓰지 않는다.

이는 generic case RAG가 fresh cohort에서 재현되지 않았던 WSL 결과와도 일치한다.
새로운 선례 branch는 source-preserving teacher record의 **label-blind semantic query**를
먼저 정의하고 검증하기 전에는 다시 열지 않는다.

## S0A — gold-evidence lexical 상한

실행: `python scripts/audit_precedent_lexical_fit.py`

- dev nonempty gold evidence 54개를 평가 전용의 낙관적 query로 사용했다.
- 20k 공고의 전체 38,862 source documents를 원문 손실 없이 두 번 stream했다.
- top-1에서 gold source와 같은 문서 유형 비율은 0.759, top-3은 0.907,
  top-1 query term 절반 이상 일치는 0.852였다.

수치만 보면 좋아 보이지만, 이는 충분조건이 아니다. 다음은 상위 문서가 실제 같은
판정 trigger가 아니었던 대표 사례다.

| dev evidence item | lexical 상위 후보가 겹친 이유 | 왜 선례로 부족한가 |
|---|---|---|
| v3 해양탐사 4.55억 실적제한 | `공고일`, `5년`, `단일`, `수행실적` | 후보는 장학 기념품 제안요청서로, 실적제한·금액비율의 법적 조건이 없다. |
| v4 국제회의 실적제한 | `국제회의`, `대행`, `최근` | 후보는 회의 대행 제안요청서의 표지·사업 개요이며 참가자격 한정 여부가 확인되지 않는다. |
| v9 Akron Brass 모델명 | `Brass` 한 단어 | 후보는 수소용기 재질 `BRASS` 규격으로 제조사/모델 강제가 아니다. |
| v22 사업설명회 참석제한 | `사업설명회`, `참석` | 후보 문구 자체는 가까울 수 있으나 협상계약·실제 참가제한이라는 card 조건까지는 lexical score가 검증하지 못한다. |

artifact: ignored `outputs/precedent-s0a-lexical-fit/report.json`, `report.md`.

## S0B — card-only label-blind candidate pool

실행: `python scripts/build_precedent_pool_s0b.py --top-per-item 20`

이 selector는 dev와 dev labels를 전혀 읽지 않고, 고정 `decision_cards_v6`와
`train_unlabeled` 원문만 사용했다. 24항목 × 상위 20개에서 316개 고유 공고가 나왔다.
그러나 상위 결과가 card의 판정 서술어에 지배됐다.

- v3: `기준`, `다르거나`, `배수`, `확인한다` 때문에 일반 물품 납품 규격서가 1위였다.
- v10/v11/v16/v18/v20: `모든 문서`, `순서`, `조건`, `확인한다` 때문에 같은 과업지시서가
  반복 선택됐다. 부재 판정의 실제 제품·등록·증명 요건은 포착하지 못했다.
- v13: `참가자격`·`판정`만 겹친 대학 입찰공고가 1위였고 경쟁제품·소기업 제한 사실이
  없었다.
- v24: `같은`, `다른`, `필드`만 겹친 과업지시서가 1위였다. v24의 문서↔meta 값 대조와
  무관하다.

artifact: ignored `outputs/precedent-s0b-card-pool/pool.json`, `pool.md`.

## 추가 구조 감사: evidence gate

EXP120의 200개 prediction을 raw model judgment와 final submission row로 대조했다.
raw positive 100개와 final positive 100개가 동일했고, 24개 항목 전체에서 evidence
postprocessing에 의한 `1 → 0` 강등은 0건이었다. 즉 현재 EXP120의 낮은 recall을
evidence substring gate 탓으로 설명할 수 없다.

## 다음 판단

1. generic lexical/BM25 casebook과 card-only pool은 닫는다. BGE를 단순 재실행해도
   이 selector의 의미적 결함을 자동으로 해결한다고 가정하지 않는다.
2. 20k self-label은 비용이 큰 만큼, 다음에 열려면 current-notice의 source fact를
   label-blind하게 정규화해 같은 사실을 검색할 수 있다는 독립 검증이 필요하다.
   raw document/card similarity나 dev positive를 기준으로 한 pool은 금지한다.
3. 이제 남은 대형 가설은 (a) 고정 Gemma가 현재 공고에서 24개 조건을 읽는 실행
   구조 자체, 또는 (b) source-preserving teacher fact record를 만들고 그 record가
   실제로 queryable함을 보이는 구조다. 어느 쪽도 지금의 local card 문구 추가로
   대체하지 않는다.
