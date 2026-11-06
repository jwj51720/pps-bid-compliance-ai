# 법령 RAG 전략: 공고·메타·조문을 연결하는 재현 가능한 설계

## 이 문서의 결론

이 대회의 RAG는 법령 패키지 전체를 공고마다 붙이는 작업이 아니다. 공고의
메타와 원문에서 **어떤 법 체계·금액·품목·제한 유형이 적용되는지 먼저
판별**하고, 해당 판정에 필요한 **완결된 공식 조문 chunk**만 골라 Gemma에
보이는 작업이다.

권장 순서는 다음과 같다.

1. 공식 법령 파일을 조문·별표·표 단위의 provenance 있는 chunk로 만든다.
2. `적용계약법`, 금액, 세부품명번호, 업무구분, 계약·낙찰방법으로 검색
   후보를 먼저 줄인다.
3. 정확한 조문명·법령명·품목번호에는 BM25/문자열 검색을, 자연어 제한
   표현에는 허용된 `BAAI/bge-m3` dense retrieval을 함께 사용한다.
4. item별 quota와 token budget으로 작은 reference set을 확정한다.
5. 그 reference set은 모든 notice pass에 **그대로** 넣고, 토큰 예산을
   넘을 때는 reference가 아니라 notice 문서만 분할한다.

EXP-005의 결과는 이 원칙을 뒷받침한다. v1 관련 네 조문을 모든 24-item
공동 prompt에 고정 삽입하면 admission/split은 정상 동작했지만 dev macro F1은
0.213825에서 0.167873으로 하락했고 v1 F1은 개선되지 않았다. 그러므로
**고정된 대형 법령 묶음**이 아니라, item·공고별로 작고 완결된 retrieval이
필요하다.

---

## 1. 문제와 데이터의 실제 모양

### 1.1 한 공고가 LLM에 들어가는 구조

원본 `dev.jsonl.gz`의 한 줄은 하나의 공고다. 필드는 다음과 같다.

```json
{
  "id": "PPS-DEV-01",
  "docs": [
    {"doc_id": "D0", "type": "공고문", "text": "..."},
    {"doc_id": "D2", "type": "과업지시서", "text": "..."}
  ],
  "meta": {
    "적용계약법": "지방계약법",
    "계약방법": "제한경쟁",
    "낙찰방법": "협상에의한계약",
    "입찰추정가격": 281818182
  }
}
```

문서 순서는 `공고문 → 규격서 → 과업지시서 → 제안요청서 → 예외공표서`로
보존한다. dev 200건의 평균 원문은 17,580자이고, 제안요청서는 평균 19,837자로
가장 길다. 따라서 법령을 더하면 32,768-token model length 안에서 문서 분할이
현실적으로 발생한다. 전체 데이터 형태와 필드는 [data.md](data.md)에 기록돼
있다.

LLM이 받는 최종 chat은 개념적으로 아래와 같다.

```text
system:
  24개 항목의 판정 계약
  + [공식 참고 법령] retrieval이 선택한 완결 조문 chunk들

user:
  [공고 ID]
  [나라장터 입력 메타]
  [문서] 공고문/첨부문서 원문 또는 그 pass
```

법령은 판정 보조자료일 뿐이다. 제출 evidence `e1`~`e24`는 반드시 공고문 또는
첨부문서의 변경 없는 substring이어야 하며, 법령 text나 metadata를 evidence로
제출하면 안 된다.

### 1.2 평가 데이터와 실제 배포 데이터의 차이

dev는 200건이며 항목별 positive가 대략 5~8건이다. 실제 평가는 약 1,900건이고
분포가 다르다. 따라서 dev label을 retrieval corpus에 넣어 test의 정답처럼
사용하면 안 된다. dev 사례는 **오프라인 설계·평가용**이고, 최종 law corpus는
대회 제공 법령 패키지와 고시 CSV만으로 만든다.

---

## 2. 실제 사례로 보는 retrieval 필요성

