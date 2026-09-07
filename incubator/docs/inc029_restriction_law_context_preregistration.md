# INC-029: Restriction-Law Context Isolation Pilot

## Motivation

INC-018 has zero recall on v4, v6, v7, and v8 (25 positive cells across 21
unique notices). These are not four arbitrary labels: each concerns whether a
restriction is lawful under the applicable contract regime, and the organizer
item table points to the same small set of national/local restriction rules.
They have not received a controlled comparison of complete legal units alone.

## Frozen cohort

The treatment cohort contains all 21 dev notices positive for at least one of
v4/v6/v7/v8:

`PPS-DEV-05, 06, 08, 09, 10, 11, 039, 042, 048, 050, 051, 053, 054, 059,
061, 062, 063, 066, 070, 071, 072`.

It additionally contains 15 negatives selected deterministically by ascending
ID, cycling through the positive cohort's `(적용계약법, 계약방법)` strata.
Labels are used only to form the complete-positive/matched-negative evaluation
cohort; they do not select prompt content or a law unit.

## Controlled arms

Both arms make one Gemma call per notice, receive all original documents in
official order and all metadata, emit only v4/v6/v7/v8, use the same model,
temperature, seed, schema, output cap, evidence validator, retry policy and
per-notice durable checkpoint.

- **Control:** the four item definitions and the whole notice only.
- **Treatment:** identical input plus the following complete organizer-law
  units selected solely by `metadata.적용계약법`:
  - national: Government Bid/Contract Execution Standard Article 5 and National
    Contract Act Enforcement Rule Article 25;
  - local: Local Contract Act Enforcement Rule Article 25, Local Bid/Contract
    Execution Standard Chapter 1 Section 7, and Chapter 5 Section 3 Item 1.

The named sections are included from their title through the next same-level
heading. An article is included from its header through the next article. No
BGE retrieval, law-text compression, character window, source cue, price rule,
or model-output merge is allowed. If a whole notice plus its fixed legal units
is rejected by the provider, that arm/notice is a recorded admission failure;
no document or law unit may be shortened.

## Budget and gates

There are 72 maximum calls (36 notices × 2 arms) and a $0.25 reported-cost
ceiling. A parse/transport/admission failure rate above 5% invalidates the
pilot. Evidence for every treatment positive must validate against the notice;
law text is never evidence.

**Success:** treatment target Macro F1 ≥ control + 0.05, target micro recall
does not decrease, new matched-negative false positives ≤2, and evidence
validity is 100%. Then run the frozen same policy across dev-200, leaving all
other labels at the INC-018 baseline for an isolated overall impact estimate.

**Partial:** target Macro F1 improves but misses the gate, with a coherent
error type and no guardrail failure. Permit one repair to the *legal-unit
boundary only*, documented before calls.

**Failure:** no target improvement, recall loss, broad matched-negative false
positives, evidence failure, or transport failure. Reject complete legal
context for this restriction family; do not tune wording, law rank, or notice
length.
