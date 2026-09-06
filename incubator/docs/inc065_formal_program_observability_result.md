# INC-065: Formal Legal-Program Observability Map Result

## Result

This all-item, no-API audit applies only necessary observability conditions:
every required metadata field must be populated for all notices, and every
positive must have a nonempty organizer evidence value contained in one
selectable unchanged source line.  It does not use any label pattern to write
a condition, and it does not claim that satisfying these conditions proves a
legal predicate.

| Family | Items | Eligible for a new formal-program audit | Interpretation |
|---|---|---|---|
| Eligibility/performance | v1–v4 | v2, v3 | Both are already the proven rules in INC-040/036. v1/v4 lack complete positive evidence observability. |
| Regional restriction | v5–v8 | none | Region metadata is populated for only 43.5% where a region list is required, and evidenced-positive coverage is incomplete except v7; no complete general program follows. |
| Specification/economic restriction | v9 | none | Only 3/6 positives have nonempty line-contained organizer evidence. |
| Product/applicability | v10–v18 | none | Exact product metadata exists in 39.0% of notices, and most items have no nonempty organizer positive evidence. This confirms that absent code is an unknown state, not a rule input. |
| Timing/procedure | v19–v23 | v22 | v22 is already 5 TP / 1 FP (F1 0.909) in INC-041. v19/v21 lack complete evidence observation; v20 has no project-state metadata; v23 loses one evidence line. |
| Cross-source consistency | v24 | none | Only 28.5% of notices have all listed metadata counterparts, and positive evidence is incomplete. |

The raw rows are in
`incubator/runs/inc065_formal_program_observability_map/report.json`.

## Decision

**Close broad deterministic legal-program expansion.**  The only newly
eligible item, v22, has at most one visible false positive to correct and is
not a route to the required Macro-F1 gain.  v2/v3 are already promoted;
revisiting them would be local tuning.  Every other item fails a necessary
observability condition before semantic legal interpretation is even tested.

This does not say the items are impossible for a full-notice LLM.  It says
that a Python rule, a law-to-metadata applicability engine, or a source cue
must not be promoted from this dev set.  In particular, the result supports
the earlier rejection of treating missing product codes, missing information
project status, or a missing gold-style source line as a negative condition.

## Consequence for research ordering

The remaining predictive route is no longer another retrieval, law-context,
or rule experiment.  It must be a distinct full-notice semantic decision
topology that preserves the complete original document and treats extracted
facts/retrieved lines as optional context rather than a gate.  It needs two
independent small repeated arms before any dev-200 spend, with the immutable
INC-041 composition as comparator.

## Reproduction

```bash
python incubator/src/inc065_formal_program_observability_map.py
```
