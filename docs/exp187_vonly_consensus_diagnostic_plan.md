# EXP187 — multi-V-only full-source consensus diagnostic

작성일: 2026-09-10 (dev / mac)

## User-requested hypothesis

Multiple full-source V-only readings may focus Gemma on binary legal decisions more effectively than
a joint V/E response. EXP187 sends the same complete input (cards v6, friendly metadata/product
facts, every admitted original source) to two independent V-only drafts. A third V-only Gemma call
receives both as explicitly untrusted non-source drafts and re-reads the complete input before
owning the final 24 labels. Python does not majority-vote, OR/AND-merge, alter a label, or select a
draft; it only parses and performs existing source-pack merge.

EXP186 already tested one V-only draft followed by V/E final and fell to `.206944` versus EXP169
`.262500`. EXP187 therefore is a **diagnostic requested by the user**, not a submission candidate
or a wording-tuning sequel to EXP186. It tests a materially different endpoint: a model-owned
V-only resolver after two independent V-only readings.

## Evidence limitation

V-only outputs cannot identify a source-grounded legal evidence span. A Python algorithm that
searches item-specific words, decides relevance, or selects a supposedly supporting sentence would
be a prohibited Python legal/evidence rule. A generic first-substring placeholder would satisfy only
the byte-substring shape while fabricating semantic evidence. Therefore EXP187 leaves non-absence
`e` fields blank, retains validation warnings, and reports only label F1/runtime topology. It may
not be promoted or packaged unless a separate source-grounded evidence owner is designed and tested.

## Scope and gates

- Base EXP169; the only declared changes are `labels_and_evidence -> labels_only`, staged mode,
  and disabling `exp123_v1` frozen postprocess. A model-owned V-only resolver cannot be evaluated
  if a Python postprocess replaces its labels or adds its evidence afterwards.
- Two drafts plus one resolver are full-source all-24 calls. No grouping, RAG, cards, source
  reduction, decoding change, or Python voting.
- Exact tokenizer profile must establish topology/omission before provider use. The 3-stage design
  is a runtime-risk diagnostic and cannot be assumed evaluator-safe from OpenRouter time.
- Mock must establish two independent stored drafts, model-owned final labels, malformed handling,
  49 columns, and explicit blank-e warnings.
- Render/read short/attachment/overflow input. The final must retain the complete semantic input
  contract; both drafts are advisory only.
- A fast20 run is label-only diagnostic evidence. Whatever its score, it does not authorize
  holdout/dev200/submission until a separate valid evidence architecture and evaluator runtime
  proof exist.

## Pre-provider gates — 2026-09-10

- `scripts/preflight_experiment.py` passed: the base is EXP169 and the declared effective changes
  are output mode, staged topology, and removal of frozen postprocess.
- Mock run at `outputs/exp-187-vonly-consensus-full-source-fast-panel-c4-mock/` completed 20/20:
  every record stores exactly two drafts, the final has model-owned labels, and all non-absence
  evidence fields are blank. The mock's all-zero labels naturally create no blank-positive warning;
  `validate_submission` still retains that warning path for a real positive V-only result.
- Semantic contract audits passed 24/24 for short `PPS-DEV-062`, attachment `PPS-DEV-046`, and
  overflow `PPS-DEV-082`. Rendered final/source messages are at
  `outputs/exp-187-vonly-consensus-contract-audit-v1/rendered_inputs/` and were read: both drafts
  are labeled non-source and non-voting; final retains cards, needed metadata/product facts, and
  original source material.
- Exact tokenizer profile is
  `outputs/exp-187-vonly-consensus-admission-audit-v1/profile.json`: dev200 has 430 draft calls
  plus 216 resolver calls (646 total; 11 batch-64 rounds), zero source-document omissions in either
  stage, and a 30,268-token maximum admitted prompt. This is 48.5% more calls than EXP171's 435,
  so it is a runtime-risk diagnostic rather than a speed candidate.
- `pytest -q` passed 149 tests. The next permitted action is one paid fast20 label-quality probe;
  no holdout, dev200, submission, card, prompt, schema, merge, or provider change is authorized.

## Result and decision — 2026-09-10

`outputs/exp-187-vonly-consensus-full-source-fast-panel-c4/` completed 20/20 at macro positive-F1
`.097917`, versus direct complete-source EXP169 `.262500` (`-.164583`). It made 46 draft calls
plus 23 resolver calls (69 total) and elapsed `78.3s` remotely; no draft/final parse error or
recovery occurred. Remote time is not evaluator-vLLM evidence. Its 16 positive labels all have
intentionally blank evidence, producing 16 validation warnings; evidence validity and joint
positive quality are necessarily zero, as declared.

The model-owned resolver did not blindly majority-vote: its labels differ from EXP169 in 18 cells,
the two drafts disagree in four cells, and it generates two v22 positives where both drafts are 0.
That independence is not helpful calibration. It loses TPs across v2/v4/v12/v21/v23/v24 and returns
zero positives for fourteen items; only v1 `.8`, v2 `.4`, v3 `.75`, and v22 `.4` have nonzero F1.
The per-item TP/FP/FN and all changed cells are preserved in `per_item_metrics.csv`, `errors.csv`,
and `predictions.jsonl`.

**Decision: reject EXP187.** Do not run holdout/dev200, change the number/wording of V-only drafts,
or build a Python evidence selector. This directly answers the multiple-V-only hypothesis: in the
only complete-source, model-owned, non-voting resolver test, additional V-only readings sharply
degraded label recall and made runtime worse than EXP171.
