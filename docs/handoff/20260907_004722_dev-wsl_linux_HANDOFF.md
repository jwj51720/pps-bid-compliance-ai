# dev-wsl branch handoff — 2026-09-07 00:47:22 KST (Linux)

## Purpose and scope

This is the complete handoff for the independent `dev-wsl` research branch
from its branch point through commit `20b9efe`. It is intended for validation
and later integration with `dev`; it does **not** authorize merging incubator
policy into the canonical root pipeline automatically.

The branch was deliberately isolated because the concurrent `dev` line is an
older, independently evolving implementation. All new experimental work lives
under `incubator/`. Root code was not repurposed for these experiments.

## Repository state at handoff

| Field | Value |
|---|---|
| Branch | `dev-wsl` |
| HEAD | `20b9efece639bd716adae9f68d14316786fee981` (`docs: close v9 specification pass`) |
| Upstream | `origin/dev-wsl` at the same commit |
| Local environment | Linux / KST |
| Worktree after this handoff change | Expected to contain only this handoff, the handoff naming-rule update, and the EXP-123 archive-reference correction |
| Secrets/raw data | Not recorded here; `.env` and data payloads remain ignored |

The tracked root policy remains the repository's canonical pipeline. The
incubator is a research sandbox with its own instructions:
[`incubator/AGENTS.md`](../../incubator/AGENTS.md).

## Competition constraints that govern every result

- The final package must make at least one successful local Gemma call with the
  actual notice for each evaluated record.
- Fine-tuning, adapters, learned classifiers/regressors, and alternate learned
  weights are prohibited. Fixed Gemma and BGE are allowed; deterministic,
  source-grounded corrections are allowed.
- Every non-absence evidence string must be an unchanged source-document
  substring of at most 500 characters. Python validation, not LLM assertion,
  is authoritative.
- All 24 decisions use notice documents and metadata. Preserve document order:
  announcement, specification, task instruction, proposal request, exception.
- Local dev-200 is a selection signal, not a test-set estimate. Do not tune
  arbitrary character counts, keyword thresholds, or individual dev IDs.

Primary rule and project references: [`docs/project_description.md`](../project_description.md),
[`docs/project_plan.md`](../project_plan.md), [`docs/memo.md`](../memo.md), and
[`AGENTS.md`](../../AGENTS.md).

## Branch architecture and reproducibility

`incubator/` is self-contained by design. It contains versioned configs,
experiment source, protocols/results, ignored run artifacts, derived research
assets, and isolated submission candidates. It may read the organizer data but
does not modify root pipeline/source files.

Core navigation:

- Research process and pre-registration gates:
  [`incubator/docs/experiment_loop.md`](../../incubator/docs/experiment_loop.md),
  [`incubator/docs/research_experiment_plan.md`](../../incubator/docs/research_experiment_plan.md)
- Full experiment record and decisions:
  [`incubator/docs/leaderboard.md`](../../incubator/docs/leaderboard.md)
- Idea inventory and explicitly rejected/parked ideas:
  [`incubator/docs/idea_notes.md`](../../incubator/docs/idea_notes.md)
- Public-control milestone and branch gates:
  [`incubator/docs/post_exp120_bfs_milestone.md`](../../incubator/docs/post_exp120_bfs_milestone.md)
- Archived historical `dev` materials, kept only as a reference:
  [`incubator/reference/dev_history/`](../../incubator/reference/dev_history/)

Experiment commands and exact inputs are recorded beside each protocol under
`incubator/docs/incNNN_*` and its corresponding ignored
`incubator/runs/incNNN_*/`. Never infer a policy from a run directory alone:
read the protocol, result, config, and metric artifact together.

## Baseline and public-leaderboard calibration

| Policy | Local dev-200 macro positive-F1 | Public score | Interpretation |
|---|---:|---:|---|
| EXP-109 official baseline reproduction | 0.223498 | 0.210360 | Historic calibration only |
| EXP-120: Gemma single V/E, ordered 4,000-char context, card v6 | 0.248932 | 0.244317 | Current public control; local/public gap -0.004615 |
| EXP-123: EXP-120 plus frozen v2/v3/v21 corrections | 0.317797 | pending at handoff | Submitted external generalization test |

EXP-120 is the only policy with an aligned public observation in this branch.
The EXP-123 local gain is promising but was discovered on dev-200; therefore
it must not be represented as a validated hidden-test improvement until the
submitted score arrives.

## Submission lineage and exact audit state

### EXP-120 control

- Submitted archive: `dist/pps_20260905_170543.zip` (ignored artifact).
- Policy: one Gemma V/E call, card v6, ordered 4,000-character notice context,
  Python evidence validation.
- Public score: `0.2443173108`.

### EXP-123 candidate — the currently submitted experiment

- **Only submitted archive:** `dist/pps_20260906_233304.zip`.
- SHA-256:
  `9b28391d63e2f8a4dcf42af8b225de30c3479dce96df310c17572b599e8b0907`.
