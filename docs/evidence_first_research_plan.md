# Evidence-first 입력 아키텍처 연구계획

## 목적

현재의 개선 폭은 카드 문구나 일부 항목 규칙을 고치는 수준에 머물렀다. 공개
검증도 이를 뒷받침한다. EXP-120의 `4,000자 + card v6 + 단일 V/E`는 dev-200
`0.248932`, 공개 `0.244317`이었고, v2/v3/v21 고정 규칙을 더한 EXP-123은
dev-200 `0.317797`이지만 공개 `0.260446`이었다. 따라서 dev 오류를 보고
항목별 규칙을 늘리는 경로는 중단한다.

이번 연구 질문은 다음 하나다.

> **Gemma가 실제 위반 근거를 보지 못해서 틀리는가? 그렇다면 모든 문서에서
> 원문 근거 후보를 고회수율로 모아 한 번의 V/E 판단에 제공하면, 4,000자
> 순서 prefix보다 일반화 가능한 개선을 만들 수 있는가?**

법령 원문 RAG, 법령 요약 bundle, full-document split/OR 병합, v-only 출력,
항목별 dev 규칙 확장은 이 연구의 treatment가 아니다. 법령 해석은 계속
decision card에만 압축한다.

## 고정 control

Control은 EXP-120과 동등한 다음 정책이다.

- Gemma 4 26B A4B IT, temperature 0, 고정 seed
- 24개를 한 번에 V/E JSON으로 출력
- official baseline prompt profile + decision cards v6
- 문서 순서 기반 4,000자 context
- metadata는 baseline과 동일, 법령 원문·제품 CSV 문맥·추가 rule 없음

새 후보는 이 control에서 **입력 문서 context 선택만** 바꾼다. 출력 schema,
card, decoding, metadata, merge, provider scheduling은 변경하지 않는다.

## 단계와 중단 조건

### E0 — 원문 증거 관측성 audit (offline, 필수)

`scripts/audit_evidence_first.py`가 dev gold evidence를 사용해 아래를
기록한다. gold label/evidence는 평가에만 사용하며, retrieval query나 prompt
생성에는 절대로 쓰지 않는다.

1. positive cell을 `nonempty evidence`, `blank evidence`, `source-unresolved`로
   분류한다.
2. nonempty evidence가 어느 문서 유형과 paragraph/line 단위에 있는지 확인한다.
3. 실제 EXP-120의 4,000자 context에 gold evidence가 포함되는 비율을 계산한다.
4. gold evidence를 포함하는 원문 paragraph들의 **oracle 합집합** 길이를 재어,
   source-unit 기반 입력이 구조적으로 가능한지 확인한다.

이 audit은 성능 점수나 retrieval 성능이 아니다. 특히 blank-evidence positive와
문서+metadata 결합 항목을 “retrieval 실패”로 부르지 않는다.

E1로 가기 위한 최소 조건은 다음과 같다.

- source-unresolved nonempty evidence가 0건이다. 0이 아니면 data/evidence
  canonicalization부터 고친다.
- 4,000자 context 밖의 nonempty gold evidence가 충분히 존재한다. 그렇지 않으면
  context selection은 큰 방향이 될 수 없다.
- paragraph oracle pack의 median과 p90이 최종 token 예산 안에 들어갈 현실적
  여지가 있다. 불가능하면 1회 evidence-first context를 설계하지 않는다.

### E1 — label-blind high-recall selector audit (offline, 필수)

E0 통과 후에만 구현한다. selector는 항목표의 항목명과 card의 `prompt_text`,
문서 type/title, metadata의 사람 친화적 값만 사용한다. dev labels/evidence,
특정 dev ID, 임의 길이 cutoff를 사용할 수 없다.

후보 selector는 아래 세 점수의 **합집합**이다.

- Korean lexical/BM25: card의 법적 행위·대상·수치 표현과 문서의 title/paragraph
- 허용된 BGE-M3: card query와 원문 paragraph의 semantic score
- 구조 보정: 공고문 title/표 heading/metadata와 같은 source-aware 단서

이 단계의 산출물은 원문 그대로의 document/offset/span을 갖는 candidate manifest다.
임베딩 또는 점수는 최종 evidence가 아니며, 원문을 대체하지 않는다.

E2로 가려면 고정 dev audit에서 다음을 충족해야 한다.

- non-absence nonempty gold evidence의 overall recall이 95% 이상
- positive가 있는 각 item에서 recall 80% 이상, 0% item 없음
- 각 notice의 selector union이 exact Gemma tokenizer 기준 prompt budget에 들어감
- 첫 4,000자보다 evidence recall이 명확히 상승함

이 gate를 못 넘으면 selector를 Gemma에 연결하지 않고 실패 원인(lexical, semantic,
chunking, table/layout)만 기록한다. BGE parameter를 dev F1에 맞춰 반복 조정하지 않는다.

### E2 — Gemma paired pilot (유료, 24–32 notices)

E1을 통과할 때만 실행한다. versioned, label-blind, 고정된 cohort에 대해 control과
treatment를 같은 config에서 비교한다.

- control: EXP-120의 4,000자 ordered context
- treatment: 동일 prompt의 `# 공고 자료`만 selector가 고른 원문 span union으로 교체
- V/E schema와 Python evidence validation은 완전히 동일
- run마다 `max_requests`, `max_cost_usd`, raw response, tokenizer count, source
  candidate manifest, per-cell error ledger를 남긴다.

승격 조건은 Macro positive-F1 상승 **및** recall 비감소, non-absence evidence
validity 100%, parse failure 2% 이하이다. F1만 높은 경우에는 TP/FP/FN과 changed
cell별 source visibility를 검사한다. 이 조건을 통과하지 못하면 dev-200으로 확대하지
않는다.

### E3 — 독립 holdout과 dev-200 (유료)

E2를 통과한 한 가지 selector 설정만 label-blind holdout에서 재현한다. 같은 방향과
evidence/runtime 조건을 만족할 때만 dev-200 paired confirmation을 한다.

dev-200에서는 headline macro F1 외에 item별 TP/FP/FN/P/R/F1, source coverage,
first-4k 대비 recovered evidence, input/completion token, 호출 수, 형식 오류,
예측이 바뀐 모든 cell의 error ledger를 비교한다. 1,853건 runtime projection은
2시간 이하여야 한다.

## 제외된 재시도

- full split + OR/AND merge: 문서-local 판단의 speculative positive가 FP를 폭증시킨
  결과가 있으므로 이번 selector 연구와 결합하지 않는다.
- v-only 또는 anchor-only output: 기존 실험에서 recall/evidence contract가 무너졌다.
- 법령 원문·요약 RAG: Gemma prompt에는 넣지 않는다.
- v별 dev 오류를 바탕으로 만든 추가 Python rule: EXP-123 공개 전이 결과상 이 연구의
  개선 수단으로 취급하지 않는다.

## 의사결정 원칙

이 계획의 성공은 “어떤 fast panel 점수가 높다”가 아니다. E0/E1의 source coverage와
E2/E3의 독립 paired 결과가 모두 맞아야 한다. E1이 구조적으로 불가능하거나 E2가
실패하면 즉시 이 방향을 닫고, 다음 대형 가설은 원문 text가 아닌 표·layout·metadata
표현 보존 문제로 전환한다.
