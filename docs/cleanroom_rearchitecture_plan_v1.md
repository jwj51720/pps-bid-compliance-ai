# PPS 판정 파이프라인 clean-room 재설계 계획 v1

작성일: 2026-09-21
상태: 설계안. 아직 기존 `src/` 이동이나 신규 구현을 시작하지 않음.

## 1. 목적

현재 저장소의 문제는 결함 몇 개가 아니다. 장기간의 실험이 하나의 pipeline/config 경로에
누적되면서 다음 질문에 즉시 답할 수 없게 되었다.

- 이 v의 최종 라벨은 정확히 어떤 모듈이 결정했는가?
- 그 모듈이 본 organizer source와 exact span은 무엇인가?
- Python rule, Gemma, merge 중 어느 단계가 raw 판단을 바꿨는가?
- local dev와 submission이 정말 같은 실행 그래프인가?
- config 한 줄의 변경이 prompt, token admission, calls, label ownership 중 무엇을 바꾸는가?
- 실패한 과거 전략이 현재 경로에 숨어 재사용되고 있지 않은가?

재설계의 목표는 단순한 코드 정리가 아니다. **24개 법률 판정 실험을 독립 교체 가능하게
만들면서도, 각 실험의 입력·판정·병합·runtime을 증명 가능한 상태로 만드는 것**이다.

## 2. 현재 구조에서 확인된 결함 계열

### 2.1 입력과 정책의 상태 불일치

- 최신 source-concordant card와 root/submission이 선택한 card가 달랐다.
- 검증된 v30/v31 입력 완결성을 과거 EXP231 policy에 전용할 수 없었다.
- config에 선언된 specialist가 local runner에서 실행되지 않았고 submission에서만 실행됐다.
- admission profiler는 specialist 400 calls를 누락해 619 calls를 219로 보고했다.
- `staged_run.mode: off`가 loader에서 실제 stage처럼 해석됐다.

### 2.2 거대한 공통 pipeline의 semantic coupling

- prompt mode, grouping, staged pass, evidence gate, merge, specialist가 같은 class의 분기에
  축적되었다.
- 한 카드 문구의 변화가 무관한 v의 attention과 출력까지 바꿨다.
- V/E, V-only, draft/verify가 serialization 변경인지 semantic 변경인지 구분하기 어려웠다.
- raw model V와 final V 사이의 writer chain을 record/item 단위로 설명하기 어려웠다.

### 2.3 병합의 과도한 일반화

- non-absence OR와 absence AND가 기본값이 되었지만 v별 truth condition과 맞는지 항상
  증명되지 않았다.
- 문서 간 관계가 필요한 항목과 한 문서 span으로 충분한 항목이 같은 reducer를 공유했다.
- specialist replacement와 source-pack merge가 실행 순서에 의존했다.

### 2.4 품질과 runtime의 분리 실패

- EXP171 435 calls, EXP231 619 calls가 120분을 초과했다.
- batch 크기를 logical call 감소로 오해할 여지가 있었다.
- local OpenRouter wall time과 evaluator vLLM time을 비교 근거로 쓸 수 없었다.
- prompt의 평균 token만 보고 tail, completion budget, arm별 prefix reuse를 충분히 보지 못했다.

### 2.5 실험 재현성 오염

- 실험 config, root canonical, submission runtime config가 서로 다른 truth를 가졌다.
- 많은 역사적 모드가 active code에 남아 선택 가능했다.
- 일부 audit가 exact tokenizer context가 아니라 무제한 rendered message를 검사했다.
- 결과 artifact가 config hash, asset hash, exact task hash, writer trace를 하나의 manifest로
  묶지 않았다.

### 2.6 정책상 자기제약

대회 규칙은 deterministic rule/correction을 허용한다. 그런데 프로젝트는 경험적으로
“Python은 label 판단을 하지 않는다”를 canonical 원칙으로 굳혔다. 0.7+ 참고 L41은 반대로
다수 항목을 deterministic solver로 처리하고 Gemma를 잔여 의미판정에 집중시킨다.

