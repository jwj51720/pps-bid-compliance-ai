# dev-wsl branch memo

This memo is the continuing branch-local record for `dev-wsl`. It exists to
keep independent research history out of the shared root `docs/memo.md`, which
remains the common project agreement for `dev` and later merges.

## Branch identity

- Branch: `dev-wsl`
- Fork point from `dev`: `6d93e8cad3d1a959c7b7878864ccefc38cdb29a3`
  (`fix: include raw data and submission artifacts in exports`)
- Research boundary: all new policy exploration, code, candidates, and
  experiment records are under `incubator/`; the root canonical pipeline is
  not an experimental target on this branch.

## Record through 2026-09-07

The complete reviewer-oriented state, commit inventory, submission lineage,
results, rejected hypotheses, known operational mistakes, and continuation
steps are in:

- [`docs/handoff/20260907_004722_dev-wsl_linux_HANDOFF.md`](../../docs/handoff/20260907_004722_dev-wsl_linux_HANDOFF.md)

The central result is the submitted EXP-123 candidate:

- archive: `dist/pps_20260906_233304.zip`
- policy: EXP-120 Gemma V/E path plus source-complete frozen v2/v3/v21 rules
- local dev-200: `0.317797` vs EXP-120 `0.248932`
- public score: pending in this branch record

This is not a promotion claim. The rules were audited on dev-200, so the
submitted public result is the required transfer measurement. Do not create
more dev-derived rules or duplicate submission zips while it is pending.

## Working agreement for subsequent dev-wsl work

1. Add branch-specific research decisions, hypotheses, and rejected paths to
   `incubator/docs/`, not root `docs/memo.md`.
2. Preserve the actual-notice Gemma call, source-substring evidence contract,
   and competition restrictions documented in the shared root guide.
3. Before a new paid experiment, pre-register one semantic change, fixed
   cohort/holdout gates, cost ceiling, and source-evidence validation.
4. Before creating a submission zip, verify that tracked candidate content
   changed; stage and mock-test in a temporary directory only, never at the
   repository root.
5. During a `dev` merge, treat `AGENTS.md` as a shared policy conflict: review
   each rule rather than choosing either file wholesale. Treat `incubator/`
   as additive history; do not import an incubator policy into root canonical
   code without an explicit integration decision.
