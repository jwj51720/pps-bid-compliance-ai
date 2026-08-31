# Repository Guidelines

## Sources of Truth

Read `docs/project_description.md`, `docs/project_plan.md`, and `docs/memo.md` before changing the pipeline or submission package. They define the competition rules, current structure, and team agreements. When `memo.md` or another policy/architecture document changes, review this guide in the same change and synchronize any affected instructions.

The goal is competition performance and reproducibility, not a production service. Favor direct, inspectable code and avoid speculative abstractions.

## Project Structure

Use the deliberately small planned layout:

```text
config.yaml           canonical final experiment/submission policy
configs/              versioned and historical experiment parameters
data/raw/             organizer-provided data
data/derived/         generated labels, indexes, and knowledge files
src/                  shared pipeline and evaluation code
src/external/         OpenRouter, OpenAI, and local Gemma adapters
scripts/              experiment and packaging entry points
submission/           thin DACON entry point and requirements
outputs/<exp_id>/      isolated experiment artifacts
dist/                 ignored submission zips and shareable artifact archives
docs/                 rules, decisions, and research notes
```

Keep `src/` flat initially (`pipeline.py`, `data.py`, `prompt.py`, `submission.py`, `evaluate.py`). Add `rules/`, `retrieval/`, or `knowledge/` only after experiments justify the separation. Root `config.yaml` is the sole canonical final policy; every non-final or historical experiment config belongs under `configs/`. Local experiments and `submission/script.py` must call the same pipeline; differences belong in input paths, LLM provider, configuration, and whether evaluation runs. The submission entrypoint must inject the evaluation runner's `count_tokens()` into that shared pipeline. Never fork or copy an official baseline into a submission archive as a shortcut: package from the tracked `submission/script.py`, `submission/runtime_config.json`, and `src/`, then mock-test the exact staged entrypoint.

The shared pipeline owns prompt construction, token admission, overflow splitting, pass-result merge, parsing, evidence resolution, and CSV validation. A retrieved official-reference chunk is fixed context: include it verbatim in every final message and count it before admitting/splitting notice documents; never split or silently drop it. If fixed context plus the non-document prompt exceeds budget, fail admission and reduce retrieval upstream. Runtime adapters own only model transport and scheduling: experiments use the configured remote provider plus evaluation/checkpointing; submissions use offline vLLM, `PPS_*` paths, and the fixed batch policy. Keep every submission-default value in the tracked submission entrypoint/config and regression-test that staged zip, not a surrogate script.

## Environment and Commands

Use one repository virtual environment and a mandatory `requirements.txt`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/run_experiment.py --config config.yaml
python -m pytest
```

Profile the official files with `python scripts/profile_data.py --config config.yaml`. Use `--mock` for a no-network pipeline smoke test and rerun the same experiment command to resume an interrupted checkpoint. Use `configs/<experiment>.yaml` for a historical or alternate experiment; never overwrite root `config.yaml` to do so. The ignored `.env` stores only `OPENROUTER_API_KEY`. Keep provider calls inside `src/external/`.

## Competition-Critical Implementation Rules

- Produce all 24 binary decisions from each notice's documents **and** metadata. Every evaluated notice must make at least one successful Gemma call containing the actual notice.
- Fine-tuning, LoRA/adapters, separate learned classifiers/regressors, alternate embedding models, and trained weights are prohibited. The fixed evaluation models are Gemma 4 26B A4B IT and `BAAI/bge-m3`; deterministic rules and corrections are allowed.
- External LLMs may create self-labels only from competition-provided material. Record model, prompt, generation settings, inputs, and outputs so the process is reproducible.
- Evidence must be an unchanged source-document substring of at most 500 characters. `e10`, `e11`, `e16`, `e18`, and `e20` are always blank. Resolve and validate evidence in Python rather than trusting generated paraphrases.
- Read submission paths from `PPS_DATA_DIR`, `PPS_OUTPUT_DIR`, `PPS_MODEL_DIR`, and `PPS_EMBED_DIR`; never hard-code local paths. Inference has no internet access.
- Preserve the document order `공고문 → 규격서 → 과업지시서 → 제안요청서 → 예외공표서`. If the token budget cannot hold every complete document, use additional notice-level passes that retain the notice and cover omitted document types; combine a positive finding from either pass and retain evidence from its source document.

## Experiments and Testing

Name runs descriptively, such as `exp005_v3_rule`. Each `outputs/<exp_id>/` should preserve the exact config, predictions/submission, metrics, per-label results, errors, runtime, logs, and a short reproduction note. Compare the mean of the 24 positive-class F1 scores and report precision/recall/F1 per label; do not rely on aggregate accuracy or assume dev class frequencies match test.

When asked to export work for another environment, run `python scripts/export_artifacts.py`. It writes a `tar.xz` below `dist/archives/` that extracts into one top-level directory and includes the source, configs, docs, `data/derived/`, and `outputs/` needed to continue work. Exclude `data/raw/`, which will be restored independently from the original source, as well as `dist/`, `submission/build/`, caches, and machine metadata. Actual files under both data directories stay ignored by Git, while `.gitkeep` preserves their layout. Write submission zips directly under `dist/`.

Use `pytest` with `tests/test_<module>.py` and `test_<behavior>`. Mock remote LLM calls. Test parsing, rules, schema-constrained output, malformed/empty structured-output recovery, metrics, evidence substring checks, and missing-document behavior. Regression-test corrected false positives and negatives.

Before packaging, validate `output/submission.csv`: exactly 49 ordered columns (`id`, `v1`-`v24`, `e1`-`e24`), unique complete IDs, integer 0/1 labels, UTF-8/NFC text, valid evidence, and the expected row count. The self-contained submission archive must include `script.py`, `requirements.txt`, code, and only permitted static assets; name it `pps_YYYYMMDD_HHMMSS.zip` (30 characters or fewer) and verify the 2 GB compressed, 8 GB extracted, 10-minute install, and 2-hour inference limits.

## Style, Commits, and Data Safety

Use Python, four-space indentation, PEP 8, type hints at module boundaries, `snake_case` functions/files, `PascalCase` classes, and `UPPER_SNAKE_CASE` constants. Prefer focused functions over factories, registries, manager classes, or catch-all `utils.py` files.

When explicitly asked to commit, inspect all changes first and split sequential commits by responsibility. Use concise imperative subjects; experiment commits may use `exp005: add v3 threshold rule`. Pull requests should state the hypothesis, validation commands, metric/runtime deltas, and any rule or packaging impact.

Never commit API keys, `.env`, competition data, generated submissions, caches, or prohibited model weights. Do not maintain a tracked environment template; document variable names without placeholder files when needed.
