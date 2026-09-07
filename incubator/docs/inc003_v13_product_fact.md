# INC-003: Joint-24 Exact Product-Fact Ablation

## Hypothesis and preflight correction

The experiment tests whether a concise applicability fact from the organizer's
competition-product CSV can reduce v13 false positives while retaining the
joint-24 control's recall. The paired cohort is identical in construction to
INC-002: six v13 positives and 12 historical-v13-FP negatives.

The initial preflight used metadata codes only and had no `matched` cases, so
it was not run. The selector was corrected before any API call: a document's
explicit ten-digit code may establish a positive exact CSV match, while a
document code never establishes `not_matched`. The final cohort was four
`matched`, seven `not_matched`, and seven `unknown`; gold v13 positives were
four `matched` and two `unknown`.

Both policies use the same joint-24 prompt, documents, metadata, model, schema,
and token budget. Treatment adds only a short natural-language rendering of the
exact CSV status and states that it is neither evidence nor a violation by
itself. No law text, card, rule correction, retrieval, or output-scope change
was made.

## Result

| Policy | Requests | v13 TP / FP / FN | Precision | Recall | F1 | Evidence validity | Cost |
|---|---:|---|---:|---:|---:|---:|---:|
| Joint-24 control | 18 / 18 | 6 / 9 / 0 | 0.40000 | 1.00000 | 0.57143 | 0.46667 | $0.01513 |
| + exact product fact | 18 / 18 | 4 / 4 / 2 | 0.50000 | 0.66667 | 0.57143 | 0.37500 | $0.01484 |

The treatment removed five false positives but also removed two true positives;
the preregistered F1-improvement and recall-preservation gates therefore fail.
All 36 requests succeeded.

The fact-state analysis is more informative than the aggregate tie:

| Exact status / gold v13 | Control positive | Treatment positive | Interpretation |
|---|---:|---:|---|
| matched / positive (4 notices) | 4 / 4 | 4 / 4 | product fact retained known-applicability recall |
| unknown / positive (2 notices) | 2 / 2 | 0 / 2 | product fact incorrectly made unknown status act as a negative gate |
| not-matched / negative (7 notices) | 5 / 7 | 3 / 7 | two false positives removed |
| unknown / negative (5 notices) | 4 / 5 | 1 / 5 | three false positives removed |

## Decision

**Partial success; no policy promotion.** Exact CSV matching is valuable as a
reproducible fact layer: it retains all matched positives and reduces false
positives. The current *rendering* is unsafe because its unknown state suppresses
both positives and negatives, contrary to the intended “do not infer” contract.

The single permitted repair is not another product lookup or a new law prompt.
It is a wording-only unknown-state ablation on the seven unknown notices:
retain the fact that applicability is unknown, but explicitly say that unknown
must not increase *or decrease* v13 and that the ordinary notice evidence must
decide. It succeeds only if it restores unknown-positive recall without
reintroducing the three unknown-negative false positives removed by INC-003.