아래의 공고 인용과 조문 출처는 모두 대회 제공 파일에서 가져왔다. 인용은
방법론 설명을 위한 것이며, test 추론에 dev 정답을 주입하라는 뜻은 아니다.

### 2.1 v1 — 특정 기관만 참가 가능: `PPS-DEV-01`

메타는 `지방계약법`, `제한경쟁`, `협상에의한계약`, 추정가격 281,818,182원이다.
공고문에는 다음 제한이 있다.

> “본 용역은 「고등교육법」 제2조에 따른 대학 또는 … 산학협력단만 참여 가능함”

이 문구는 단순히 “대학”을 검색하는 문제가 아니다. 지역·중소기업 제한도 같은
공고에 함께 있으므로, v1은 특정기관 한정이 허용되는 참가자격인지 구분해야
한다. item table은 v1에 국가계약법 시행령 제12·21조와 지방계약법 시행령
제13·20조를 연결한다.

**검색 query 예시**

```text
item=v1 | 적용계약법=지방계약법 | 계약방법=제한경쟁
공고 cue=대학, 산학협력단, 참여 가능함, 입찰참가자격
```

**가져올 법령 후보**

```text
지방자치단체를 당사자로 하는 계약에 관한 법률 시행령
  - 제13조(입찰의 참가자격)
  - 제20조(제한입찰에 의할 계약과 제한사항 등)
```

실제로 제13조 제1항은 “다른 법령에 따라 … 자격요건을 갖추어야 할 경우”
그 요건에 적합한 자만 입찰에 참가하게 하도록 하고, 제20조 제1항은
입찰참가자격을 제한할 수 있는 경우와 제한사항을 열거한다. 따라서 이 사례의
LLM 입력에는 조문 제목만이 아니라 두 조문 전문을 넣어, `대학/산학협력단`이라는
공고 문구가 일반 참가자격인지 제한입찰의 별도 제한인지 문맥 안에서 판단시킨다.

출처는 `data/raw/open/data/법령패키지/법령/` 아래의 같은 이름 `.txt`다. 조문
전문을 하나의 chunk로 보존하고, 제13조 일부나 제20조 일부만 임의로 잘라
법적 조건을 잃지 않는다.

### 2.2 v3 — 실적제한 1배수 이상: `PPS-DEV-04`

메타는 `국가계약법`, 추정가격 318,181,818원이고 공고는 다음을 요구한다.

> “최근 5년 간 단일 건으로 455,000,000원 이상(기초금액의 130% 이상)의 …
> 수행실적 … 제출이 가능한 업체”

여기서는 BM25가 `455,000,000`, `130%`, `실적제한`, `최근 5년`을 잘 잡는다.
그러나 모델이 법적 허용 기준과 이 공고의 금액을 비교하려면 item table의
국가계약법 시행령 제21조 및 `정부 입찰·계약 집행기준`의 제한경쟁 관련
조항을 함께 봐야 한다.

**중요한 설계점:** query에 공고 숫자를 그대로 넣되, 숫자만 비슷한 다른
조문을 다수 넣지 않는다. `item=v3`, `법체계=국가`, `제한=실적` filter로
후보군을 먼저 한정한 뒤 lexical/dense score를 계산한다.

### 2.3 v13 — 소기업·소상공인 제한은 품목 상태와 함께: `PPS-DEV-16`

공고에는 다음 문구가 있다.

> “소기업자로서 … 소기업, 소상공인확인서를 소지한 업체이어야 합니다.”

동시에 직접생산확인증명서와 세부품명 `7811189902`도 적혀 있다. 이 사례가
보여 주는 핵심은 “소기업”이라는 단어만으로 v13을 1로 만들면 안 된다는 점이다.
경쟁제품 여부와 예외·품목 조건을 먼저 확인해야 한다.

이 항목은 일반 텍스트 RAG만으로 끝내지 말고 다음 두 retrieval을 결합한다.