앞으로 Python 판단을 무조건 허용하거나 무조건 금지하지 않는다. **관측 extractor,
deterministic decision, LLM decision을 서로 다른 module type으로 선언하고 동일한 평가 gate로
비교**한다. 어떤 module도 숨은 후처리로 들어갈 수 없다.

## 3. clean-room 경계

향후 구현 시 기존 코드를 `src/legacy` 안에 두지 않는다. 같은 import root 아래에 두면 새 코드가
우연히 legacy helper를 import하고도 clean-room이라고 착각할 수 있다.

계획된 경계는 다음과 같다.

```text
legacy/
  pipeline_v1_20260921/       # 현재 src/scripts 중 보존 대상, read-only archive
  README.md                   # provenance, 마지막 commit, 실행 금지 이유

src/
  pps_ai/                     # 새 코드의 유일한 import root
    domain/
    ingest/
    facts/
    views/
    decisions/
    assembly/
    evidence/
    runtime/
    artifacts/

experiments/
  manifests/                  # 실행 가능한 immutable experiment manifests

submission/
  script.py                   # pps_ai runtime adapter만 호출
```

실제 이동은 별도 migration commit에서 한다. 이동 전에 현재 worktree의 사용자 변경을 보존하고,
tracked/untracked 파일 목록과 content hash manifest를 만든다. Git history가 없는 ignored output과
data는 이동하지 않는다.

## 4. 핵심 domain model

### 4.1 불변 입력

한 공고를 다음으로 정의한다.

```text
NoticeRecord R = (
  id,
  ordered_documents,
  metadata,
  input_completeness,
  dropped_document_counts
)
```

모든 원문 관측은 자유 문자열이 아니라 `SourceSpan`을 사용한다.

```text
SourceSpan = (
  notice_id,
  document_id,
  document_type,
  document_order,
  start,
  end,
  exact_text,
  document_sha256
)
```

불변식:

- `exact_text == document.text[start:end]`
- span은 한 문서를 넘지 않는다.
- normalization된 파생 문자열을 evidence로 쓰지 않는다.
- 원문 순서와 organizer가 제공한 type을 보존한다.
- semantic type 추정은 별도 observation이며 원본 type을 덮어쓰지 않는다.

### 4.2 관측, 판정, 출력의 타입 분리

```text
Observation    = source/meta에서 얻은 사실. label을 포함할 수 없음.
Judgment       = 한 v에 대한 0/1/U와 판정 provenance.
Evidence       = Judgment를 뒷받침하는 SourceSpan 또는 absence marker.
FinalCell      = 최종 0/1, evidence text, owner, writer trace.
```

`Observation` schema에 `v`, `violation`, `label`, `positive` 같은 필드를 금지한다. 반대로
`DecisionModule`만 Judgment를 만들 수 있다. 이 타입 경계로 “사실 추출처럼 보이는 Python
override”와 “prompt helper가 사실상 판정하는 경우”를 드러낸다.

## 5. 계층형 실행 DAG

```text
L0 ingest/normalize
  ↓
L1 source ledger
  ↓
L2 factual observations ─────────────┐
  ↓                                  │
L3 bounded source views/retrieval ───┤
  ↓                                  │
L4 decision modules (rule or LLM) ◄──┘
  ↓
L5 ownership-aware assembly
  ↓
L6 evidence resolution
  ↓
L7 validation/export

L8 runtime scheduler는 L3/L4를 실행하지만 의미를 바꾸지 않는다.
L9 artifact ledger는 모든 층의 hash와 trace를 기록한다.
```

### L0. ingest/normalize

- JSONL schema, unique ID, document order, field types를 검증한다.
- Unicode NFC/NFD 파일명 차이는 path resolver에서만 처리한다.
- 원문 text 자체를 정규화하지 않는다.
- upstream missing과 pipeline omission을 별도 상태로 둔다.

### L1. source ledger

- 각 document의 byte/character hash와 ordered identity를 생성한다.
- 모든 downstream span을 역검증한다.
- record별 제공 문서 수와 type coverage를 manifest에 남긴다.

### L2. factual observations

교체 가능한 pure module이다.

```python
class FactExtractor(Protocol):
    module_id: str
    schema_version: str

    def extract(self, record: NoticeRecord, assets: AssetView) -> FactPacket: ...
```

