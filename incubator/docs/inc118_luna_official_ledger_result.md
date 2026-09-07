# INC-118: Luna + official-law ledger

## Hypothesis

INC-088's full-notice Luna card arm (`.36073` on all dev-200) receives synthesized decision-card text, but not the organizer-provided statutory text. Its dominant failures are conservative false negatives in compositional legal items. Give the same full notice and metadata to the same Luna high setting, but replace the card-only legal context with the archived official-law ledger: profile-selected item summaries plus unchanged official statutory chunks.

This is a single-context change. The model, full document order, metadata, 24-label schema, and `high` reasoning setting are unchanged.

## Design

- Model: `gpt-5.6-luna`, OpenAI Responses API, reasoning `high`.
- Output cap: 8,192, matching the successful INC-088 full-dev run.
- Cohort construction: two disjoint 32-notice cohorts, each with 8 notices from `national`, `local_small`, `local_negotiated`, and `local_general`. Each group is selected by a documented SHA-256 rank before labels are read.
- Comparator: cached INC-088 card-v6 output for precisely the same IDs.
- Every request succeeded (64/64). No request was retried or replaced.

## Results

| Cohort | Card-v6 | Official ledger | Delta |
| --- | ---: | ---: | ---: |
| Initial stratified 32 | 0.25694 | 0.33194 | +0.07500 |
| Disjoint holdout 32 | 0.16468 | 0.26528 | +0.10060 |
| Combined 64 | 0.27585 | 0.40056 | +0.12471 |

The combined score is not an estimate of the public leaderboard and must not be compared directly with dev-200 macro due to a different class mix. The paired improvement repeats in both independent cohorts, which is the evidence for advancing this context branch.

On the combined 64, the official ledger improves v4 (0.50 -> 1.00), v6 (0.00 -> 0.667), v7 (0.00 -> 0.50), v9 (0.00 -> 0.444), v16 (0.00 -> 0.50), v18 (0.00 -> 0.667), and v22 (0.80 -> 1.00). It also introduces false positives in v2, v5, v10, v15, v17, v19, v20, and especially v24. The v24 effect is conceptually separate: it is document-versus-metadata consistency, not statutory applicability. Preserving INC-088's v24 output while taking official-ledger output for v1--v23 gives 0.40350 on these same 64. This merge was defined by item semantics before inspecting holdout labels; it is still a candidate, not a promoted final policy.

## Decision and next BFS

Promote the official-law context as the only current Luna branch. Do not promote individual item cherry-picks from the 64 labels.

1. Confirm the broad policy on a third, disjoint, label-blind profile-balanced cohort before any dev-200 or unlabeled scaling.
2. In that confirmation, compare only three policies fixed now: card-v6, official ledger, and official ledger for v1--v23 plus card-v6 for v24.
3. If the official-law policy wins again, transplant precisely the same fixed legal context into a small Gemma paired test. The notice remains present; no self-label or learned model is involved.
4. Treat v2/v5/v10/v15/v17/v19/v20 false positives as a separate later precision branch. Do not tune them from the two cohorts.

Artifacts: `runs/inc118_luna_official_ledger_stratified32/`, `runs/inc118_luna_official_ledger_holdout32/`, and the two frozen manifests in `data/derived/`.