```text
정확 lookup: 공고/메타의 세부품명번호 → 공식 경쟁제품 CSV 행
법령 retrieval: 중소기업제품 구매촉진 및 판로지원에 관한 법률 제7조 및
               관련 시행령/예외 조문
```

정확 code lookup 결과는 LLM에게 “경쟁제품 CSV에 매칭됨/매칭되지 않음”과
매칭 행의 provenance로 제공한다. 매칭되지 않았다는 사실만으로 법적 예외나
위반이 자동 확정되지는 않으며, LLM은 공고 문구와 관련 조문을 함께 판단한다.

### 2.4 v20 — SW 참여제한은 금액과 예외를 함께 읽는다: `PPS-DEV-24`

`PPS-DEV-24`는 국가계약법 공고이며, 공고문에 “소프트웨어사업자(컴퓨터관련
서비스사업)”와 정보시스템 유지관리 세부품명이 보인다. v20은 부재탐지 항목이
므로, 단어가 있다고 끝나지 않는다. 사업이 SW인지, 사업금액 구간은 무엇인지,
대기업 참여제한·예외가 공고에 어떻게 명시됐는지를 함께 본다.

관련 공식 지침에는 다음과 같은 구조가 있다.

> “제2조(사업금액의 하한) … 하한은 별표 1과 같다.”

> “사업금액은 … 추정가격에 부가가치세를 포함한 금액으로 한다.”

따라서 query에는 `정보화사업여부`, 업무명, SW/정보시스템 cue, 추정가격과
기간을 포함한다. retrieve할 unit은 지침 제2·3조와 필요한 별표 1의 **해당
행을 포함한 표 chunk**다. 표는 행만 고립시키지 말고 header·단위·조건을 같이
보존한다.

### 2.5 v23 — 법령보다 날짜·계약방법이 먼저인 항목: `PPS-DEV-27`

공고문에는 다음이 있다.

> “사업설명회 : 2026. 2. 3.(화) 14:00”

> “제안서 및 가격입찰서 제출 … 2026. 2. 6.(금)”

이 공고는 지방계약법·협상에 의한 계약이다. 여기서는 우선 Python이 설명회와
제출·공고일 날짜 후보를 문서에서 추출하고, 메타의 계약방법으로 v23 적용성을
gate한다. 그 뒤에만 지방계약법 시행령 제35조와 `지방자치단체 입찰시 낙찰자
결정기준`의 협상계약 절차 chunk를 붙인다. 날짜만 비슷한 조문을 dense search로
무차별 수집하는 것은 도움이 되지 않는다.

### 2.6 v24 — Law RAG를 하지 말아야 하는 반례: `PPS-DEV-29`

공고문은 “용역금액: 금37,930,000원(추정가격 34,481,818원 …)”이라고 쓰고,
메타에는 입찰추정가격 36,118,183원이 있다. v24의 핵심은 법령 해석이 아니라
문서 수치와 나라장터 메타의 같은 필드를 정규화해 대조하는 것이다. v24에는
법령 chunk를 배정하지 않고, 숫자·날짜·지역·계약방법별 deterministic comparison
fact를 LLM에 제공하거나 Python에서 보정한다.

---

## 3. 법령 corpus를 만드는 방법

### 3.1 chunk 경계

권장 최소 단위는 다음과 같다.

| 원본 형태 | chunk 단위 | 반드시 함께 둘 것 |
|---|---|---|
| 법률·시행령 | 조문 하나 | 조 제목, 항·호 전체, 법령명, 시행/개정 표기 |
| 예규·지침 | 조문 또는 절 | 제목, 정의/예외가 이어지면 인접 조문 |
| 별표·표 | header + 적용조건 + 관련 행 | 단위, 각주, 표 제목 |
| 경쟁제품 CSV | 세부품명번호 행 | 파일 버전, 열 이름, 직접구매 여부 |

문장 길이로 1,000자를 기계적으로 자르는 naive chunking은 조문 조건과 예외를
분리한다. 너무 긴 조문은 문단 단위 child chunk를 만들 수 있지만, parent 조문
ID와 full-text checksum을 함께 유지하고 retrieval 결과에는 필요한 인접 문단을
재조립해야 한다.

