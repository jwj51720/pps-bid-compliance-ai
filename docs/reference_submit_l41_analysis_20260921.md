# 0.7+ 참고 제출물 L41 정적 분석 및 로컬 재현 기록

작성일: 2026-09-21
대상: `dist/reference/submit.zip`
분석 범위: 압축 안전성, 실행 경로, 입력 축약, 항목별 최종 판정 소유권, 병합, evidence,
vLLM/runtime, 로컬 mock 재현, 현재 프로젝트와의 구조 차이

## 1. 결론

이 제출물의 핵심은 좋은 all-24 프롬프트 하나가 아니다. 실제 구조는 다음의 hybrid다.

1. Python이 공고 원문과 meta에서 결정론적 사실과 의미 구역 후보를 만든다.
2. BGE-M3가 경쟁제품 CSV 후보를 검색한다.
3. Python 규칙이 24개 중 다수 항목의 최종 라벨을 직접 결정한다.
4. Gemma는 잔여 10항목용 expert, v19 전용 expert, v24 전용 expert로 정확히 3회 호출된다.
5. 각 항목은 고정된 last-writer가 소유하며 범용 OR merge나 투표를 하지 않는다.
6. 16,384-token context와 1,536-token completion 안에서 모든 요청을 사전 검증하고,
   원문 전체가 아니라 약 14,000자의 목적별 source pool을 사용한다.

따라서 현재 프로젝트와의 가장 큰 차이는 프롬프트 문구가 아니라 **문제 분해와 판정
소유권**이다. 현재 프로젝트는 입력 완결성을 위해 모든 원문·카드·metadata를 큰 Gemma
판정에 맡겼고, 참고물은 관측·후보화·결정론 판정·잔여 의미 판정을 분리했다.

다만 이 코드를 정답 구현으로 간주해 그대로 복사하면 안 된다. v4 예외 출력이 최종 계산에서
무시되는 회귀, arm 단위 fail-closed가 대량 false negative를 만들 수 있는 failure policy,
키워드와 dev 실험에 강하게 결합된 규칙, source candidate recall 미보장 등 잠복 결함도 있다.
사용자가 알려준 0.7+ 성적은 중요한 외부 관측이지만, 이 ZIP만으로 점수와 실행시간을 독립
재현하지는 못했다.

## 2. 압축물 무결성과 안전한 추출

| 항목 | 확인값 |
| --- | --- |
| 원본 | `dist/reference/submit.zip` |
| ZIP 크기 | 138,129 bytes |
| ZIP SHA-256 | `a06feff77ffbc4a6f2a47cd0e2d322f341f652ca865d1b9cf53919012c8ca216` |
| 엔트리 | `script.py` 한 개 |
| 압축 전/후 | 906,714 / 138,013 bytes |
| 경로 안전성 | 상대경로, `..` 없음, absolute path 아님, symlink 아님 |
| 추출 위치 | `dist/reference/submit_extracted_a06feff7/script.py` |
| 추출 파일 SHA-256 | `e30579a31b4a1f957b0252cebde705dff11bd4b372982087d27ffa69cf1ccea7` |
| 소스 크기 | 11,986 lines, 906,714 bytes |
| 문법 검사 | `python -m py_compile` PASS |

ZIP을 실행하거나 현재 소스 트리에 덮어쓰지 않고 격리 디렉터리에 추출했다. `script.py`는
`_EMBEDDED_SOURCES`에 44개 Python 모듈을 문자열로 동결하고 custom import finder로 로드하는
standalone bundle이다. 실제 최종 entrypoint가 import하는 경로만 분석했다.

## 3. 실제 실행 흐름