초기 module 후보:

- `meta_exact_v1`: 값과 missing state만 보존
- `amount_arithmetic_v1`: 예산/추정가격/비율. 법률 threshold 적용은 하지 않음
- `product_exact_code_v1`: organizer CSV exact join과 특이사항 원문
- `region_token_v1`: 익명화 지역 token 관측
- `date_role_candidate_v1`: 날짜 문자열과 문서 역할 후보
- `input_completeness_v1`: upstream availability

각 fact는 source kind, field path 또는 SourceSpan, extractor version을 가진다.

### L3. bounded source views/retrieval

full source, semantic section, exact-code retrieval, BGE catalog 등은 모두 `SourceViewBuilder`의
서로 다른 구현이다. view는 판정하지 않는다.

```python
class SourceViewBuilder(Protocol):
    def build(self, record, facts, budget) -> SourceView: ...
```

`SourceView`는 다음 coverage를 의무 기록한다.

- inspected documents
- selected spans
- omitted spans와 이유
- token count
- selection rule/version
- truth-contract required roles의 covered/missing 상태

full source도 하나의 view다. “전체를 넣었다”가 아니라 tokenizer admission 이후 실제
context별 coverage를 기록한다.

### L4. decision modules

세 종류를 동일 인터페이스로 지원한다.

1. `DeterministicDecision`: 명시 predicate로 최종 Judgment 생성
2. `LLMDecision`: prompt와 schema로 최종 Judgment 생성
3. `HybridDecision`: LLM이 원자 상태를 추출하고 결정론 reducer가 명시된 식으로 결합

```python
class DecisionModule(Protocol):
    module_id: str
    owned_items: tuple[str, ...]
    required_facts: tuple[str, ...]
    required_source_roles: tuple[str, ...]
    failure_policy: str

    def decide(self, packet: DecisionInput) -> DecisionBatch: ...
```

deterministic rule도 organizer-source specification, 적용 전제, positive predicate, negative/
exception predicate, evidence rule, unknown 처리, 금액 경계를 갖는 versioned contract를 먼저
작성해야 한다. dev 오답에서 직접 만든 문자열은 provenance 없이 active module이 될 수 없다.

### L5. ownership-aware assembly

모든 experiment manifest는 24개 v 각각에 정확히 한 final owner를 정한다.

```text
owner(v_i) = exactly one DecisionModule
```

overlap은 기본적으로 config error다. 교체 실험만 명시적 `replacement` edge를 허용하며,
base owner와 replacement owner를 manifest에 함께 적는다. 실행 순서에 의한 암묵적 overwrite,
dict update, 전역 OR는 금지한다.

여러 source context가 하나의 owner에 들어갈 때 reducer를 item contract에 선언한다.

- `ANY_WITNESS`: 한 유효 양성 span이면 1
- `ALL_OBSERVED_ABSENT`: 완전관측된 모든 scope에서 필수 사실 부재
- `RELATION_JOIN`: 명명된 두 observation의 관계식
- `SINGLE_JUDGMENT`: 한 module 결과 그대로
- `REPLACEMENT`: 실험적으로 명시한 last writer

OR/AND라는 구현 편의가 아니라 truth condition이 reducer를 결정해야 한다.

### L6. evidence resolution

V와 E의 관계를 item별로 선언한다.

- `required_for_positive`: evidence 없으면 Judgment invalid. 자동 0으로 바꾸지는 않고 failure 처리
- `optional_for_v`: V 유지, E blank 허용
- `absence`: E는 항상 blank
- `metadata_relation`: source evidence가 없을 수 있음을 명시

evidence invalid가 label override로 숨어들지 않게 `JudgmentValidity`와 label을 분리한다.

### L7. validation/export

- 49 ordered columns
- input ID 순서/완전성/unique
- binary V
- evidence exact substring, <=500, NFC, formula prefix 차단
- absence blank
- atomic write
- expected row count

### L8. runtime scheduler

scheduler는 batching, device, structured decoding만 담당한다. prompt나 label semantics를
변경할 수 없다.

필수 report:

- logical requests = `Σ records × contexts × active arms`
- physical batches by arm
- prompt/completion token sum/max/p95
- load/retrieval/inference/assembly time
- finish reason, malformed, fallback
- peak memory if observable
- retry count와 retry trigger

batch size를 call-count 감소로 보고하지 않는다.

### L9. artifact ledger

모든 실행은 하나의 immutable run manifest를 남긴다.

```text
run_id
git commit + dirty patch hash
experiment manifest SHA-256
input ID/order hash
asset content hashes
module IDs/schema versions
exact rendered-task hash
tokenizer/model generation settings
owner matrix hash
runtime report
prediction writer trace
metrics/per-item confusion
```

## 6. experiment manifest

YAML inheritance과 CLI 기억에 의존하지 않는다. 실행 전 fully resolved manifest를 JSON으로
고정하고 hash한다.

```yaml
experiment_id: exp_clean_001
base_manifest: baseline_organizer_v1
allowed_changes:
  - decisions.v19

assets:
  item_table: {path: ..., sha256: ...}
  product_catalog: {path: ..., sha256: ...}

facts:
  - meta_exact_v1
  - product_exact_code_v1

views:
  residual: semantic_sections_v1

decisions:
  v1: rule_v1_organization_v1
  v2: llm_all_item_control_v1
  # ... exactly v1-v24

runtime:
  model: gemma-4-26B-A4B-it
  max_model_len: 16384
  max_tokens: 1536
  temperature: 0
  seed: 20260826
  batch_size: 128
```

preflight는 base와 candidate의 resolved manifest를 비교해 `allowed_changes` 밖의 차이가 있으면
실행을 거부한다. path만 같은 asset은 같은 asset이 아니다. content hash가 같아야 한다.

## 7. 항목 truth contract

24개 item마다 문서가 아니라 machine-readable contract를 둔다.

```text
applicability facts
positive atomic conditions
negative/exception conditions
required document roles
required metadata/catalog facts
unknown semantics
multi-document relation
evidence policy
allowed owner types
organizer source provenance
```

contract에서 prompt card, deterministic predicate, evaluator test fixture를 생성하되, 생성 결과를
별도 versioned artifact로 고정한다. 사람 문장 카드와 Python rule이 서로 다른 진리조건을 구현하는
문제를 막기 위해 둘 다 같은 contract ID를 참조한다.

중요: 한 schema가 24개를 억지로 동일 형태로 만들 필요는 없다. 공통 envelope만 유지하고
item-specific atomic observations를 허용한다. v19 whole proposition, v23 timeline, v24 field-pair
comparison처럼 관계 유형이 다른 문제를 일반 `evidence[]` 하나로 평탄화하지 않는다.

## 8. 실험 모듈의 생명주기

각 module은 다음 상태 중 하나만 가진다.

```text
draft → audited → runnable → evaluated → accepted
                               └──────→ rejected
                      defect 발견 → invalidated
```

- `draft/audited`는 paid run 불가
- `rejected`는 재현 가능하지만 candidate manifest에서 선택 불가
- `invalidated`는 loader가 실행 거부
- `accepted`도 canonical manifest가 명시적으로 선택해야 활성화

모든 module directory에는 contract, implementation, unit tests, fixtures, result references,
status가 함께 있어야 한다. 단순히 함수가 repository에 존재한다는 이유로 선택할 수 없다.

## 9. 검증 체계

### 9.1 static/schema tests

- config/manifest full resolution
- exactly-one owner for 24 items
- no cyclic dependency
- Observation에 label field 없음
- DecisionModule만 Judgment 생성
- asset hash와 schema version 일치
- local/submission entrypoint가 같은 resolved manifest hash 사용

### 9.2 source/provenance tests

- 모든 span round-trip
- 문서 누락은 upstream/pipeline으로 구분
- exact-code join과 특이사항 보존
- source view required-role coverage
- truncated candidate가 evidence로 선택될 때 원문 offset 유효

### 9.3 semantic contract tests

각 v에 최소 다음 fixture를 둔다.

- clear positive
- clear negative
- 주요 exception
- missing/unknown
- attachment-only fact
- cross-document relation이 있다면 양 endpoint
- misleading keyword hard negative

card, deterministic module, LLM prompt가 같은 contract version을 참조하는지 검사한다.

