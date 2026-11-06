# EXP189 — 공고문-only source-scope ablation

작성일: 2026-09-10 (dev / mac)

## 질문

Complete-source direct final(EXP172)에서 첨부문서가 cross-pack OR noise/runtime을 만드는지,
아니면 실제 판정 사실을 제공하는지 분리한다. 이는 submission policy가 아니다. 공고문 밖
첨부가 위반 근거일 수 있다는 대회 규칙은 유지하며, 결과가 좋아도 source exclusion을
제출 후보로 승격하지 않는다.

## 고정 입력과 두 arm

공통으로 EXP172의 card v6, human-readable metadata, exact product fact, final V/E schema,
frozen postprocess, decoder, evidence validator와 merge를 그대로 쓴다. 바꾸는 것은 source scope
와 overflow 처리뿐이다.

1. **A — announcement-only packed:** `공고문`만 보되 exact tokenizer admission으로 overflow
   source packs 전체를 final V/E에 넣는다. non-absence OR와 absence AND는 기존과 같다.
2. **B — announcement-only single-prefix:** `공고문`만 보되, cards/meta/product/final contract를
   포함한 exact 30,268 input budget에 들어가는 가장 긴 공고문 prefix 한 번만 넣는다. 뒤의
   공고문과 모든 첨부는 의도적으로 미관측이다. merge가 없으므로 A와 source-cross-pack merge
   영향을 분리한다.

둘 모두 `lifecycle: diagnostic`, `visible_document_types: [공고문]`로 명시하며 complete-source
semantic audit를 통과한 submission policy와 혼동하지 않는다.

## Gate와 판정

각 arm은 provider 전 exact tokenizer source admission/profile, mock, short/attachment/overflow
rendered input review, 49-column/evidence validation을 기록한다. B는 notice별 retained/dropped
token/document length를 전수 기록한다. fast20에서 EXP169/172 direct control과 macro F1뿐 아니라
per-item TP/FP/FN, attachment-origin gold evidence가 있는 FN, parse/recovery, call count 및 runtime
을 비교한다. 한 arm의 fast gain도 holdout/dev200/submission 권한이 아니다; 이 ablation은
source-scope 원인 진단으로 종료한다.

## Fast20 result — 2026-09-10

Both arms completed 20/20 with validation pass. A (announcement-only packed) scored `.213889`;
B (announcement-only single-prefix) scored `.220833`; both are below matched full-source direct
EXP169 `.262500` by `.048611` and `.041667`. A remote elapsed `56.0s`, B `49.2s`; neither is
evaluator-vLLM evidence.

The intended prefix comparison is **not identified on fast20**: A made exactly 20 final calls and
B exactly 20, so every fast-panel announcement already fit a single exact-token context. The two
arms therefore saw the same source material; their small score difference must not be interpreted
as a truncation effect. Running B on holdout only to obtain another mostly-untruncated sample would
spend tokens without answering the question.

What is identified is attachment exclusion: removing attachments loses direct-full-source positives
at v4/v12 and changes product/Sme/document judgments into v13/v17 FPs. A has v13 three FP and v23
four FP; B retains v13 three FP and adds a v24 FP. Evidence validity is `.7143` (A) / `.8333` (B),
so the loss is not a CSV substring failure. **Decision: do not promote announcement-only scope.**
The submitted runtime fallback remains direct full-source, not announcement-only. A future B test
is justified only on a precomputed overflow-only cohort, with no labels used to select it.