```text
test.jsonl.gz
  │
  ├─ FactBuilder ─────────────── F1..F6 구조화 사실
  │                              계약/meta, 금액, 제품코드, 지역, 날짜, 완전관측
  │
  ├─ section_extractor ───────── S1..S11,SX 원문 후보
  │                              12개 의미 구역 중 r10은 10개를 선택, 전체 약 14,000자
  │
  ├─ BGE-M3 on CPU ───────────── 경쟁제품 CSV top-10
  │                              공고문의 조달대상 후보 query
  │
  ├─ Gemma arm r10 ───────────── 잔여 10항목의 원자 사실/판정
  ├─ Gemma arm B ─────────────── v19 whole-proposition 전용
  └─ Gemma arm C24 ───────────── v24 네 축 대조 전용
           │
           ▼
  deterministic solver
           │
           ├─ 다수 v를 Python rule로 기록
           ├─ B가 v19를 last-write
           └─ C24가 v24를 last-write
           ▼
  evidence 정리 → 49열 CSV 검증 → atomic write
```

Gemma expert들은 서로의 결과를 읽지 않는다. 전체 조립 순서는 정확히
`r10 decode → deterministic solver → B/v19 → C24/v24`다.

## 4. 입력은 어떻게 만들어지는가

### 4.1 F: 결정론적 사실

`FactBuilder`는 같은 공고에서 다음 사실을 만든다.

| fact | 내용 | 중요한 제한 |
| --- | --- | --- |
| F1 | 적용계약법, 업무·기관·계약·낙찰·입찰·조달 방식, 공동도급, 정보화 여부 | exact 문자열 flag는 법률판정이 아니라고 표시 |
| F2 | 예산, 추정가격, 차이·비율, 금액 band | 1억/2.3억 경계를 내장 |
| F3 | meta 세부품명코드, 제공 CSV exact match, 문서 내 10자리 코드 후보 | 코드 없음은 일반제품이 아니라고 명시 |
| F4 | meta 지역제한과 익명화 지역토큰 | 주소·납품지일 수 있어 자동 제한 해석 금지 |
| F5 | 공고일, 개찰일, 날짜 차이, 긴급 여부 | 개찰일을 제안마감일로 쓰지 않음 |
| F6 | 문서 수·유형·길이, input completeness, dropped docs, meta missing state | 불완전관측을 특정 라벨로 변환하지 않음 |

이 층은 우리 프로젝트의 human-readable metadata renderer보다 강하다. 단순 표시가 아니라
산술, exact-code join, 상태 구분, meta-document 관계까지 명시적으로 구조화한다.

### 4.2 S: 목적별 원문 후보

`section_extractor`는 전 문서를 다음 의미 구역으로 검색한다.

| section | 의미 |
| --- | --- |
| S1 | 입찰 개요 |
| S2 | 입찰 참가자격 |
| S3 | 참가자격상 실적 제한 |
| S4 | 평가상 실적·배점·제출양식 |
| S5 | 지역 제한 |
| S6 | 품목·기업 규모 제한 |
| S7 | 규격·공급·제조사 조건 |
| S8 | 소프트웨어 사업 조건 |
| S9 | 공동수급 |
| S10 | 설명회·제안서 일정 |
| S11 | 공고문-meta 대조 후보 |
| SX | 법령상 예외 사유 후보 |

후보는 `doc_id`, 문서유형, 원문 offset, heading, 역할, 탐지어, 변경 없는 원문을 보존한다.
중복 span을 합치고 section별 character quota에 따라 선택한다. r10 source pool의 총 예산은
14,000자다.

이는 EXP171의 7개 자유형 navigation과 다르다. Gemma가 1차 발췌를 생성하지 않고 Python이
원문 위치를 결정론적으로 후보화한다. 따라서 추가 LLM pass가 없고 substring provenance가
처음부터 유지된다. 반면 extractor가 모르는 표현은 빠지며, quota 끝에서 후보 text가 잘릴 수
있다. **전 문서를 스캔한다는 것과 모든 판정 사실이 최종 prompt에 보존된다는 것은 다르다.**

### 4.3 BGE 제품 검색

BGE-M3는 공고문의 구매·용역 대상처럼 보이는 행을 최대 1,600자로 query화하고 제공 경쟁제품
CSV 전체를 dense search해 top-10을 만든다. CPU, batch 24, max length 256이다. 최종 코드의
BGE 결과는 Gemma prompt에 직접 들어가지 않고 v10/v14 등 Python product gate에서 쓰인다.

