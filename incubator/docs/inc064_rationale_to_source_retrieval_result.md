# INC-064: Rationale-to-Source Retrieval Gate Result

## Execution validity

All 12 frozen v4/v7 positive-evidence cells produced a valid flat `memo`
response.  The initial aggregation attempt exposed a local return-value bug in
the embedding-usage collector before it scored any cell.  The collector was
fixed; the already checkpointed memos were reused unchanged, and only the
specified BGE ranking was then run.  Reported total remote cost was
`$0.02409515`.  This is an evidence-ranking audit, so it produces no labels,
no F1, and no submission evidence.

## Paired retrieval result

| Representation | MRR | Recall@1 | @3 | @5 | @10 | @20 |
|---|---:|---:|---:|---:|---:|---:|
| Item criterion + metadata + complete linked law | 0.13655 | 0.000 | 0.167 | 0.250 | 0.417 | 0.667 |
| Same query plus Gemma legal/factual memo | 0.20826 | 0.083 | 0.250 | 0.333 | 0.500 | 0.667 |

The memo improves 9 of 12 evidence ranks, leaves two unchanged, and worsens
one (`PPS-DEV-10/v7`, 17 to 18).  Every evidence remains somewhere in its
notice line set, but this is not a useful result for a candidate gate: two v4
examples remain at ranks 120 and 141 after the memo.  A later adjudicator that
only saw a bounded candidate package would therefore still lose known
evidence, despite the better average ranking.

The content diagnosis is also important.  Several memos correctly express a
compound statutory question (contract amount/type, procurement regime,
institution-specific performance or an adjacent-region exception).  Yet
BGE's nearest source lines do not reliably select the organizer's exact
evidence line.  This is the same evidence-localization limitation seen in
INC-049, now after a legally informed full-document reading rather than a
bare criterion query.

## Decision

**Rejected as a retrieval gate.**  The preregistered paired condition required
no evidence loss, no pairwise rank regression, and at least one strict rank
improvement.  The rank regression means it fails.  More fundamentally, its
rank tail cannot safely support a fixed candidate context.  Do not repair the
memo wording, select a rank cutoff, or launch an adjudication/F1 experiment
from this result.

The narrow positive finding is retained: concise legal memos are
transport-safe and often improve semantic source ranking.  They may be used
only as non-gating auxiliary analysis in a future architecture that still
provides the complete original notice to its final judgment.  They cannot
replace direct source location or suppress a label.

## Reproduction

```bash
python incubator/src/inc064_rationale_to_source_retrieval_gate.py --mode preflight
python incubator/src/inc064_rationale_to_source_retrieval_gate.py --mode run
python incubator/src/inc064_rationale_to_source_retrieval_gate.py --mode aggregate
```

Artifacts: `incubator/runs/inc064_rationale_to_source_retrieval_gate/`.