### 9.4 writer/merge tests

- raw judgment부터 final cell까지 모든 writer trace
- unauthorized overwrite 즉시 실패
- reducer의 교환/결합 성질을 요구하는 경우 property test
- absence는 incomplete observation에서 positive로 확정되지 않음
- evidence invalid와 label mutation 분리

### 9.5 runtime/parity tests

- exact chat template/token IDs
- no hidden truncation/retemplating
- all tasks preflight before paid/model call
- logical calls와 physical batches 모두 보고
- mock staged ZIP를 실제 entrypoint로 실행
- local and submission task hashes equal
- failure injection: 한 arm malformed/length/exception일 때 명시 policy대로 종료

## 10. 실패 정책

참고 L41처럼 무조건 0 fallback을 쓰지 않는다. item contract가 다음 중 하나를 선택한다.

- `ABORT_RECORD`: 해당 record 결과를 만들지 않고 전체 run 실패
- `ABORT_RUN`: 어떤 partial submission도 쓰지 않음
- `FALLBACK_OWNER`: 사전에 선언된 별도 owner 사용
- `UNKNOWN_RETRY_ONCE`: runtime budget에 포함된 동일 semantics retry
- `ZERO`: organizer truth상 보수적 0이 정당한 항목에만 허용

failure policy는 metric과 runtime report에 나타나야 하며 Python exception handler 속에 숨지 않는다.
최종 제출은 정상 Gemma call requirement도 record별 trace로 확인한다.

## 11. local/submission 단일 경로

`submission/script.py`는 orchestration을 복제하지 않는다.

```python
manifest = load_frozen_manifest(PACKAGED_MANIFEST)
adapters = EvaluatorAdapters.from_pps_env()
run_pipeline(manifest, adapters)
```

local runner도 같은 `run_pipeline`을 호출하고 adapter만 OpenRouter/local-vLLM/mock으로 바꾼다.
specialist, retrieval, merge, evidence, validation은 adapter가 아니다. 따라서 local에서 빠지고
submission에만 존재할 수 없다.

packager는 다음을 검사한다.

- root candidate manifest와 packaged manifest hash 동일
- 모든 선택 module과 static asset 포함
- legacy import 0
- ignored data/model weight 포함 0
- staged unzip 후 exact entrypoint mock
- ZIP size/extracted size/install/inference projection

## 12. baseline과 참고물 재현 사다리

새 구조의 첫 목표는 새 아이디어가 아니라 세 기준선의 동형 재현이다.

1. **B0 official baseline**: organizer 제공 prompt/I/O를 가장 작은 pipeline으로 재현
2. **B1 current known local control**: 현재 best의 실제 semantics를 trace 가능한 형태로 동결
3. **B2 reference L41 frozen**: 참고 ZIP 자체를 변경 없이 local artifact로 평가
4. **B3 clean L41 reimplementation**: 같은 ownership과 input contract를 새 interface로 구현

B2와 B3의 per-record/per-item output, prompt/task hash가 같아야 clean reimplementation parity로
부른다. 그 뒤에만 rule, view, expert를 하나씩 교체한다.

## 13. 성능 연구 방향

### 13.1 우선 가설

1. all-24 full-source attention보다 item-specific truth decomposition이 강하다.
2. deterministic fact와 semantic judgment를 분리하면 Gemma가 담당할 범위를 줄일 수 있다.
3. v19/v24처럼 관계 전체를 보존한 specialist가 keyword/card 보정보다 일반화 가능성이 높다.
4. rule-dominant 항목은 organizer source로 완결된 predicate라면 LLM보다 안정적일 수 있다.
5. compact source view는 runtime을 줄이지만 recall audit가 있어야 full source를 대체할 수 있다.

### 13.2 실험 단위

한 실험은 다음 중 정확히 하나만 바꾼다.

- fact extractor
- source view
- 한 item 또는 진리조건을 공유한다고 입증된 작은 family의 decision owner
- reducer
- evidence policy
- runtime serialization/transport

prompt, source selection, schema, owner, reducer를 동시에 바꾸지 않는다.

### 13.3 평가 gate