일반적인 catalog semantic matching이 아니다. v10 bridge는 score `>=0.49`에 더해 행사·축제·
박람회 또는 시스템 유지관리라는 특정 query와 코드군을 요구한다. 이 부분은 좁고 강한
competition-specific rule이다.

## 5. 항목별 최종 판정 소유권

아래 표의 `Python`은 transport나 evidence 검증이 아니라 최종 v를 실제로 계산한다는 뜻이다.

| item | 최종 소유자 | 실제 계산 요약 |
| --- | --- | --- |
| v1 | Python | 공고문 같은 행의 기관 한정, 선보유 능력, 제조사등록 표현 |
| v2 | Python | 공고문 참가효과 표현, 지방 소액수의 예외 |
| v3 | hybrid | r10이 참가자격 실적 여부 `q`와 배수/규모초과 `x` 추출; Python이 `q∧x`와 source-role gate |
| v4 | hybrid | r10이 참가자격 `q`, 특정 실적 `r`, 예외 `e` 추출; 최종은 현재 `q∧r` |
| v5 | Python | 공사 제외, 계약법별 금액 cap, strict 지역 참가제한 |
| v6 | Python | 고시금액 미만 기초단위 소재지 제한, 지방 소액수의 예외 |
| v7 | Python | 고시금액 미만 복수 광역지역 제한, 지방 소액수의 예외 |
| v8 | Python | 공고문 실적 gate와 지역 gate 교집합, 공사/지방 소액수의 예외 |
| v9 | r10 Gemma | 신규 조달품 특정 제조사·브랜드·모델 강제 및 동등품/호환·안전 예외 판단 |
| v10 | Python | 경쟁제품 BGE/exact bridge, 직접생산 요구 부재, 명시 예외 |
| v11 | Python | 완전관측 + 경쟁제품 + 중소기업 범위 부재 + 예외 부재 |
| v12 | Python | 직접생산 참가요건과 비경쟁 meta code 또는 catalog 특이사항 금액 불적용 |
| v13 | Python | 공고문 exact 제품코드 + 소기업·소상공인 hard gate + 수의/특례 예외 |
| v14 | Python | 금액, 비공사, 기업범위, hybrid 제품판별, 명시 예외 |
| v15 | hybrid | Python이 1억 이상 2.3억 미만을 gate하고 r10 판단을 결합 |
| v16 | Python | 완전관측, 일반제품, 금액 band, 기업범위/예외 부재 |
| v17 | Python | 1억 미만 일반제품, 중소기업만 허용하고 소기업 한정은 아님 |
| v18 | Python | 완전관측, 1억 미만 일반제품, 기업범위 요구 부재 |
| v19 | B Gemma last-writer | 외부사 이행보장 서류의 낙찰 전 의무라는 whole proposition |
| v20 | Python | SW 적용 신호와 대기업 참여제한 exact phrase 부재. r10의 raw `y`는 최종 계산에 쓰지 않음 |
| v21 | hybrid | r10 판단 후 분담이행 veto, 국가 공동이행 5% 명시 force-positive |
| v22 | hybrid | r10 판단, 특정 mandatory phrase force-positive, 발표평가 문맥 veto |
| v23 | hybrid | r10이 설명회 역할·설명일·실제 제안마감일 추출; Python이 계약법/협상/기간 계산 |
| v24 | C24 Gemma last-writer | 금액·계약방법·참가업체 지역·필수 업종 네 축의 same-field 명백 불일치 |

순수하게 넓은 법률판정을 Gemma에 전담하는 항목은 생각보다 적다. v3/v4/v15/v21/v22/v23도
Gemma 출력 뒤 구조화된 Python gate가 적용된다. 이는 현재 프로젝트의 “Python은 label을
판정하지 않는다” 원칙과 정면으로 다르다.

## 6. 세 Gemma expert

### 6.1 r10

- 소유 출력: `v3,v4,v9,v15,v19,v20,v21,v22,v23,v24`
- 입력: compact F + 14,000자 목적별 S pool + 해당 10개 카드
- 실제 최종 보존: v3, v4, v9, v15, v21, v22, v23 중심
- v19는 B가, v24는 C24가 나중에 교체한다.
- v20은 `solve()`가 parsed model y를 버리고 Python exact presence로 다시 계산한다.
- malformed, non-stop, schema 오류면 10개 모두 0 fallback이다.

