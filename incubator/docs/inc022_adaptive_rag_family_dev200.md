# INC-022: Adaptive Legal-Context Admission

INC-021 compressed every retrieved law excerpt to 165 characters so that the
single longest notice could fit. INC-022 changes only that admission policy.
For every notice and legal family, it binary-searches the largest common
per-item excerpt length up to 600 characters that fits the exact Gemma chat
template budget. It retains every complete notice document and all other
family-pass, model, schema, evidence-validation, and merge rules.

The purpose is to test whether longer organizer-law context recovers the
recall lost in INC-021 without reinstating the original joint-pass FP problem.
Success requires Macro F1 above 0.26074, non-decreasing INC-021 recall,
evidence validity at least 0.90, and at least 95% successful calls.

## Status: invalidated before completion

This run was stopped at 625/800 calls. Its rationale was not adequate for a
generalization experiment: the prior 165-character setting and the new
600-character maximum were chosen from dev token-fit behavior, not from a
law-article or submission-policy invariant. The partial checkpoint is retained
only as an interrupted transport artifact and must not be scored, resumed, or
used for policy selection.

Any replacement must pre-register a context rule independent of dev lengths:
keep a complete retrieved legal article/paragraph as fixed context; reserve the
submission-defined output budget; then use the same exact admission and
complete-document overflow policy for every notice. Do not search excerpt
character counts against dev metrics.
