# INC-037 Result: Controlled v3/v21 Composition

## Controls passed

INC-037 materializes an INC-018-derived CSV in the exact original row order.
The only permitted changes are `v3/e3` and `v21/e21`; an independent file-level
comparison found zero changes in every other cell. Python syntax checks passed
for all four deterministic predicate/composition modules.

## Dev result

Replacing the two target item pairs yields Macro F1 **0.24856**, versus
INC-018's 0.19361. The independent rules each have TP/FP/FN of v3 8/0/0 and
v21 6/0/0, with source-containment evidence validity 1.0.

The 20,000-record organizer-format unlabeled scan found 82 v3 and 9 v21 rule
positives, all with contained source evidence. This is a parser-format and
provenance check only: the corpus is not the hidden test set and the counts do
not provide a test prevalence or score estimate.

## Decision and next direction

Keep this as a reproducible deterministic component, but stop tuning v3/v21
against dev. The largest remaining weakness is broad: INC-018 has zero F1 for
many independent item shapes. The next branch should therefore be a fresh,
pre-registered source-fact coverage audit across a *different* structural
family, before choosing any LLM, retrieval, or rule implementation.