- Policy: the EXP-120 Gemma path stays mandatory and unchanged; after normal
  finalization, only v2/v3/v21 may be replaced by frozen source-complete
  deterministic predicates. The other 21 V/E pairs remain the EXP-120 result.
- Packaging source:
  [`incubator/submission_candidates/exp123_card_v6_frozen_rules/`](../../incubator/submission_candidates/exp123_card_v6_frozen_rules/)
  and [`incubator/scripts/package_exp123_candidate.py`](../../incubator/scripts/package_exp123_candidate.py).
- Validation: 18-member zip integrity; extracted staged `script.py --mock`;
  49 ordered CSV columns and unique fixture IDs; 20k format audit; evidence
  length and substring validation; two frozen dev folds.
- The separate `pps_20260907_001734.zip` was byte-content-equivalent after
  extraction, was never a new policy, and has been deleted. Do not recreate or
  submit it. The archive dossier now points to the actual submitted file:
  [`incubator/docs/exp123_submission_decision_dossier.md`](../../incubator/docs/exp123_submission_decision_dossier.md).

The user reported that `pps_20260906_233304.zip` has already been submitted.
At handoff, its score was not supplied to this environment. Obtain that exact
score before treating EXP-123 as promoted or rejected.

## Deterministic correction: what is justified, and its limit

EXP-123 uses no character-length or keyword-frequency cutoff. It replaces
three labels only when organizer-law, metadata/source-role, and complete-source
conditions hold:

| Item | Frozen condition | Dev-200 rule result | 20k activation |
|---|---|---:|---:|
| v2 | organizer 230M legal amount + below-threshold estimate + explicit bidder-performance eligibility clause | 7 TP / 0 FP / 0 FN | 0.850% |
| v3 | one explicit qualification-performance amount at least raw allocation budget | 8 / 0 / 0 | 0.410% |
| v21 | explicit joint-contract share below statutory default; exclude divided-performance contracts | 6 / 0 / 0 | 0.045% |

All positive rule evidence is source unchanged and no longer than 500
characters. The all-dev composition rises from `0.248932` to `0.317797`
(+`0.068865`). It also rises independently in the pre-existing folds:
`0.262247 -> 0.319192` and `0.222421 -> 0.305754`.

This is stronger than a local prompt tweak but **not** a hidden-test proof:
the rules were identified using dev labels. Do not add any new dev-derived
rules merely because an error pattern looks plausible. Detailed evidence:
[`incubator/docs/inc123_exp120_frozen_rule_composition_result.md`](../../incubator/docs/inc123_exp120_frozen_rule_composition_result.md),
[`incubator/docs/inc124_exp123_unlabeled_format_audit_result.md`](../../incubator/docs/inc124_exp123_unlabeled_format_audit_result.md),
[`incubator/docs/inc130_exp123_frozen_fold_stability_result.md`](../../incubator/docs/inc130_exp123_frozen_fold_stability_result.md).

## High-value research findings

### Luna is a teacher/diagnostic ceiling, not a submission replacement

Using permitted Luna calls on competition-provided materials, the official
legal-ledger protocol scored `0.427366` on dev-200; its historical composition
with the same three frozen rules scored `0.462222`. This proves useful
conditional-law reasoning can be elicited, but it is not a valid submission
path because the submission requires local Gemma inference. It is also not a
license to distill labels into a trained model.

References: [`incubator/docs/inc125_luna_full_dev_official_ledger_result.md`](../../incubator/docs/inc125_luna_full_dev_official_ledger_result.md),
[`incubator/docs/inc126_luna_frozen_rule_composition_result.md`](../../incubator/docs/inc126_luna_frozen_rule_composition_result.md).

### Rejected or closed directions

The following are closed unless genuinely new external evidence changes their
premises. Do not repeat them on another convenient cohort.

| Direction | Result / reason |
|---|---|
| V-only output | INC-121 recall collapse; cannot provide submitted evidence |
| Source-anchor output | Semantic positive-without-anchor failures |
| Compact/full legal-summary injection | INC-122 regression; profile-gated transfer also closed by INC-128 |
| Full-document split/OR merge | INC-018 severe false-positive explosion |
| Generic BGE/case RAG | insufficient retrieval/evidence recall; template overlap is non-discriminative |
| Global extract-then-adjudicate or e-prime | incomplete/unstable transport and lower result |
| Gemma operational-contract rewrite | INC-127 -0.006944 on fresh paired pilot |
| Gemma second source-grounded audit | INC-129 no macro gain; one new v21 false positive |
| v9 specification-only second pass | evidence/document topology incomplete and generic identifier cue fires in 95.4% of negatives |
| Broad deterministic-rule expansion | formal observability audit leaves only already-used v2/v3/v21 useful; no automatic regional/product rule |

