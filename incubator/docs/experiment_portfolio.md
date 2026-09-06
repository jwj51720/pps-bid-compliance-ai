# Experiment Portfolio and Ordering

## Guiding principle

Spend OpenRouter budget only where a deterministic inspection proves that the
model will see the relevant source facts and a small active-item prompt can test
a distinct legal decision. Broad “more context” and “more instructions” variants
are deprioritized: historical experiments already found them neutral or harmful.

## P0 — Build measurement before model calls

### P0.1 Reproducibility and historical-baseline audit

Recreate the documented baseline configuration against the local source tree in
mock mode, verify paths and submission columns, and record which historical
results have local artifacts. Then run one frozen, small paid comparator only if
the prompt hash matches its documented comparator.

**Success:** an auditable starting point; no claim that undocumented artifacts
are reproducible.

### P0.2 Item coverage and error taxonomy

For every dev gold positive, identify document type, evidence availability,
applicable contract-law family, price/product metadata, document cue class, and
whether it is local, absence, or cross-source. For dev negatives, build matched
hard-negative strata. This is an analysis aid, not a final-label lookup.

**Success:** each of 24 items has a candidate-source and failure taxonomy.

### P0.3 Provenance-preserving legal corpus

Extract only item-table-linked official statutes, decrees, regulations,
guidelines, notices, and table/appendix units. Preserve complete legal meaning:
article title, all paragraphs/items, table header, units, exceptions, source
path, source SHA-256, boundaries, and chunk SHA-256. Resolve currently uncertain
selectors from the source text before use.

**Comparator:** no legal chunk versus one narrow active-item chunk.  
**Success:** legal context is small, exact, token-accounted, and source-backed.

**Current status:** INC-023 resolved 76 article units; INC-028 fixes the
remaining named-section boundaries and records that the exact submission
tokenizer is unavailable here. No char-based admission substitute or paid
token-count probe is allowed.

## P1 — Separate task shapes with low-cost pilots

### P1.1 Exact structured facts and `v24` reconciliation

Build a non-learned extractor for amounts, percentage thresholds, dates,
contract/award method, region restrictions, product codes, business restrictions,
and document provenance. Create a field-by-field reconciliation candidate report
for v24; Gemma adjudicates ambiguous document wording and returns document-only
evidence.

**Why first:** v24 is not a law-retrieval problem and is currently diluted inside
the joint prompt.  
**Risk:** false mismatches caused by VAT, rounding, different financial fields,
or anonymized regional descriptions.  
**Gate:** no automatic positive correction until matched-negative review confirms
normalization semantics.

**Current status:** INC-011/011R closes the presently available four-field
ontology. The broad matcher is too nonspecific and the heading/value repair
misses most positives; do not reopen this branch without a new
organizer-provided source-field mapping.

**Metadata rule status:** INC-031 rejects exact metadata-state tables as
automatic label policies. A state may be rendered as an applicability fact only
when an independent legal predicate—not dev state purity—justifies it.

**Current deterministic progress:** INC-033R found complete source-line fact
coverage for v3 and v21 only. INC-034/036 formalized two law-linked predicates
without dev-derived numeric cutoffs, and INC-037 replaces only those cells in
the immutable global baseline (dev Macro F1 0.24856). Treat this as an audited
component, not a reason to tune adjacent items from the same dev labels.

### P1.2 Product and price applicability engine (`v10`--`v18`)

Use exact 10-digit product-code matching against the organizer CSV, preserving
`matched`, `not_matched`, and `unknown` separately. Compute price brackets and
contract-law applicability from metadata. Use these facts only to select the
applicable active-item law/card prompt; unknown never means non-competitive.

The first calls should cover at most this group, not all 24 labels. Absence
items receive a document-coverage presence check; document-local positives
require source evidence.

**Why first:** baseline errors and prior experiments identify this family as the
largest false-positive/false-negative source.  
**Gate:** stratified pilot over all target positives and matched product/price
hard negatives, followed by dev-200 confirmation if any suppression/merge logic
changes.

### P1.3 Qualification, performance, region, and model terms (`v1`--`v9`)

Create high-recall lexical/numeric candidate windows for participant classes,
performance amount/ratio/period, geographic restrictions, duplicated
restrictions, and model/brand wording. An active prompt sees only this group and
the relevant law family. The full notice triage remains available for context.

**Risk:** words such as “실적”, “지역”, and model-like tokens occur in benign
examples.  
**Gate:** report false triggers by cue and prove that candidate extraction does
not lose dev-positive evidence.

### P1.4 Procedural and special cases (`v19`--`v23`)

