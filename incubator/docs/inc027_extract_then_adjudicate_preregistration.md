# INC-027: Extract-Then-Adjudicate Pilot

## Rationale

INC-024 shows that changing output grouping does not repair incorrect factual
interpretation. INC-025 and INC-026 show that generic semantic/lexical source
selection is not a safe global gate. This experiment changes a distinct,
upstream variable: whether Gemma must both discover relevant source facts and
apply 24 legal predicates in one generation.

## Frozen arms

The joint-control outputs from INC-024 are retained as the paired comparator.
The treatment uses two calls for the same complete ordered notice and metadata:

1. **Extractor:** emits only a typed ledger of explicit document facts. Each
   fact must include source document ID, unchanged quote, and type among money,
   date/time, ratio, product code, contract/procurement method, qualification,
   region, corporate restriction, joint-contract term, or metadata comparison.
   It may emit an empty list; it must not infer a violation.
2. **Adjudicator:** receives the item table, metadata, and ledger. It emits all
   24 judgments. A non-absence positive may use only an extractor quote that
   validates unchanged against the original full notice; otherwise Python
   downgrades it to zero. Absence items retain full-document coverage semantics
   and have blank evidence.

Both calls contain the actual notice (the adjudicator receives it as a fixed
source-validation appendix as well as the ledger). No retrieval, law card,
candidate cue, character cap, length-derived policy, prediction routing, or
per-item correction is allowed. Complete-document provider rejection is a
failure, not permission to shorten the notice.

## Pilot contract

Use the first eight ordered IDs of the frozen INC-024 cohort. The control rows
are copied from the immutable INC-024 joint artifact; treatment makes exactly
16 calls. The extractor and adjudicator model/settings/schema are frozen before
requests. Maximum additional spend is $0.20; parse/transport failure above 5%
immediately invalidates the run.

The purpose is mechanism diagnosis, not metric selection. Report changed cells,
TP/FP/FN and Macro F1, extraction quote validity, empty-ledger frequency,
extractor/adjudicator tokens, and all-negative changes.

## Amendment: r1 transport-safe execution and fact-schema clarification

The initial execution is invalid: two notices completed, then the third
extractor response was non-parseable, exceeding the pre-registered 5% failure
limit. It is retained in `inc027_extract_then_adjudicate_pilot/` as an invalid
transport/parse artifact and will never be scored as an arm.

Before r1 requests, the extractor fact schema is clarified only: every allowed
`type` has a schema description and the same definitions are printed in the
extractor instruction. This repairs the observed ambiguity where unrelated
facts were all typed `product_code`; it neither changes the adjudicator prompt
nor adds labels, retrieval, source selection, thresholds, or post-hoc rules.
The r1 executor runs one frozen cohort notice per invocation, writes a
fsync-backed stage checkpoint and a per-notice result (including raw response
on failure), then aggregates separately. This changes failure observability,
not model input or the experimental variable. The original $0.20 total cap
remains across r1 requests; r1 does not reuse initial invalid-run outputs.

## Decision

- **Success:** at least four net corrected cells, no more than one new
  all-negative positive, and 100% valid non-absence treatment evidence. Then
  run a separately preregistered 24-notice paired confirmation.
- **Partial:** source validity and a coherent error reduction improve but the
  net gate misses. Permit exactly one repair to the *fact schema only*.
- **Failure:** no net correction, recall collapse, invalid evidence, or broad
  all-negative FP. Reject extraction/adjudication separation; do not repair the
  adjudication wording.
