# Repository Guidelines

## Sources of Truth

Read `docs/project_description.md`, `docs/project_plan.md`, and `docs/memo.md` before changing the pipeline or submission package. They define the competition rules, current structure, and team agreements. When `memo.md` or another policy/architecture document changes, review this guide in the same change and synchronize any affected instructions.

The goal is competition performance and reproducibility, not a production service. Favor direct, inspectable code and avoid speculative abstractions.
Do not generalize a suspected merge or prompting issue into a multi-item schema, rule, or extra-call framework without first showing that the item’s truth condition cannot be represented by the existing pipeline. Start with the smallest affected item and validate its accuracy, malformed-output rate, and runtime before changing the canonical policy.
Before a paid experiment, verify that every component required by its stated hypothesis is implemented and selected by the experiment config; validate source coverage/provenance, exact tokenizer admission, mock execution, and isolated output paths. Label an intentionally partial run as a diagnostic probe, never as the result of the complete strategy.
Before a paid prompt experiment, export and read the exact rendered system/user messages for at least: one short complete notice, one truncated/overflow notice, and one notice with attachments. Record those paths and the human review conclusion in the experiment plan; do not rely on config fields or prompt source alone.
Before a paid prompt experiment, perform a separate **semantic-input contract** review for every active v item. The review must trace its applicability facts, 1-condition, material 0-condition/exception, required notice document type, and required metadata/organizer-CSV fact to an organizer-provided source and an exact span in the rendered message. A tokenizer-admitted, schema-valid prompt is not complete merely because it renders; do not pay for a run while an active item has only an item name, vague note, or an untraced condition.
For an ablation, declare `experiment.base_config` and `experiment.allowed_policy_changes`, then run `scripts/preflight_experiment.py` before the paid call. It must find no undeclared effective prompt, LLM, or grouped-execution change. Put grouping/reference execution in versioned config (`grouped_run`), never only in a remembered CLI command. An invalidated config is audit-only and must not be runnable.
Use the versioned `configs/dev_fast_panel_v*.json` local fast cohort rather than file-order first-N records. A fast-panel result ranks candidates only; do not promote a canonical policy without dev-200 confirmation.

## Project Structure

2026-09-21 이후 active code는 clean-room layout만 사용한다:

```text
experiments/manifests/ immutable clean experiment manifests
data/raw/             organizer-provided data
data/derived/         generated labels, indexes, and knowledge files
src/pps_ai/            the only active import root
scripts/              clean entry points only
legacy/pipeline_v1_20260921/ archived old src/scripts/tests/submission
outputs/<exp_id>/      isolated experiment artifacts
dist/                 ignored submission zips and shareable artifact archives
docs/                 rules, decisions, and research notes
```

Every file that existed under the old `src/` is legacy. It may be read for analysis, but active code must
never import it, add it to `sys.path`, or expose compatibility shims. Pytest must not collect the legacy
suite. New code imports only `src.pps_ai`; the hash-pinned L41 artifact is loaded through the isolated
frozen-reference loader. `legacy/pipeline_v1_20260921/` is not runnable product code.

The migration is still pre-submission: root `config.yaml` and the archived submission package describe the
old policy and are historical only. Until a clean `submission/` adapter is built and exact staged mock-tested,
there is no canonical submission candidate. Clean experiments use fully resolved manifests under
`experiments/manifests/`.

The shared pipeline owns prompt construction, token admission, overflow splitting, pass-result merge, parsing, evidence resolution, and CSV validation. A retrieved official-reference chunk is fixed context: include it verbatim in every final message and count it before admitting/splitting notice documents; never split or silently drop it. If fixed context plus the non-document prompt exceeds budget, fail admission and reduce retrieval upstream. Runtime adapters own only model transport and scheduling: experiments use the configured remote provider plus evaluation/checkpointing; submissions use offline vLLM, `PPS_*` paths, and the fixed batch policy. Keep every submission-default value in the tracked submission entrypoint/config and regression-test that staged zip, not a surrogate script.

## Environment and Commands