v3/v4는 바로 0/1을 묻지 않고 원자 상태를 Y/N/U로 분해한다. v23도 날짜 역할을 먼저
추출하고 Python이 날짜 계산을 한다. 이는 우리가 탐색했던 관계형 사실 구조화를 실제 최종
판정과 결합한 형태다.

### 6.2 B: v19 whole-proposition

v19를 단순히 “확약서가 있는가”로 묻지 않는다. 한 대표 요구 전체를 다음 중 하나로 해석한다.
낙찰 전 외부사 보장, 낙찰 후, 선택사항, 입찰자 자신의 약속, 자격·속성 증빙, 기타, 요구 없음,
불명확. 이 중 첫 번째이면서 model y=1이고 유효 source ID가 있을 때만 양성이다.

발급자·내용·시점을 서로 다른 문장에서 무리하게 합성하는 오류를 막는 좋은 설계다. 양성에는
유일하게 원문에 mapping되는 source가 반드시 필요하며, B가 최종 v19/e19를 덮어쓴다.

### 6.3 C24

v24를 법률 위반 일반문제가 아닌 네 필드 대조 문제로 제한한다.

1. VAT 역할을 구분한 금액
2. 계약방법과 낙찰방법의 구분
3. 참가업체 소재지와 현장·납품지의 구분
4. 필수 업종과 과업 분야·인력자격의 구분

양쪽에 같은 의미·범위·시점의 확정값이 있을 때만 비교하며 null이나 원문 미발견은
불일치가 아니다. 이는 현재 카드보다 훨씬 구체적인 비교 프로토콜이다.

## 7. 병합과 evidence

이 구조에는 문서별 OR merge가 없다. 각 항목의 final owner와 last-writer가 고정되어 있다.
따라서 서로 다른 pass의 모순을 일반 OR로 덮지 않는다.

- 결정론 양성은 찾은 원문 window를 `clean_evidence`로 exact substring화한다.
- r10은 source ID에서 evidence를 선택한다.
- v19는 양성 source가 없으면 결과 자체가 실패한다.
- C24는 evidence가 원문에 없으면 evidence만 비우고 v24 label은 유지한다.
- 최종 `clean_rows`도 evidence가 무효면 evidence만 제거하고 label을 바꾸지 않는다.
- absence evidence는 항상 빈 문자열이다.

우리의 과거 strict evidence gate처럼 evidence 실패가 positive label을 0으로 강등하지 않는다.
V 점수와 E 품질을 분리한다는 점은 합리적이지만, positive-without-evidence가 최종 정성평가에
남을 수 있다.

## 8. runtime 구현

| 설정 | 값 |
| --- | --- |
| calls per record | 정확히 3 |
| test 1,853건 예상 logical requests | 5,559 |
| batch chunk | 128 |
| context | 16,384 |
| prompt budget | 14,848 |
| completion | 최대 1,536 |
| temperature / n | 0 / 1 |
| seed | 20260826 |
| thinking | disabled |
| quantization | `int8_per_channel_weight_only` |
| GPU memory utilization | 0.92 |
| prefix caching | enabled |
| retry | 없음 |

`apply_chat_template(... enable_thinking=False, truncation=False)`로 만든 token ID를 그대로
`llm.generate`에 넘기며 backend가 받은 prompt token ID와 순서를 다시 비교한다. structured
JSON decoding은 whitespace까지 제한한다. 세 arm의 모든 prompt가 14,848 token 이하인지
한 건도 호출하기 전에 preflight한다.

batch 128은 logical request 5,559개를 없애지 않지만, 같은 system prefix를 가진 arm별 전체
batching, 16k 고정 context, 짧은 completion, prefix caching, no retry가 throughput에 유리하다.
EXP171/231의 긴 full-source pack과 다단계 호출보다 runtime 설계가 훨씬 명시적이다.

