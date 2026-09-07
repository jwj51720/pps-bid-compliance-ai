# Incubator Operating Contract

`incubator/` is an isolated research area for the `dev-wsl` branch. Its purpose
is to test a smaller, item-aware compliance approach before any proposal is made
to merge code into the repository pipeline.

## Isolation

- Do not edit, import, or monkey-patch `../src/`, `../scripts/`, `../configs/`,
  `../submission/`, or root `config.yaml` from this directory.
- Treat `../data/raw/open/` as immutable organizer data. Read it by a relative,
  configured path; do not copy it, rewrite it, or use the duplicate organizer
  files under `../data/` as an alternate source.
- Put generated indexes, manifests, self-label records, and temporary data under
  `incubator/data/derived/`. Put each run's prompts, raw responses, predictions,
  metrics, and analysis under `incubator/runs/<experiment_id>/`.
- Generated data, responses, and caches are ignored by this directory's
  `.gitignore`. Source code, configurations, and concise research decisions under
  `incubator/docs/` are tracked.

## Competition Constraints

- Every final evaluation notice must receive at least one successful Gemma call
  that contains its actual notice. Deterministic extraction can schedule or
  correct a decision, but cannot replace that call.
- Do not train or package classifiers, regressors, fine-tunes, LoRA/adapters, or
  learned weights. The only allowed embedding model is the provided BGE-M3.
- Use only organizer-provided notices, metadata, laws, and ministry notices.
  Never recover anonymized identities or fetch external procurement/legal data.
- External LLM self-labeling may use only organizer-provided material (including
  the 20,000 unlabeled notices, supplied laws, and ministry notices). It may
  create static case/RAG assets for final inference. Record input IDs and
  hashes, model, prompt version, parameters, raw output, validation, and
  source-data version.
- Evidence must be an unchanged source-document substring of at most 500
  characters. `v10`, `v11`, `v16`, `v18`, and `v20` always have blank evidence.

## Experimental Discipline

1. Write a one-sentence hypothesis, a fixed cohort, comparator, budget, and
   promotion rule before an API run.
2. Run a mock/input audit first, then a small paid pilot. Never silently change
   more than one material variable in a comparison.
3. Record macro positive-F1, precision/recall/F1 per item, TP/FP/FN, evidence
   validity, token use, request count, wall time, and estimated/actual cost.
4. Inspect every changed positive and a representative sample of unchanged hard
   errors before promotion. A gain that only comes from labels absent in the
   cohort is not a promotion.
5. Promote only predeclared candidates to a dev-200 confirmation. The root
   pipeline remains unchanged until a proposal includes reproducible artifacts,
   runtime estimates for 1,853 notices, and a submission-parity design.

## Cost and Safety

- Read `OPENROUTER_API_KEY` only through the environment; never print, store, or
  commit it. Use OpenRouter only after the mock preflight records exact messages.
- The final runtime must use the fixed Gemma model for at least one actual-notice
  call per notice, but experiments may use an external LLM to create permitted
  offline self-label/RAG assets. BGE-M3, lexical retrieval, metadata, and their
  combinations are all admissible retrieval comparators; measure their value
  rather than imposing a retrieval order in advance.
- Set a request and monetary ceiling in every experiment configuration. Stop on
  the ceiling or a transport/schema failure rate that makes results unreliable.
- Do not make a leaderboard submission from incubator work. A submission is a
  separate, explicit integration and packaging task.
