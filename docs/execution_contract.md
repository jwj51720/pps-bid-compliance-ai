# Execution Contract

This document fixes the boundary between common inference logic and runtime
adapters. It applies to every future experiment and submission.

## Shared pipeline (`src/`)

- Load and NFC-normalize notices, preserve document order, and include metadata.
- Construct the 24-item prompt and JSON schema.
- Include every selected official-reference chunk verbatim in the final system
  prompt, then count the final chat prompt. Admit one full pass or create
  token-admitted ordered split passes of notice documents only. If the fixed
  prompt itself cannot fit, fail clearly; retrieval must reduce its selected
  chunks rather than truncate a reference.
- Merge pass labels with OR; retain the earliest positive pass evidence.
- Parse structured output, resolve evidence to a source substring, enforce the
  500-character and absence-item rules, and construct/validate the 49-column CSV.
  An unusable model candidate is recorded with its raw response and contributes
  an all-negative result for that pass; it must never abort rows already inferred.

## Experiment adapter

- Reads root `config.yaml` only for the canonical final policy, or an explicitly
  named versioned YAML under `configs/` for a historical/alternate experiment.
- Uses OpenRouter or a mock client, checkpoints raw responses and usage, and
  evaluates only when local labels are configured.
- May set concurrency and retry policy, but cannot change shared judgment logic.

## Submission adapter

- Reads only `PPS_DATA_DIR`, `PPS_OUTPUT_DIR`, `PPS_MODEL_DIR`, and optionally
  `PPS_EMBED_DIR`; it never uses network access or local absolute paths.
- Uses offline vLLM with the fixed Gemma at `PPS_MODEL_DIR`.
- Reads the packaged `runtime_config.json`; its prompt-policy values must match
  root `config.yaml` before packaging.
- Injects `runner.count_tokens()` into the shared pipeline.
- Schedules prepared notice/pass messages in vLLM batches of **128 by default**.
- Validates each structured candidate before finalization and retries malformed
  candidates once individually. It logs the retry count and any pass that still
  required the shared all-negative fallback.
- Never evaluates against labels, writes checkpoints, or changes decisions.

## Packaging gate

`scripts/make_submission.py` must package `submission/script.py`,
`submission/runtime_config.json`, `submission/requirements.txt`, and the shared
`src/` modules, never a copied baseline. Submission zips go under `dist/`; data
and output archives go under `dist/archives/`. Use `scripts/export_artifacts.py`
for a portable archive: it includes source/config/documentation, raw and derived
data, outputs, staged submission builds, and submission zips; it excludes `.env`,
Git metadata, environments/caches, and `dist/archives/` to avoid recursive
archives, and extracts into one top-level directory. Before handoff, run the staged zip's
exact `script.py --mock` against the official 10-notice fixture and validate the
resulting CSV's rows, IDs, order, and 49 columns.

Submission archive names use `pps_YYYYMMDD_HHMMSS.zip` in local execution time.
This keeps each archive below DACON's 30-character filename limit while making
the creation time explicit.
