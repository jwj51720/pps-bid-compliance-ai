# EXP171 이후 구조 탐색 프로그램 v1

작성일: 2026-09-10 (dev / mac)

## 목적과 고정점

EXP171의 유일하게 일관된 신호는 모든 exact-token admitted source pack에서 **법률 판단 없는
사실 navigation**을 먼저 수집하고, final Gemma가 card v6·필요한 human-readable
metadata·friendly competition-product fact·navigation·**모든 admitted 원문**을 다시 읽는
구조다. fast20, independent holdout20, dev200에서 capacity-matched direct control보다 같은
방향으로 높았다. 이 프로그램은 그 네 가지 final 입력을 줄이거나 대체하지 않는다.

다음은 후보가 아니다: raw-law/law-summary RAG, 20k case RAG, Python 문구/법률 판정 또는
label override, document × v-group multiplication, full-split × grouping, final 4k anchor,
category 후보 수 증가, navigation 위치 변경, 이미 실패한 global label adjudication이다.

공통 base는 repeatability evidence가 있는 EXP179 source-first/full-final v1이다. card,
metadata/product renderer, source admission, final V/E schema, evidence resolver, merge,
frozen EXP123 v2/v3/v21 postprocess, model parameters는 고정한다. 각 실제 유료 config에는
`experiment.base_config`, `allowed_policy_changes`, isolated output path를 명시한다.

## 후보 비교

| 후보 | 새 역할 | final label 소유자 | 최소 topology | 지금 상태 |
| --- | --- | --- | --- | --- |
| A. 조건부 관계 navigation | 기존 7 category가 표현하지 못하는 하나의 source relation을 source-only로 역할화 | 기존 full-source final Gemma | EXP171 + 적용 notice당 1 source-only pass | EXP180 v23은 fast20에서 하락해 기각 |
| B. notice procedure model | qualification/product/schedule/documents/contract/metadata counterpart 관계를 source-grounded ledger로 모델링 | 기존 full-source final Gemma | **교체형** one whole-notice source-only relation pass + final | EXP182/183은 fast gain이 holdout에서 붕괴해 기각 |
| C. final-source consistency review | final V/E가 원문·card·metadata와 양립하는지 별도 Gemma가 검토 | reviewer Gemma; Python은 reviewer의 JSON만 전달 | EXP171 + 1 full-source review pass | runtime/semantic contract proof 전에는 구현·유료 실행 금지 |

세 후보 모두 navigation/review가 empty 또는 malformed일 때 Python이 어떤 v를 0으로 만들지
않는다. evidence는 여전히 final source document의 unchanged substring(최대 500자)만 남긴다.

## A. 조건부 관계 navigation

### 가설

7개 broad category는 날짜, 대응 필드쌍, 동일 자격조항의 두 제한처럼 **관계 자체가 필요한
truth condition**을 raw snippet으로만 남긴다. 해당 관계를 source-only로 명시하면 final이
원문을 다시 찾고 card를 적용하기 쉬워진다.

이는 multi-item schema로 일반화하지 않는다. 먼저 organizer semantic contract와 source-only
rendered message를 대조해 해당 v의 관계가 기존 category의 최대 3 excerpt로 표현되지 않는
구체 사례를 보인다. 그 뒤에만 하나의 v와 하나의 applicability slice를 추가한다.

현재 유일한 준비된 최소 후보는 `docs/exp180_v23_timeline_navigation_plan.md`의 지방
협상계약 v23 timeline이다. 그것은 날짜 계산이나 violation을 stage-1b에 맡기지 않으며,
eligible notice에만 0–2 unchanged substring/role을 수집한다.

### gate

EXP180 또는 후속 A 후보는 mode 하나만 allowed change로 선언한다. exact tokenizer admission,
short complete/attachment/overflow rendered stage-1·final review, 24-item semantic-input
contract, malformed/duplicate/empty navigation mock, fast20을 먼저 통과한다. fast gain은
independent holdout20, 그 다음 dev200으로만 확대한다.

## B. notice procedure model

### 가설

source-first의 이득은 excerpt 수가 아니라, final이 공고 전체의 사실 구조를 먼저 훑게 되는
데서 나왔을 수 있다. broad category snippet과 달리 source-grounded procedure ledger가
qualification, product requirement, schedule, required document, contract method, metadata
counterpart 간의 연결을 남기면 final이 full source에서 더 적은 재탐색으로 판단할 수 있다.

### 구현 전 representability audit

이 후보는 당장 새 schema를 만들지 않는다. 다음 label-blind audit artifact가 먼저 필요하다.