### 3.2 chunk manifest 예시

```json
{
  "chunk_id": "law:local-decree:art-20",
  "source_path": "법령패키지/법령/지방자치단체를 당사자로 하는 계약에 관한 법률 시행령.txt",
  "source_sha256": "…",
  "title": "제20조(제한입찰에 의할 계약과 제한사항 등)",
  "law_family": "지방계약법",
  "items": ["v1", "v2", "v3", "v5", "v13"],
  "kind": "article",
  "text": "원문 그대로의 완결 조문"
}
```

`data/derived/law_chunks.jsonl`, BM25 index, BGE vectors, code lookup table,
manifest를 같은 derived-data version으로 기록한다. 원본 `data/raw/`는 재배포
하지 않지만, derived artifact에는 원본 경로·SHA-256·생성 command를 남겨 다른
환경에서 똑같이 재생성할 수 있게 한다.

---

## 4. 검색 전략의 선택지

| 방식 | 동작 | 강점 | 실패 방식 | 권장 용도 |
|---|---|---|---|---|
| Naive static RAG | item table의 관련 조문을 모두 삽입 | 가장 단순, audit 쉬움 | EXP-005처럼 무관한 23개 item을 흔듦 | 초기 smoke test만 |
| BM25 | 법령명·조문·숫자·품목번호·정확 문구 검색 | 법령 citation/숫자에 강함, 빠름 | 동의어·문맥 표현 누락 | 반드시 포함 |
| BGE dense | 공고 cue와 법령 chunk embedding 유사도 | “참여 가능”, “참가자격 제한” 같은 표현 변형 | 숫자/조문명 exactness 약함 | BM25 보완 |
| Hybrid RRF | BM25와 BGE 순위를 reciprocal-rank fusion | 한 방식의 누락 완화 | item gate 없으면 여전히 잡음 | 기본 retrieval |
| Metadata/code gate | 법체계·품목·금액·계약방법으로 후보 filter | 정확하고 token 절약 | 불완전 메타에 취약 | retrieval 이전 필수 단계 |
| LLM wiki/card | 공식 원문을 item별 조건·예외 card로 구조화 | 판정 경계가 명확해짐 | 요약이 원문을 왜곡할 수 있음 | 원문 chunk와 병행 |
| Gemma rerank | top-N의 적용성을 Gemma가 재정렬 | 법적 문맥 판단 가능 | 호출·시간 비용 증가 | 소수 애매 case만 |

### 4.1 Naive RAG가 유용한 곳과 멈춰야 할 곳

가장 먼저 할 수 있는 것은 v1의 네 조문처럼 item table에 있는 조문을 매번
붙이는 방법이다. 이는 token accounting과 출처 추적을 검증하는 smoke test로는
좋다. 하지만 EXP-005에서 full context 대비 macro F1이 하락했으므로, 이것을
성능 전략으로 일반화하면 안 된다.

### 4.2 BM25: 정확한 키가 있는 법령 검색

다음은 BM25 query에 포함해야 할 강한 키의 예다.

```text
v3: "실적", "최근 5년", "130%", "제한경쟁", "국가계약법"
v13: "소기업", "소상공인", "직접생산", "7811189902"
v20: "소프트웨어사업자", "대기업", "사업금액의 하한", "유지관리"
v23: "협상에 의한 계약", "사업설명회", "제안서"
```

법령명이 공고에 직접 나타난 경우에는 이 방식이 특히 안정적이다. 다만 공고의
“참여 가능함”과 법령의 “참가자격”처럼 표현이 다르면 BM25만으로 부족하다.

### 4.3 Dense retrieval: BGE-M3는 보완자

허용된 `BAAI/bge-m3`에 query를 넣을 때도 item과 facts를 명시적으로 넣는다.

```text
[item=v1] [law=지방계약법] [contract=제한경쟁]
대학 또는 산학협력단만 참여 가능하다고 정한 입찰참가자격 제한의 허용 조건
```

