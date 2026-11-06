# 경쟁제품 CSV BGE 후보검색 capability audit

작성: 2026-09-18, dev / mac

## 목적

v26 카드의 기준은 보수됐지만 v10–v18 일부 notice에는 exact product code가 없어 경쟁제품
적용 사실이 불명이다. 615행 organizer 경쟁제품 CSV만 검색 대상으로 삼을 때, fixed
`BAAI/bge-m3`가 실제 구매대상 표현에서 올바른 고시 행을 작은 top-k 안에 회수할 수 있는지
먼저 측정한다.

이 audit은 label이나 legal judgment를 만들지 않는다. raw 법령, 사례 corpus, dev prediction,
gold evidence를 query/candidate/ranking에 쓰지 않는다. gold v10 label은 ranking 완료 후 panel별
diagnostic 목록에만 붙인다.

## Query와 candidate

- query: organizer metadata의 업무구분, 세부품명 **이름**(숫자 code 제거), 공고문 첫 1,600자.
- candidate: organizer CSV 원행의 세부품명, 제품명, 특이사항.
- model: fixed `baai/bge-m3`, cosine ranking.
- 검색범위: `competition_products_v1.json`의 전체 615행만.
- 출력: 모든 dev200의 top10과 score, exact-code matched notice의 target-row rank, fixed
  fast/holdout v10-positive의 label-blind top candidates.

exact code는 target rank 평가에만 쓰며 embedding query에서 제거한다. exact-code matched
notice의 target row recall@1/3/5/10이 낮으면 BGE 후보 prompt를 구현하지 않는다. 높더라도
similarity를 적용 판정 또는 evidence로 쓰지 않는다.

## 다음 gate

회수율이 충분하면 v10 하나의 source-grounded candidate prompt를 별도 version으로 만든다.
후보 원행의 이름·제품명·특이사항을 non-authoritative하게 제공하고 Gemma가 actual purchased
object, condition, direct-production absence와 전체 원문을 다시 대조한다. Python은 similarity로
v10을 정하거나 unknown을 matched로 바꾸지 않는다. fast/holdout precision을 통과하기 전에는
v11–v18로 일반화하지 않는다.

## Headline v1 중간 결과와 사전 선언된 보완

공고문 첫 1,600자를 한 query로 쓴 v1은 exact target recall@1/3/5/10이
`.3788/.5152/.6212/.7121`이었다. exact target 중 metadata와 문서에 모두 나타난 행은
top3 `1.0`이지만 document-only 행은 top10 `.6042`였다. 특히 제목 뒤의 긴 계약 boilerplate가
제품 의미를 희석하는 사례가 확인됐다.

이를 gold/키워드 규칙 없이 보완하는 v2는 모든 제공 문서를 900자, overlap150의 고정 chunk로
나누고 문서별 round-robin 순서로 최대12개를 선택한다. 각 CSV 행의 점수는 해당 notice chunk
점수의 maximum이다. 후보 행, model, top-k는 유지한다. v2도 recall@10이 충분하지 않으면
Gemma prompt probe를 중단한다.

## Source-chunk v2 결과와 중단 결정

2,199개 source chunk를 embedding한 v2 exact target recall@1/3/5/10은
`.3788/.5303/.6667/.7424`였다. headline v1의 top10 `.7121`에서 개선은 `+.0303`뿐이며,
exact target 66행 중 약 26%가 여전히 top10 밖이다. exact-code target 자체도 실제 구매대상과
참가자격용 별도 code가 섞인 불완전 proxy이므로 이 수치보다 실제 precision이 더 높다고
가정할 수 없다.

따라서 사전 gate를 통과하지 못했다. BGE 후보를 model prompt에 넣는 v10 유료 probe나
submission runtime 검색은 구현하지 않는다. 이 결과는 입력 완결성 보수가 아니라 organizer가
제공하지 않은 exact 적용 fact를 유사도로 안정적으로 복원하기 어렵다는 capability 한계다.
