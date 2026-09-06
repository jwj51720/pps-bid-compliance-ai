# INC-028: Complete Legal-Context Admission Protocol

## Question

INC-021 is the only full-dev result above the INC-018 global reference, but it
changed both legal context and output-family decomposition. INC-024 separately
rejects output-family decomposition. INC-028 therefore isolates a single
question: can source-complete, item-table-linked organizer-law context be
admitted alongside a whole notice for one joint 24-item output?

This is an admission and provenance experiment, not yet a paid prediction
experiment. No dev labels select a law unit, a threshold, an item, or a source
span.

## Frozen source-unit policy

INC-023's 76 uniquely cited `제N조` units remain unchanged. The following
manual citations have an unambiguous *named legal boundary*, even though they
are not article-number citations. They may be added only as the complete named
boundary below; no character excerpt, keyword neighborhood, or partial table
is allowed.

| Item(s) | Organizer source | Complete unit boundary | Status |
|---|---|---|---|
| v2, v4, v9, v19 (local) | 지방자치단체 입찰 및 계약 집행기준 | 제1장 입찰 및 계약 일반기준, `7. 계약담당자 주의사항` through before `8. 계약정보의 공개` | boundary review ready |
| v5 (national) | 재정경제부장관이 정하는 고시금액 | current operative notice body, title through before first `부칙` | boundary review ready |
| v20 | 중소 소프트웨어사업자의 사업 참여 지원에 관한 지침 | `제2조(사업금액의 하한)` plus its expressly incorporated `[별표 1]`, each complete to the next same-level section/table | boundary review ready |
| v21 (national) | (계약예규) 공동계약운용요령 | current operative body, title through before first `부칙`; the item table cites the instrument without a narrower unit | boundary review ready, potentially large |
| v21 (local) | 지방자치단체 입찰 및 계약 집행기준 | 제6장 공동계약 운영요령, complete chapter through before the next chapter | boundary review ready, potentially large |
| v23 (local) | 지방자치단체 입찰시 낙찰자 결정기준 | 제7장 협상에 의한 계약 낙찰자 결정기준, 제3절 입찰과 계약상대자 결정절차 through before 제4절 | boundary review ready |

The v10/v11 product-designation citation is **not** converted to a law-text
context. The organizer text explicitly says its substantive list is image-only
and directs use of the original HWPX and exact-code CSV; the existing exact
product index remains an audit fact, not a fabricated prose legal unit. v23
nationwide and v24 are item-table-declared non-law/cross-source exceptions.

## Tokenizer gate

On 2026-09-05, local `transformers` can import, but the cached
`google/gemma-4-26B-A4B-it` artifact lacks a usable tokenizer backend:
`AutoTokenizer.from_pretrained(..., local_files_only=True)` fails before an
encode operation. No `PPS_MODEL_DIR` was provided in this environment.

Therefore INC-028 must not use character counts as a proxy, send a paid
token-count-only OpenRouter request, or select a smaller legal unit. It remains
**admission-blocked** until the exact tokenizer from the submission runtime is
available. This is a reproducibility gate, not a performance blocker: all
source units and their inclusion rules are now fixed independently of dev
metrics.

## When the tokenizer is available

1. Encode each frozen complete legal unit and the fixed non-document prompt.
2. For every dev notice, admit fixed legal context first and then exact complete
   documents using the submission's context/output reserve policy.
3. Record unit hashes, exact tokens, admission outcome, omitted-document
   coverage, and all overflow packs. Never shorten a legal unit to rescue an
   overflow.
4. Proceed only if the same frozen policy is admissible for every notice. The
   subsequent paid pilot is a paired joint-24 control versus joint-24 plus this
   legal context alone; no family-output split, case RAG, item rule, or
   retrieval-rank change is permitted.

If fixed complete context is not admissible, reject global legal context before
any prediction calls. A future item-group experiment would need a separately
pre-registered legal applicability mechanism, not a length-based repair.