법령 chunk도 제목과 법체계 prefix를 embedding text에 포함한다. 단순히 원문만
embedding하면 서로 다른 법의 “참가자격” 조문이 섞일 수 있다.

### 4.4 Hybrid retrieval와 deterministic gate

권장 점수는 `RRF(BM25 rank, BGE rank)`처럼 단순하고 inspect 가능한 결합이다.
그보다 앞단에서 다음 gate를 적용한다.

```text
적용계약법=지방계약법  → 지방계약법 chunk 우선, 국가계약법은 기본적으로 제외
세부품명번호 존재       → 경쟁제품 CSV exact lookup을 먼저 수행
업무/공고 cue=SW        → v20 지침·별표 후보를 활성화
낙찰방법≠협상           → v22/v23 관련 법령 quota를 0 또는 낮춤
```

이 gate는 학습 모델이 아니라 대회 제공 메타와 item table을 이용한 deterministic
전처리이므로 audit가 쉽다. metadata가 `미입력`이거나 누락이면 hard exclusion보다
fallback 후보로 남긴다.

---

## 5. LLM wiki와 decision card

LLM wiki는 법령 원문을 대체하는 요약이 아니라 retrieval을 안내하는 작은
**source-backed decision card**여야 한다. 생성에 외부 LLM을 쓰더라도 입력은
오직 대회 제공 법령·고시·공고여야 하며, model/prompt/temperature/source hash를
저장한다.

```json
{
  "item": "v13",
  "gates": ["경쟁제품 여부", "계약법", "가격/예외", "소기업 제한 문구"],
  "required_facts": ["세부품명번호", "입찰추정가격", "적용계약법"],
  "source_chunks": ["law:sme-purchase:art-7", "notice:competitive-products-csv"],
  "do_not_infer": ["소기업 문구만으로 경쟁제품 여부를 추정하지 않음"]
}
```

card의 역할은 (a) retrieval query 생성, (b) top-k chunk의 최소 필요 집합 선택,
(c) LLM에게 확인 순서를 주는 것이다. 최종 prompt에는 card와 함께 원문 chunk
ID/본문을 넣어, card의 오해·환각을 원문으로 교정할 수 있게 한다.

---

## 6. Token budget과 split의 정확한 계약

### 6.1 순서

```text
notice + meta
  → deterministic facts / item gates
  → BM25 + BGE hybrid retrieve
  → complete reference chunks selected
  → final system + user chat template token count
  → fit: one pass
  → overflow: notice docs only split into ordered passes
  → every pass receives the identical selected references
  → 24 labels OR-merge; earliest positive evidence retained
```

현재 예산은 32,768에서 2,500 output reserve를 뺀 30,268 input tokens다. EXP-005
에서는 16,620자 v1 reference를 넣자 dev 200건 중 21건이 overflow해 225 pass가
생겼다. 이 사실은 test에서 더 긴 공고가 있을 때를 대비해 반드시 final template
기준으로 admission해야 함을 보여 준다.

### 6.2 reference가 예산을 초과할 때

법령은 선택된 완결 chunk라면 자르지 않는다. 아래는 올바른 처리다.

```text
reference + system contract + metadata > 30,268
  → 오류/telemetry: fixed context overflow
  → retrieval stage에서 낮은 우선순위 chunk 제거 또는 더 작은 완결 단위 선택
  → 다시 token count
```

잘못된 처리:

```text
법령의 뒷부분을 문자열 기준으로 자르기
법령을 첫 pass에만 넣기
법령을 빼고 공고만 분할한 뒤 조용히 계속하기
```

법령 reference는 evidence source가 아니므로, 어느 pass가 positive여도 evidence
해결은 항상 그 pass의 공고 원문에서 한다.

### 6.3 실제 prompt fragment 예시

