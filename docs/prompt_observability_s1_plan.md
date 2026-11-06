# S1 — baseline prompt observability audit

## Question

Before another paid prompt change, distinguish two cases for each dev gold
positive under the current canonical 4,000-character organizer-baseline input:

1. the source evidence/fact is already inside the exact context but Gemma did
   not apply the item boundary correctly; or
2. the source is outside the context, or a positive absence judgment needs a
   document scope that the context omitted.

## Method

`scripts/audit_prompt_observability.py` reconstructs the actual shared
`build_official_baseline_context` output for every dev record. It uses gold
labels/evidence only *afterwards* to count source visibility and writes a
separate review pack below `outputs/prompt-observability-s1/`.

It never constructs a model prompt, retrieval query, decision card, routing
feature, or Python correction. The audit is diagnostic only.

## Decision rule

- If source-visible positives dominate an item's misses, do not solve it by
  adding documents or split/merge calls; inspect the item's semantic boundary
  and existing prompt representation first.
- If source-outside or absence-scope cases dominate, document coverage is a
  real prerequisite but any repair still requires a separate runtime-quality
  experiment.
- Do not turn either count directly into item-specific dev rules.