Treat supply-confirmation timing, joint-contract ratios, SW qualification, site
briefing eligibility, and local-negotiated briefing periods as separate
subproblems. Use date and percentage normalization where applicable, and apply
contract-method/legal-family gates before a targeted call.

**Risk:** these items have few dev positives and sparse language variants.  
**Gate:** do not make final deterministic rules from dev wording alone; require
official legal conditions and a full-dev review.

## P2 — Retrieval ablations

### P2.1 Lexical retrieval first

Use exact item/law selectors, normalized metadata filters, Korean cue lexicons,
and BM25 over provenance-preserving chunks and extracted evidence windows.

**Comparator:** deterministic selector only.  
**Success:** retrieves the required legal/document unit on target cases with
materially fewer tokens than full documents.

### P2.2 Hybrid retrieval with BGE-M3

Only after P2.1, add BGE-M3 as a rank-fusion complement for semantic variation.
Use the permitted model through the provided offline `PPS_EMBED_DIR` in a final
submission design; OpenRouter's `baai/bge-m3` endpoint may be used for isolated
development experiments. Record endpoint model/version and keep vectors/index
as reproducible static derived artifacts.

**Risk:** embeddings can obscure exact numbers, codes, and legal citations;
they must never override exact metadata/code gates.  
**Gate:** show recall improvement over lexical retrieval on a frozen query set,
with no token-budget or runtime regression that blocks submission.

**Current negative evidence:** INC-025's generic full-notice BGE leave-one-out
audit cleared the embedding transport/provenance gates but produced 2×
same-label enrichment for only 8/24 items, scattered across task shapes. Do
not run global dev-few-shot or generic Case RAG. Any future BGE use must first
be conditioned by an independently validated exact fact/evidence type.

### P2.3 Evidence-window retrieval

Retrieve source-document windows with stable character offsets, then require
final evidence to resolve against the full original document. Windows are for
attention, not evidence alteration.

**Success:** unchanged source substring validity stays at 100% for gated items.

## P3 — Case retrieval and permitted self-labeling

Mine unlabeled notices using P1 facts/cues into item-specific strata: likely
positive, likely negative, ambiguous, and rare-layout cases. Label only selected
strata using Gemma/OpenRouter and organizer materials. Keep a complete audit
trail, then retrieve examples only for the active item group and matching legal,
price, and product regime.

**Do not start here.** Case RAG without a reliable applicability layer risks
teaching Gemma superficial wording and spending budget on an unstratified 20,000
notice corpus.

**Gate:** self-label agreement checks, source-backed audit samples, and a
frozen dev comparison against the corresponding no-case-RAG policy.

## P4 — Scheduling and final-system ablations

Compare these bounded schedules after item-group quality is known:

1. one full-notice triage + candidate-targeted groups;
2. one full-notice triage + only ambiguity/evidence-missing second calls;
3. document-local groups with source-local evidence and notice-level groups with
   full-coverage logic.

For each schedule, estimate actual prompt/completion tokens, batch shape, and
worst-case calls for 1,853 notices. The target is not the fewest calls; it is a
safe two-hour policy with clearly superior per-item behavior.

## Explicitly deprioritized experiments

- another generic 24-item “be more careful” prompt;
- standalone fixed-family output decomposition: INC-024 isolated it with
  complete identical notices and found more false positives than corrections;
- global extract-then-adjudicate prompt separation: INC-027 r1 completed its
  frozen paired pilot without structured-output failures but lost recall and
  Macro F1; do not repair or confirm it as a general policy;
- generic whole-notice Case RAG: INC-025 found no coherent item-family signal;
- lexical/structural cue absence as a global candidate gate: INC-026 has
  incomplete gold-evidence supervision, misses several evidenced items, and
  leaves v3 with near-universal negative activation;
- a full legal package or a large fixed law bundle in every joint call;
- character-based truncation or arbitrary legal chunk splits;
- treating absent product codes as proof of a non-competitive product;
- all-item, all-document OR merging for absence or metadata-comparison labels;
- indiscriminate self-labeling of all 20,000 notices;
- submissions or leaderboard calibration before a reproducible dev improvement.

## Next preregistered topology gate

INC-066 tests an independent source-line *attention proposal* pass followed by
a complete-notice final decision.  It differs from all closed retrieval and
extraction routes because proposals are neither labels nor candidate gates and
the final pass retains all original documents.  Its two repeated arms and
decision rule are frozen in
`incubator/docs/inc066_attention_proposal_topology_protocol.md`; it is the
only currently authorized paid direction before another broad ideation pass.
