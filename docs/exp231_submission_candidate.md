# EXP231 local-best submission candidate

## Packaged policy

`dist/pps_20260914_152230.zip` reproduces the current best dev200 composition,
not a new prompt experiment:

1. EXP208 runs all v1-v24 with `relation_checklist_after_source_v1`, complete
   corrected inputs, decision cards v10, and full-source exact-token admission.
2. EXP221 independently runs v4 only with `complete_fact_subset_v1`, baseline
   prompting, and decision cards v11. Its v4/e4 replaces EXP208 v4/e4.
3. EXP231 independently runs v5 only with `complete_fact_subset_v1`, baseline
   prompting, and decision cards v12. Its v5/e5 replaces the already composed
   output's v5/e5.

This is field replacement, not OR merge. No other item is taken from a
specialist. All three request sets are prepared and executed as global vLLM
batches of 128.

## Local evidence

- EXP208 dev200 Macro positive-F1: `0.2929590948553797`.
- EXP208 + EXP221(v4): `0.3061169895922218`.
- EXP208 + EXP221(v4) + EXP231(v5): `0.32926513774037`.
- Final composed evidence validity: `0.8047337278106509`.
- EXP208 exact dev200 topology: 219 admitted source-pack calls.
- EXP221 exact dev200 topology: 200 calls; 200/200 records single-pass.
- EXP231 exact dev200 topology: 200 calls; 200/200 records single-pass.
- Total matched dev200 topology: 619 Gemma calls. Batch size changes scheduling,
  not this call count.
- Specialist admission audits retain all 374/374 source documents with zero
  source, metadata, active-card, organizer-semantics, or over-budget omissions.
  The EXP208 input audit likewise retained 374/374 source documents with zero
  semantic-input omissions.

## Package verification

- Canonical and offline runtime policies were compared by
  `scripts/make_submission.py` before packaging.
- The archive contains cards v10, v11, v12 and
  `competition_products_v1.json`.
- The exact extracted archive was run with `--mock --limit 10` against organizer
  format input. It executed the base, v4, and v5 request sets, produced 10 unique
  rows and exactly 49 columns, and passed the shared evidence/ID validation with
  zero warnings.
- Focused submission and packaging tests: 15 passed.
- A real GPU/vLLM smoke was not available in this environment.

## Runtime limitation

This package intentionally prioritizes the best verified local score requested
for submission. Its 619-call matched dev200 topology is higher than both prior
submission candidates that exceeded the 120-minute evaluator limit. Global
batching at 128 is implemented, but does not reduce calls or guarantee that this
candidate finishes within the public evaluator limit.