환경변수 `PPS_DATA_DIR`, `PPS_OUTPUT_DIR`, `PPS_MODEL_DIR`, `PPS_EMBED_DIR`를 모두 요구하고,
server mode에서는 임의 input/limit/output override를 금지한다. Hugging Face offline 환경을
강제하고 BGE는 CPU에서 먼저 실행한 뒤 해제한다. CSV는 atomic write하며 입력 ID 순서를
검증한다.

## 9. 로컬 재현 결과

실행 명령:

```bash
.venv/bin/python dist/reference/submit_extracted_a06feff7/script.py \
  --mock \
  --data-dir data/raw/open/data \
  --output-dir outputs/reference-submit-l41-mock-20260921 \
  --limit 10
```

결과:

- 10개 sample record 준비 성공
- organizer 항목표와 경쟁제품 CSV 경로 해석 성공
- r10/B/C24 각각 10개 응답 조립 성공
- `submission.csv`: 10행 × 49열
- ID unique, v1-v24 binary, 정해진 column order PASS
- runtime report status PASS
- mock 총시간 약 0.785초
- 실제 Gemma 호출 0, BGE는 empty mock, server runtime 검증 아님

산출물:

- `outputs/reference-submit-l41-mock-20260921/submission.csv`
- `outputs/reference-submit-l41-mock-20260921/l41_runtime_report.json`

이 환경에는 공식 evaluator와 동일한 L40S/vLLM model runtime이 확인되지 않았으므로 실제
inference, 정확 tokenizer preflight, 1,853건 2시간 통과는 주장하지 않는다. mock 결과는
패키지의 data dependency, 조립, schema, CSV 계약만 입증한다.

## 10. 현재 프로젝트와의 구조 차이

| 축 | 현재 EXP171/EXP231 계열 | 참고 L41 |
| --- | --- | --- |
| 중심 가설 | 완결 입력과 full source를 Gemma가 재독해 전 항목 판정 | 다수 항목은 결정론 solver, 의미 잔여만 Gemma |
| source 입력 | exact-token admitted full documents | 전 문서에서 Python이 만든 11개 semantic section pool |
| 1차 navigation | Gemma source-only pass | deterministic span extraction |
| 법률 조건 | versioned decision card 중심 | item card + hard-coded predicates/thresholds/exception terms |
| 제품 | exact-code friendly fact를 Gemma가 적용 | exact scan + BGE top-10 + lexical/code/amount Python gate |
| all-24 attention | 한 final prompt에 집중 | r10 10개 + v19 + v24로 제한 |
| merge | source pack OR, absence AND, specialist replacement | single final owner와 고정 last-writer |
| evidence 영향 | 일부 strict gate에서 label 강등 가능 | 대체로 label 유지, evidence만 제거 |
| failure | staged/parse recovery와 많은 호출 | no retry, arm별 0 fallback |
| call topology | EXP171 dev200 435, EXP231 선언 619 | 정확히 3/record |
| local/submission 동형성 | specialist 무시 결함이 있었음 | 하나의 frozen standalone path |

우리가 놓친 가장 중요한 설정은 “정보를 더 많이 넣는 법” 하나가 아니다.

> 각 v의 진리조건을 원자 관측으로 분해하고, 값비싼 의미판단이 필요한 부분만 Gemma에게
> 맡기며, final writer를 하나로 고정하는 문제 구조화가 부족했다.

## 11. 참고 코드에서 확인된 결함과 일반화 위험

### 11.1 확정 코드 결함 또는 불일치

1. **v4 예외 슬롯 무시**: r10 v4 schema는 `q,r,e`를 요구한다. v4 버전의 solver는
   `q∧r∧¬e`였지만 최종 v5 solver는 `q∧r`만 사용한다. 모델이 예외를 Y로 찾아도 양성이 된다.
2. **arm failure의 비대칭 은폐**: r10 오류는 잔여 10개 0, B 오류는 v19=0, C24 오류는
   v24=0이다. `normal_coverage`는 세 arm 중 하나만 정상이어도 record를 통과시킨다.