The supporting documents are linked in the leaderboard and, for the latest
closures, [`incubator/docs/inc127_gemma_operational_contract_pilot_result.md`](../../incubator/docs/inc127_gemma_operational_contract_pilot_result.md),
[`incubator/docs/inc128_luna_ledger_profile_stability_result.md`](../../incubator/docs/inc128_luna_ledger_profile_stability_result.md),
[`incubator/docs/inc129_gemma_source_grounded_self_audit_result.md`](../../incubator/docs/inc129_gemma_source_grounded_self_audit_result.md), and
[`incubator/docs/inc131_v9_specification_second_pass_feasibility.md`](../../incubator/docs/inc131_v9_specification_second_pass_feasibility.md).

## Commit inventory since `dev`

| Commit | Subject | Responsibility |
|---|---|---|
| `4dc5ffc` | `feat: add isolated incubator research foundation` | isolated research loop, data/runs structure, early baselines |
| `bb25c1a` | `feat: add source-grounded rule and retrieval audits` | audited retrieval/rule/evidence research suite |
| `17b71c2` | `feat: add Luna teacher and legal-ledger research` | teacher protocol, historical references, error analyses |
| `606d3f1` | `chore: stage EXP-120 submission candidate` | isolated EXP-120 staging/package path |
| `c53ae05` | `docs: record EXP-120 submission milestone` | public calibration and BFS gates |
| `158947d` | `docs: record research reset and historical controls` | reset rules and prior-art audit |
| `a7524a5` | `exp121: record output and legal-context branch results` | V-only/anchor/legal-summary branch closures |
| `31c83f2` | `exp123: package frozen-rule submission candidate` | EXP-123 candidate and composition record |
| `76930a3` | `fix: bound EXP-123 rule evidence windows` | evidence length compliance |
| `14467a5` | `exp125: confirm Luna ledger policy` | Luna teacher ceiling and transfer probes |
| `3ea4e70` | `docs: record INC-125 to INC-127 results` | leaderboards/results update |
| `ee34801` | `docs: record v24 alignment diagnostic` | v24 diagnosis |
| `e30ab02` | `docs: close profile-gated ledger transfer` | closes unsupported profile branch |
| `0a743ec` | `exp129: reject Gemma source audit pass` | two-pass self-audit closure |
| `4cdec82` | `docs: verify EXP-123 fold stability` | fold-level rule audit |
| `0b1b325` | `docs: add EXP-123 submission dossier` | package decision dossier |
| `20b9efe` | `docs: close v9 specification pass` | v9 second-pass feasibility closure |

## Operational mistakes already corrected

1. A duplicate `pps_20260907_001734.zip` was produced by re-running the
   package script without any policy/content change. Its member contents were
   identical to the actual submitted EXP-123 zip. It was deleted. Do not make
   a new submission archive unless a source/config/manifest change requires
   one; record the exact archive SHA at creation.
2. During staging inspection, submission files were accidentally extracted at
   repository root, overwriting root `requirements.txt` and creating
   `script.py`, `runtime_config.json`, `decision_cards_v6.json`,
   `MANIFEST.json`, and `src/frozen_rules.py`. They were removed and the root
   `requirements.txt` restored from Git. Extract/test submission archives only
   in a dedicated temporary directory or within their `incubator` candidate
   directory. Never unpack a zip at repository root.

## Exact continuation sequence

1. Check the DACON result for **only** `pps_20260906_233304.zip`; record its
   public score in the dossier and leaderboard.
2. Compare it to EXP-120's `0.244317` using the predeclared decision: a clear
   improvement supports the three-rule transfer; a material regression rejects
   it and closes additional dev-derived rule expansion. Do not manufacture a
   duplicate zip or alter rules before this measurement.
3. If a new Gemma branch is proposed, first add a protocol with one semantic
   change, a fixed label-blind stratified exploration cohort, an independent
   holdout, cost/runtime cap, evidence contract, and promotion threshold.
4. The only not-automatically-closed broad direction is a source-preserving
   teacher-record retrieval input. Before any paid Gemma call, audit Luna
   ledger records for a label-blind retrieval key and verify retrieved records
   cannot replace raw-source evidence. Generic case RAG and global e-prime are
   explicitly not sufficient.
5. For a future submission: build from the isolated candidate, stage/extract
   under a temporary directory, run the exact staged `script.py --mock`,
   validate CSV schema/evidence, produce one timestamped zip, SHA it, and add
   a dossier record before upload.
6. When merging `dev`, treat this branch as an additive `incubator/` history.
   Inspect path conflicts and runtime interface compatibility first. Do not
   overwrite root canonical policy or silently import experimental submission
   code.

## Handoff naming rule update and branch-record separation

The mandated format is now:

```text
docs/handoff/YYYYMMDD_HHMMSS_<branch>_<mac-or-linux>_HANDOFF.md
```

The shared [`AGENTS.md`](../../AGENTS.md) was updated to make the branch
component mandatory. Shared [`docs/memo.md`](../memo.md) remains unchanged;
branch-local history belongs in
[`incubator/docs/dev-wsl_memo.md`](../../incubator/docs/dev-wsl_memo.md).
