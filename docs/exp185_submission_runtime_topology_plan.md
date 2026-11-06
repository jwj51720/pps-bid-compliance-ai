# EXP185 — EXP171 submission runtime topology audit

작성일: 2026-09-10 (dev / mac)

## Purpose

EXP171 is the local quality incumbent, but its 435 dev200 calls and OpenRouter wall time do not
prove the evaluator's vLLM throughput. Before spending on another quality topology, measure the
exact tokenizer-admitted message count and token burden on the organizer test input using the same
shared message construction and the submission runtime policy.

This is a no-provider, no-label, no-prediction runtime audit. It does not claim an evaluator
duration or public score. It reports the quantities a future GPU smoke must validate: stage-1
source packs, stage-2 final packs after a schema-sized navigation ledger, per-stage prompt-token
distribution, document-type coverage, and batch-64 request counts.

## Fixed policy

The audit uses `config.yaml` / `submission/runtime_config.json` EXP171 policy without changing
cards v6, product facts, metadata rendering, source admission, inventory schema, final V/E schema,
merge, or batch size. It profiles the organizer `test.jsonl.gz` only; it must not read labels or
send provider requests.

For final admission it records both:

1. empty navigation, which isolates base full-source packing; and
2. a schema-sized synthetic upper ledger (7 categories × 3 source-labelled excerpts × 360 chars),
   which bounds final context expansion without pretending synthetic text is quality evidence.

Actual saved dev inventory remains a separate descriptive scenario and cannot be projected to test
notices.

## Gates and interpretation

- Exact Gemma chat-template tokenizer only; every document must remain covered in stage 1 and final.
- Report call counts, batch-64 rounds, token quantiles/max, and source omissions by document type.
- Do not execute vLLM or a provider on this macOS machine. A pass means only admission/topology
  evidence, never two-hour compliance.
- If schema-upper calls or tokens create a materially larger topology than the documented dev200
  projection, freeze new multiplicative experiments and require evaluator GPU smoke before any
  further submission candidate promotion.

## Result — 2026-09-10

`scripts/profile_source_first_full_final.py` now accepts an explicit organizer-format input path
without mutating the policy config, and records exact stage/final token summaries plus batch rounds.
It was run against `data/raw/open/data/test.jsonl.gz` using root `config.yaml` and batch size 64;
the artifact is `outputs/exp185-submission-runtime-topology/test_profile.json`.

The locally supplied `test.jsonl.gz` contains **10 organizer-format records**, so it is a staging
sample rather than evidence about the evaluator's full hidden set. On that sample, stage 1 has 11
token-admitted packs and final has 11 packs: 22 calls, one batch-64 round per stage, and zero source
document omissions in either stage. Empty-navigation final prompt tokens total 185,643 (p50 16,691,
max 24,067); the schema-upper synthetic ledger totals 228,070 (p50 20,548, max 27,924). Stage-1
tokens total 141,698 (p50 12,704, max 20,063).

The schema upper ledger did not create an additional final pack on this small sample. This says only
that the exact message construction and admission work for these 10 records. It does **not** prove
2-hour evaluator compliance, vLLM throughput, hidden-test call count, or public quality. No GPU,
vLLM, provider, labels, or prediction was used. The next runtime evidence must be an evaluator-GPU
smoke using the actual mounted input; until then, no new multiplicative quality topology is justified.