3. **evidence 정책 불균일**: v19는 양성 evidence가 없으면 0 fallback인 반면 C24/r10의 일부는
   양성 label을 유지하고 evidence만 비운다.
4. **후보 text character 절단**: source pool quota가 token이나 문장 경계가 아닌 character
   slice로 후보를 자를 수 있다.
5. **bundle 비대화**: 최종 경로가 쓰지 않는 dev 평가·실험 모듈도 44개 bundle에 포함된다.
   실행 자체에는 문제가 없지만 검증 표면과 provenance를 불필요하게 키운다.

### 11.2 일반화 위험

1. **첨부문서 blind spot**: v1/v2/v5/v6/v7/v8 계열의 핵심 iterator와 v12/v13의 여러 hard
   gate는 `type == "공고문"`만 검사한다. 공식 문제에서는 첨부문서가 위반 근거일 수 있으므로,
   r10 section pool이 전 문서를 읽더라도 Python이 최종 소유한 항목은 첨부-only 위반을 복구하지
   못할 수 있다.
2. 많은 classifier가 구체 문자열, 같은 행/최대 3~4행 window, 익명화 token, 특정 금액,
   특정 조문 표현에 의존한다.
3. BGE v10 bridge가 행사/시스템 코드군과 `0.49` threshold에 특화되어 있다.
4. 경쟁제품 `특이사항` 금액 해석은 확인된 일부 문구만 처리한다.
5. 완전관측 flag가 false면 여러 absence positive를 보수적으로 0으로 만든다. public의 upstream
   누락 분포가 다르면 recall이 바뀐다.
6. 의미 section extractor recall을 측정하는 독립 gold가 없다. 못 찾은 사실은 Gemma가 볼 수 없다.
7. 파일명과 주석이 다수 dev experiment의 채택 결과임을 보여준다. dev-label leakage가 최종
   실행에 직접 들어간 증거는 없지만 rule selection overfit 위험은 크다.
8. hard rule이 틀렸을 때 Gemma가 복구할 경로가 없다. 다수 항목은 LLM 결과보다 Python이
   최종 권한을 가진다.

## 12. 받아들일 것과 받아들이지 않을 것

### 받아들일 구조 원리

- immutable source span과 provenance
- deterministic fact layer와 decision layer의 분리
- 항목별 truth-condition decomposition
- single final owner / explicit last-writer
- v19처럼 전체 명제를 한 번에 해석하는 specialist
- v24처럼 비교 가능한 필드쌍을 먼저 정의하는 protocol
- exact tokenizer preflight와 tokens-in vLLM parity
- fixed call topology, no hidden retry, runtime report
- V 판정과 evidence 유효성의 명시적 분리

### 그대로 복사하지 않을 것

- dev에서 고른 문자열 rule과 threshold
- 44개 연구 모듈을 그대로 submission에 동결하는 방식
- source section recall을 측정하지 않은 채 full source를 완전히 버리는 정책
- 실패한 expert를 조용히 0으로 만드는 정책
- v4 같은 schema-to-solver semantic drift
- item별 owner를 테스트 없이 순서 의존 overwrite로 구현하는 방식

## 13. 다음 재현 단계

이 문서 단계에서는 실제 전략을 이식하지 않는다. 새 architecture가 준비되면 다음 순서로
참고물을 독립 재현한다.

1. L41 frozen artifact의 exact tokenizer-only preflight를 공식 tokenizer로 실행한다.
2. 가능하면 동일 GPU에서 sample/소형 dev runtime과 malformed/fallback rate를 측정한다.
3. 현 dev-200에 실행해 제공된 0.7+ claim과 분리된 local metric을 얻는다.
4. final ownership table과 실제 row 변화가 일치하는지 trace한다.
5. deterministic-only, r10, B, C24 기여를 one-change ablation으로 분해한다.
6. reference rule을 복사하기 전 organizer source와 label-blind truth contract를 다시 작성한다.

현재 확실한 결론은 하나다. 0.7+ 후보가 보여주는 방향은 “Gemma에게 더 많이 읽혀라”보다
“각 항목을 관측·관계·판정으로 분해하고 최종 책임을 명확히 하라”에 가깝다.