Use one repository virtual environment and a mandatory `requirements.txt`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/run_clean_reference_baseline.py --config experiments/manifests/<manifest>.json
python -m pytest
```

Use `--mock` for a no-network clean-pipeline smoke test and rerun the same command to resume an interrupted
checkpoint. Do not invoke archived `legacy/.../scripts`. The ignored `.env` stores only
`OPENROUTER_API_KEY`. Keep provider calls inside `src/pps_ai/runtime/`.

## Competition-Critical Implementation Rules

- Produce all 24 binary decisions from each notice's documents **and** metadata. Every evaluated notice must make at least one successful Gemma call containing the actual notice.
- Fine-tuning, LoRA/adapters, separate learned classifiers/regressors, alternate embedding models, and trained weights are prohibited. The fixed evaluation models are Gemma 4 26B A4B IT and `BAAI/bge-m3`; deterministic rules and corrections are allowed.
- External LLMs may create self-labels only from competition-provided material. Record model, prompt, generation settings, inputs, and outputs so the process is reproducible.
- Evidence must be an unchanged source-document substring of at most 500 characters. `e10`, `e11`, `e16`, `e18`, and `e20` are always blank. Resolve and validate evidence in Python rather than trusting generated paraphrases.
- Read submission paths from `PPS_DATA_DIR`, `PPS_OUTPUT_DIR`, `PPS_MODEL_DIR`, and `PPS_EMBED_DIR`; never hard-code local paths. Inference has no internet access.
- Preserve the document order `공고문 → 규격서 → 과업지시서 → 제안요청서 → 예외공표서`. If the token budget cannot hold every complete document, use additional notice-level passes that retain the notice and cover omitted document types; combine a positive finding from either pass and retain evidence from its source document.
- Root `config.yaml`, EXP171 source-first/full-final, adaptive `single`, and `full_split_merge` are
  historical legacy policies. Do not load them from active code. Reintroduce a policy only as a fully
  resolved clean manifest with explicit item owners, then implement it under `src/pps_ai` without importing
  its legacy implementation.
- When `prompt.strict_document_evidence: true` is used with `full_split_merge`, every non-absence positive must quote an unchanged substring from that pass's target source-document fragment—not the announcement anchor, metadata, reference, or another document. The pipeline must downgrade a positive without such evidence to 0 before OR merging; the prompt must state this contract clearly.
- In `full_split_merge`, absence items (`v10`, `v11`, `v16`, `v18`, `v20`) are the logical inverse of a document-level presence check. With `prompt.absence_detection_strategy: per_pass_and`, their final violation is 1 only when every document pass returns absence (1); non-absence items retain OR merging. Do not apply the non-absence evidence gate to absence items.
- `data/derived/decision_cards_v*.json` is the item-table-linked prompt-policy artifact. It may make 1/0 conditions explicit but must not invent thresholds, product status, or exceptions; those facts require organizer-provided law/notice data. Preserve prior card versions for experiment reproduction. When enabled, experiments and submission must read the same card file, and submission packaging must include and verify it.
- The canonical prompt knowledge policy is **cards, not law-reference context**: do not inject raw laws, article excerpts, or separately summarized legal-reference bundles into the model prompt. Review organizer-law material offline with source provenance, then encode only the compact, item-specific applicability conditions, numeric thresholds, periods, and major exceptions in versioned decision cards. Prompt the model as a legal-compliance expert to apply those cards carefully to actual notice text and metadata, without converting uncertainty into an automatic positive.
- Canonical model-message order is: (1) legal-compliance role and decision principles, (2) the versioned output contract for V-only or V+E, (3) cards for the active v items, (4) only the human-readable metadata and organizer-CSV facts needed for those items, then (5) actual notice documents. Do not dump raw metadata JSON, internal codes/status keys, a 20,000-notice corpus, or law-reference text into the model context. Notice documents remain the only source for actual restriction/evidence text.
- `data/derived/competition_products_v1.json` is an organizer-CSV exact-code index. Preserve its raw matched/not-matched/unknown fact for audit, but render only concise Korean applicability text into the LLM message; never expose implementation status keys or code arrays as prompt instructions. When enabled, experiments and submission must read and package the same index. The lookup is not evidence.
- A matched competition-product row is not automatically an applicable product when the organizer CSV row has a `특이사항`. A condition-aware candidate must preserve that row text and human-readable code provenance through the fact/renderer path, then let Gemma compare the condition and actual purchased item; Python must not convert the row condition into a label. Keep the historical names-only renderer explicitly versioned so old experiments remain reproducible.

## Experiments and Testing

Name runs descriptively, such as `exp005_v3_rule`. Each `outputs/<exp_id>/` should preserve the exact config, predictions/submission, metrics, per-label results, errors, runtime, logs, and a short reproduction note. Compare the mean of the 24 positive-class F1 scores and report precision/recall/F1 per label; do not rely on aggregate accuracy or assume dev class frequencies match test.

The former exporter is archived under legacy and must not be invoked. Before the next export request,
implement a clean exporter under active `scripts/` with the same safety contract: one top-level `tar.xz`,
include source/manifests/docs/raw+derived data/outputs/submission artifacts, and exclude `.env`, Git metadata,
virtual environments, caches, machine metadata, and `dist/archives/` itself.

Use `pytest` with `tests/test_<module>.py` and `test_<behavior>`. Mock remote LLM calls. Test parsing, rules, schema-constrained output, malformed/empty structured-output recovery, metrics, evidence substring checks, and missing-document behavior. Regression-test corrected false positives and negatives.
When changing a response format, test that the intended semantic contract is unchanged: the same evidence gate, merge rule, cards, retrieval selection, and final labels must remain unless each is explicitly declared as a separate policy change. A serialization-only experiment may alter only JSON shape/parsing, never Python label overrides.

Before packaging, validate `output/submission.csv`: exactly 49 ordered columns (`id`, `v1`-`v24`, `e1`-`e24`), unique complete IDs, integer 0/1 labels, UTF-8/NFC text, valid evidence, and the expected row count. The self-contained submission archive must include `script.py`, `requirements.txt`, code, and only permitted static assets; name it `pps_YYYYMMDD_HHMMSS.zip` (30 characters or fewer) and verify the 2 GB compressed, 8 GB extracted, 10-minute install, and 2-hour inference limits.

For every submission candidate, record the exact tokenizer-admitted document-context count by document type and the resulting call count after item grouping (`contexts × groups`). Batch size does not reduce that total. Treat full-document splitting plus v-item grouping as a runtime-risk ablation, not a default; retain a single-call/adaptive-overflow baseline and require evidence of both quality and runtime benefit before submitting the multiplicative design.

## Style, Commits, and Data Safety

Use Python, four-space indentation, PEP 8, type hints at module boundaries, `snake_case` functions/files, `PascalCase` classes, and `UPPER_SNAKE_CASE` constants. Prefer focused functions over factories, registries, manager classes, or catch-all `utils.py` files.

When explicitly asked to commit, inspect all changes first and split sequential commits by responsibility. Use concise imperative subjects; experiment commits may use `exp005: add v3 threshold rule`. Pull requests should state the hypothesis, validation commands, metric/runtime deltas, and any rule or packaging impact.

When explicitly asked to leave a handoff, create `docs/handoff/YYYYMMDD_HHMMSS_<branch>_<mac-or-linux>_HANDOFF.md` using the current branch name, local environment, and current local timestamp. A handoff records the day's changes and commits, experiments/configs/results, reasoning and rejected assumptions, current canonical-versus-experiment policy status, exact continuation steps, and links to relevant tracked files or ignored output/data artifacts. It must be sufficient for another environment to continue without repeating known mistakes. Keep it free of secrets and raw competition data. Keep branch-local experiment history out of shared `docs/memo.md`; write it under that branch's isolated experiment area (for example, `incubator/docs/<branch>_memo.md`). When merging a conflict in this shared guide, compare each policy rule with both branches and explicitly preserve or re-ratify it; never resolve it wholesale or automatically promote an experimental policy.

Never commit API keys, `.env`, competition data, generated submissions, caches, or prohibited model weights. Do not maintain a tracked environment template; document variable names without placeholder files when needed.