```text
[공식 참고 법령]
[law:local-decree:art-20 | v1]
제20조(제한입찰에 의할 계약과 제한사항 등) ...

[나라장터 입력 메타]
적용계약법: 지방계약법
계약방법: 제한경쟁

[문서]
[공고문:D0]
... 대학 또는 산학협력단만 참여 가능함 ...
```

실제 최종 messages는 EXP-005의 `outputs/.../inputs.jsonl`처럼 pass별로 저장한다.
새 RAG 실험도 `retrieval.jsonl`(query, gate, 후보, score, selected chunk IDs,
token count)과 `inputs.jsonl`을 함께 남겨야 한다.

---

## 7. 추천 구현 순서

### Phase A — source-preserving corpus와 deterministic facts

1. 법령·예규를 조문/별표 chunk로 만들고 source hash를 기록한다.
2. item table의 국가/지방 법령 매핑을 chunk ID에 연결한다.
3. 경쟁제품 CSV의 세부품명번호 exact lookup을 derived table로 만든다.
4. 금액, 날짜, 지역, 계약방법, SW cue, 문서별 keyword window를 추출한다.

이 단계는 LLM 호출 없이 검사 가능해야 한다. 특히 v10~v18은 code lookup과
금액 bracket이 먼저이고, v24는 비교 fact가 먼저다.

### Phase B — BM25 baseline

각 notice에서 item별 query를 만들되, 최종 prompt에는 모든 item의 top-k를
무제한 합치지 않는다. 예를 들어 item family별로 1~2개, 전체 4~8 complete chunks
같은 상한을 둔다. `retrieval.jsonl`의 top-k recall과 token cost를 먼저 평가한다.

### Phase C — BGE hybrid 및 card

BM25가 놓치는 표현 변형만 BGE로 보완한다. 이후 source-backed card를 추가해
“무엇을 확인해야 하는가”를 명시하되, LLM에게 card만 주지 않는다.

### Phase D — 선택적 Gemma rerank/second pass

BM25와 BGE가 강하게 불일치하거나, high-impact item의 조건이 충돌할 때만
Gemma에게 작은 후보 집합의 적용성을 재정렬하게 한다. 1,900여 test 공고와
2시간 제한 때문에 24 item별 추가 호출은 기본 경로가 될 수 없다.

---

## 8. 다음 실험의 측정 계획

1. **Retrieval quality:** dev gold와 무관하게, item table에서 기대한 source chunk가
   top-k에 들어오는 비율과 source hash/provenance 완전성.
2. **Prompt feasibility:** notice별 selected chunk 수, final token count, overflow 수,
   pass 수, fixed-context overflow 수.
3. **Judgment:** 24개 positive-class precision/recall/F1 및 macro F1.
4. **Evidence:** 공고 원문 substring validity와 span F1. 법령 인용이 evidence에
   섞이지 않았는지 별도 검증.
5. **Ablation:** full no-RAG → BM25-only → hybrid → hybrid+card 순으로 같은
   고정 cohort에서 비교하고, 유망한 것만 200 dev로 확대한다.

앞 20개는 비용을 아끼는 prompt mechanics smoke cohort로는 쓸 수 있지만 v1
positive가 하나뿐이다. item 효과를 주장하려면 해당 item positive/negative가
충분히 들어간 stratified dev subset을 별도로 고정해야 한다.

## 9. 제출 전 불변 조건

- retrieval corpus와 index는 대회 제공 법령·고시에서만 만든다.
- 사용 가능한 embedding model은 `BAAI/bge-m3`뿐이다.
- 모든 공고는 실제 공고 내용을 포함한 Gemma 호출을 적어도 한 번 받아야 한다.
- notice와 reference를 합친 **최종** chat template을 제출 runner tokenizer로
  계수한다.
- selected reference는 모든 notice split pass에 동일하게 포함한다.
- 출력 evidence는 언제나 공고/첨부문서 원문 substring이며, 법령·card·metadata는
  evidence가 아니다.
- model, prompt, chunk/index version, source hash, retrieval result, token/pass
  statistics를 output에 남긴다.
