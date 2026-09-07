# EXP130 — four-group organizer prompt diagnostic

## Hypothesis

EXP129 directly showed that asking Gemma for one v2 V/E judgment recovered
five v2 positives that the exact 24-item organizer prompt missed, with far
shorter outputs. This experiment tests the smallest complete partition already
defined by the repository: four fixed semantic groups. It does **not** add a
card, raw law, product context, retrieval, document splitting, Python rule, or
new decoding parameter.

## Controlled difference

The base is EXP125A's exact organizer-format 4,000-character single-context
V/E control. EXP130 changes only:

1. `official_baseline_subset_v1`, which preserves organizer wording and user
   rendering but names the active group's keys in the output contract; and
2. versioned `grouped_run.grouping: four_way`.

The groups are fixed in `src/legal_groups.py` and partition every item once:

- G01: v1–v5;
- G02: v6–v9, v19;
- G03: v10–v18;
- G04: v20–v24.

Each notice therefore has exactly four calls (80 calls for fast-20), each with
the same 4,000-character organizer context. There is no document split or
cross-pass label merge: the orchestrator only writes each group's disjoint
keys into the final row.

## Required review gates

Before a provider call:

1. `scripts/inspect_grouped_prompt.py` must export all four real group inputs
   for `PPS-DEV-062` (shorter complete), `PPS-DEV-042` (announcement overflow),
   and `PPS-DEV-01` (attachment overflow).
2. Read the Markdown exports. Confirm each system prompt contains only its
   declared v keys, each user message is identical across four groups for the
   same notice, and the only context markers are actual `[절단]`/`[미수록 문서]`.
3. Run preflight, grouped mock execution, and exact Gemma tokenizer admission.
   Record the observed call count and max token count.

## Evaluation

Compare with EXP125A on the frozen 20-notice fast panel: macro positive F1,
per-item TP/FP/FN, parse errors, evidence validity, per-group output tokens,
and wall-clock time. EXP130 is diagnostic only. It cannot change canonical or
submission policy without a dev-200 quality confirmation and a separately
measured 1,900-notice runtime projection.

Reject it if parse failures, runtime multiplication, or quality decline erase
the potential output-scope gain. Do not repair individual items from the
fast-panel labels.