```text
contract fixtures
  → rendered/task review
  → mock/failure injection
  → fast20 ranking
  → independent holdout20
  → dev200
  → exact vLLM runtime smoke
  → submission candidate
```

per-item TP/FP/FN뿐 아니라 observation recall, unknown rate, fallback rate, writer changes, evidence
validity, tokens, logical calls를 함께 본다. dev200 점수만 오른 rule은 public 일반화 근거가 아니다.

## 14. migration 단계

### Phase 0. 동결과 목록화

- 현재 dirty worktree를 사용자 변경과 agent 변경으로 구분
- tracked/untracked/ignored artifact inventory와 hashes 생성
- 현재 config들의 resolved semantics와 known invalidity 기록
- 기존 tests/outputs를 변경하지 않음

완료 조건: 어느 파일도 잃지 않고 legacy snapshot 범위가 확정됨.

### Phase 1. domain과 contract skeleton

- `NoticeRecord`, `SourceSpan`, `Observation`, `Judgment`, `FinalCell`
- manifest resolver와 owner matrix
- source ledger와 CSV validator
- model 호출 없는 unit tests

완료 조건: synthetic 24-item row가 unauthorized overwrite 없이 조립됨.

### Phase 2. official baseline parity

- organizer loader
- official prompt/schema
- mock/local adapter
- exact staged ZIP

완료 조건: official baseline과 입력/출력 contract가 동형이고 local/submission task hash가 같음.

### Phase 3. factual/view modules

- meta exact, amount, product exact code, completeness
- full-source view와 semantic-section experimental view
- provenance/coverage report

완료 조건: dev 200 supplied document omission 0, 모든 selected span round-trip, tokenizer report PASS.

### Phase 4. reference L41 parity

- frozen reference를 B2로 먼저 평가
- 새 구조에 item owner와 세 expert를 하나씩 이식
- 코드의 v4 예외 무시 등 발견 결함은 parity mode에서는 재현하되 `known_defect`로 표시
- corrected mode는 별도 experiment로만 실행

완료 조건: parity manifest와 corrected manifest가 섞이지 않고 output delta가 설명됨.

### Phase 5. 일반화 실험

- source-grounded deterministic predicates 재감사
- source view recall panel 구축
- atomic/hybrid expert 비교
- item family별 독립 교체

완료 조건: fast/holdout/dev200 및 runtime을 모두 통과한 module만 accepted.

### Phase 6. submission hardening

- active module만 standalone package
- exact tokenizer preflight
- official-like GPU smoke가 가능할 때만 runtime claim
- 1,853건 call/token/memory projection과 safety margin

## 15. 구현 전 승인해야 할 결정

다음은 문서 합의 없이 코드로 정하지 않는다.

1. legacy snapshot의 정확한 범위와 위치
2. 새 canonical baseline을 official B0로 할지 reference B3로 할지
3. deterministic decision을 적극 허용하되 어떤 provenance gate를 요구할지
4. failure 시 run abort와 item fallback의 기본 정책
5. full source view를 baseline으로 유지할지 semantic source view를 baseline으로 할지
6. 현재 dirty 변경 중 새 구조로 이식할 최소 목록

## 16. 완료 정의

재설계는 폴더가 예뻐졌을 때 끝나는 것이 아니다. 다음 질문에 기계적으로 답할 수 있어야 한다.

- 이 `submission.csv`의 v17은 어느 owner가 어떤 사실과 source span으로 결정했는가?
- 다른 owner가 값을 덮어썼는가?
- 실행한 local task와 ZIP task의 token ID가 같은가?
- 모든 supplied document가 어느 view에서 검사되거나 왜 제외됐는가?
- malformed expert 하나가 어느 항목을 어떻게 바꿨는가?
- batch 128에서 logical requests, physical batches, token tail은 얼마인가?
- 이 실험은 base에서 정확히 무엇 하나를 바꿨는가?
- 같은 코드와 asset으로 다시 실행할 수 있는가?

이 조건이 만족되면 이후에는 결함을 하나씩 우연히 발견하는 것이 아니라, 새로운 결함 계열이
경계에서 즉시 실패한다. 그것이 이번 clean-room 재설계의 핵심이다.
