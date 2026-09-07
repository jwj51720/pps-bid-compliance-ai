# INC-065: Formal Legal-Program Observability Map

## Purpose

This is an offline, all-item triage before another prediction call.  A legal
rule can be automated only if the final system can observe its applicability
conditions and its source-side factual condition.  The map separates these
requirements from model accuracy, keyword frequency, and dev-score tuning.

## Frozen program families

The 24 organizer items are assigned from their item-table legal citations and
plain task shapes, before looking at predictions:

| Family | Items | Necessary observable inputs |
|---|---|---|
| Eligibility/performance | v1–v4 | contract regime, amount where relevant, an eligibility condition and its restricted subject/amount in source |
| Regional restriction | v5–v8 | regime, amount/procurement context, geographic restriction plus any statutory exception facts |
| Specification/economic restriction | v9 | binding specification condition and equivalence/exception language in source |
| Product/applicability | v10–v18 | product applicability, price bracket, legal exception state, and source restriction or absence |
| Timing/procedure | v19–v23 | procedure/contract context and a source-side timing, participant, or ratio fact |
| Cross-source consistency | v24 | the relevant metadata field and its source counterpart |

The map records three independent facts per item: metadata-field availability,
organizer gold-evidence source-line containment, and the immutable INC-041
error profile.  It does **not** derive a rule from labels, declare a source cue
sufficient, choose an activation threshold, or change predictions.

## Decision use

An item/family can be considered for legal-program construction only when its
required metadata fields are fully present and its positive organizer evidence
is source-line observable.  These are necessary, not sufficient, conditions.
Failure means no deterministic predicate experiment follows.  Passing merely
identifies the next family needing a separately specified complete legal
program and all-positive/hard-negative audit.
