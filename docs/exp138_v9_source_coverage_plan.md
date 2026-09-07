# EXP138 — v9 source-coverage test

## Evidence before the experiment

The rendered-input audit found three v9-positive notices whose unchanged gold
model-name evidence is in an omitted `규격서`, not in the actual 4,000-character
organizer prompt (`PPS-DEV-09`, `12`, `23`). This is a deterministic source
coverage gap. It is not repaired by a card, a keyword rule, or a positive
default.

## Controlled change

EXP133's two groups become three disjoint groups:

- G01: the unchanged 19 remainder items, 4,000-character organizer context;
- G02: v6, v7, v8, v19, unchanged 4,000-character organizer context;
- G03: v9 alone, `full_split_merge` with exact-tokenizer admission.

G03 makes one source-document pass per complete organizer document and splits
only an oversized source document. Thus a 규격서 is actually shown to the model
when present. No law/card/retrieval/product context, decision rule, decoding,
or other item context is changed. G03's final v9 is an OR across its document
passes; evidence is retained from its source pass. This is a runtime-risk
ablation, deliberately limited to one item.

## Required rendered-input review

Before the paid fast-20 run, export and read actual messages for:

1. `PPS-DEV-062` (short complete notice);
2. `PPS-DEV-042` (announcement overflow); and
3. `PPS-DEV-01` (attachments).

For G01/G02, confirm byte-identical user input to EXP133. For G03, confirm
each document pass identifies its target document, includes the source text,
uses no raw law/card, and stays inside the exact Gemma budget. Additionally
inspect `PPS-DEV-09`, `12`, and `23` directly: their 규격서 pass must contain
the formerly inaccessible model-name text. Run preflight, all-fast-panel
tokenizer admission, and mock execution before the provider call.

## Decision

Compare against EXP133. Continue only if v9 F1 improves without a material
macro decline, parses remain clean, and the measured v9 context/pass count is
small enough to project safely to competition runtime. A fast-panel result is
diagnostic; it cannot change the canonical policy.
