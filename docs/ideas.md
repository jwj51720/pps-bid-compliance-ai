# Experiment Ideas

These are candidates for experiments after EXP-001. They are intentionally not implemented in the baseline.

## Naive Law RAG

Chunk the organizer-provided legal package, embed it with the permitted `BAAI/bge-m3` model, and retrieve relevant provisions for each notice. Decide later whether indexes are built before packaging or at runtime, based on DACON limits.

## LLM Wiki

Pre-structure the provided laws and item definitions into a compact knowledge base containing conditions, exceptions, and positive/negative patterns for each of `v1` through `v24`.

## Self-label and Case RAG

Use an approved external LLM only with competition-provided inputs to label selected `train_unlabeled` candidates. Preserve model, prompt, settings, inputs, and outputs, then retrieve similar positive, negative, and hard-negative cases at inference time.

## EXP-002: Official Reference-Data Decision Cards

EXP-001 shows that a generic prompt with only item names cannot distinguish the overlapping product, price, and exception conditions in `v10` through `v18`. Build compact, auditable decision cards from official files before introducing broad RAG.

1. Normalize `meta` into typed facts: governing contract law, procurement type, estimated price, budget, region fields, contract method, award method, dates, and detailed product codes.
2. Join `세부품명번호목록` to `data/법령패키지/중기부고시/중기부고시_경쟁제품_세부품명.csv`. The CSV has 616 competitive-product detailed codes, including 360 marked as direct-purchase construction materials. Record `competitive_product`, `direct_purchase_material`, matched codes, and unmatched codes as derived facts.
3. Encode only source-backed legal gates in compact cards: product status, price bracket, applicable contract law, required restriction, and stated exception. This directly addresses v10-v18; never infer a legal condition from a missing CSV match.
4. Create separate cards for document-led items: v1-v9 (qualification, performance, region, model wording), v19/v21-v23 (supply confirmation, joint contract, briefing conditions), and v24 (field-by-field document-to-meta comparison).
5. Give Gemma the notice, normalized facts, the applicable card, and only the relevant legal excerpts. It must still receive actual notice content at least once. Python owns arithmetic, code lookup, exact evidence resolution, and safe rule corrections.

Keep the first generated artifact small: a versioned `data/derived/decision_cards.json` plus a registry entry containing raw-source hashes and the creation command. This is permitted static data, is packageable, and avoids a premature `rules/` or `retrieval/` directory.

## Context Selection Before Law RAG

The EXP-001 prompt admitted only 4,000 characters; just 8 of 200 dev notices fit in full. Gold evidence was usually visible, but recall remained low, so context expansion is necessary but insufficient.

Use the evaluation model's 32,768-token sequence budget for deterministic packing rather than first-document truncation. Reserve the configured structured-output allowance and measure prompts with the supplied Gemma tokenizer; the baseline's 16,384-token setting is only a speed-oriented example, not an evaluation limit:

- Include all metadata and one short header for every document.
- Include candidate windows for cue terms, product codes, money, percentages, dates, regions, and briefing/confirmation wording from every document type.
- Reserve space for the decision card and related law excerpts.
- Mark unavailable documents from `dropped_doc_counts`; absence-based labels must distinguish unavailable from observed absent.

Measure gold-evidence coverage and per-item F1 against EXP-001 before adding embedding retrieval.

## Case RAG and Self-Labels After the Fact Layer

Use the 200 dev labels first as item-specific positive, negative, and hard-negative examples. The 20,000 unlabeled notices should not be labelled indiscriminately: use the normalized facts and lexical candidates to form small strata, then self-label candidates and matched hard negatives using only competition-provided documents, metadata, laws, and the allowed Gemma model.

Store every self-label run under `data/derived/` with source IDs/hashes, model, prompt, settings, raw output, and validation result. Retrieve examples only after the fact layer establishes the applicable item and product/price regime. This makes few-shot examples clarify a decision boundary instead of teaching Gemma spurious wording correlations.

## Output-Contract Ablation

Compare the same fixed dev sample using (a) one 24-label judgment-only call with Python evidence extraction and (b) the current joint judgment/evidence call. Apply a second call only to ambiguous or evidence-missing positives. Do not run 24 calls per notice: the test set has 1,853 notices and the two-hour limit makes that design unsafe.

The first follow-up experiment must be selected from EXP-001 error analysis rather than from this list alone.