1. card v6와 semantic-input contract의 사실 요구를 relation type으로 분해한다.
2. 각 relation type이 현 7 category의 unchanged excerpt만으로 역할과 양쪽 endpoint를
   잃지 않고 표현되는지 표시한다.
3. 표현 불가 relation은 organizer source, 필요한 document/metadata fact, exact rendered
   span, 예상 source packs와 함께 기록한다.
4. 표현 불가가 발견돼도 all-24 schema로 승격하지 않는다. independent relation types가
   실제로 복수이고 하나의 minimal ledger가 각 type의 source provenance를 보존하는 경우에만
   schema draft를 만든다.

schema draft가 생기면 stage는 one whole-notice source-only call이며 label/evidence/법률판단을
출력하지 않는다. ledger field마다 document id와 unchanged source substring을 Python에서
검증한다. final은 ledger를 신뢰해 자동판정하지 않고 same full source를 다시 본다.

### paid gate

base EXP179 대비 `staged_run.mode` 하나만 바꾼 config가 전제다. schema worst-case completion
size, exact admission 뒤 stage/final context count, 1,853-notice call upper bound를 먼저
기록한다. source omission, parser recovery, evidence warnings가 EXP179보다 나빠지거나
topology가 bounded whole-notice extra pass를 넘으면 paid fast20 없이 종료한다.

## C. final-source consistency review

### 가설

final V/E가 navigation과 원문을 모두 보아도 card의 exception 또는 metadata counterpart를
놓칠 수 있다. 완결 입력과 full source를 다시 주고 “이 final result가 source/card/meta와
양립하는가”만 독립적으로 검토하면 source-first의 recall 이득을 보존하면서 unsupported
positive/negative를 줄일 수 있다.

### 기존 기각과의 경계

이는 EXP146류의 global adjudication을 재실행하지 않는다. 기존 final을 Python OR/AND 혹은
hard override하는 label selector도 아니다. candidate가 성립하려면 reviewer가 모든 24 v에
대해 same semantic input contract와 every original source를 받고, each changed label의
source-grounded reason/evidence를 반환하며, full replacement V/E result를 Gemma가 소유해야
한다. Python은 parsing, unchanged substring validation, existing merge만 한다.

### 구현 전 proof

이 조건은 third whole-notice stage가 되어 EXP171 dev200의 observed 435 calls에 final pack
수만큼 추가될 수 있다. 따라서 다음을 모두 만족하기 전에는 config나 paid run을 만들지 않는다.

1. exact prompt는 final card/meta/product/full-source contract를 빠짐없이 다시 포함한다.
2. reviewer output contract와 replacement/merge semantics가 EXP146과 다른지 문서화한다.
3. shortest, attachment, overflow notice에서 reviewer message를 export해 읽고, 24/24
   semantic-input audit을 통과한다.
4. exact tokenizer admission과 dev200/test-sample call projection이 2-hour limit에 대한
   현실적인 margin을 보인다. OpenRouter wall time은 근거로 쓰지 않는다.
5. malformed reviewer output은 final result를 자동으로 0 또는 그대로 확정하는 Python rule이
   되지 않도록, Gemma-owned fallback semantics를 mock과 parser test로 증명한다.

이 proof가 통과해도 fast20 → independent holdout20 → dev200 순서다. quality와 evaluator
runtime의 독립 근거가 없으면 제출 후보로 승격하지 않는다.

## 우선순위

1. EXP171 제출 후보의 evaluator runtime 관측을 확보할 수 있을 때까지 canonical policy는
   `submit-exp171-source-first-full-final-v1`로 동결한다.
2. EXP180의 conditional v23 timeline은 fast20 `0.241667` (EXP179 `0.287500`)으로, EXP182의
replacement procedure ledger는 fast20 `0.319444`였으나 frozen holdout20 `0.125000`
(EXP168 `0.229167`)으로 각각 기각됐다. EXP184 strict source-only broad inventory도
tokenizer stage-1 입력 66,089 tokens를 줄였지만 fast20 `0.283333`으로 기각됐다. relation
field wording·excerpt cap·item follow-up 또는 source-only wording tuning은 이 후보군을
되살리지 않는다.
3. C는 EXP146의 전역 second-adjudication 기각과 같은 위험을 다시 갖고, third full-source
stage의 runtime 근거도 없다. 따라서 새 quality mechanism 또는 evaluator runtime 관측이
생기기 전까지 구현하거나 유료 실행하지 않는다.
4. 다음 구조 후보는 이미 기각된 relation/adjudication family를 재포장하지 않아야 하며,
EXP171의 source-first/full-final contract를 보존하는 별도 information-flow hypothesis부터
문서로 증명한다.
