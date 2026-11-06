# INC-042 Result: Replicated v2/v4 Law Adjudication

## Execution

The preregistered 36-notice cohort (all ten v2/v4-positive notices plus all 26
dual-negative performance-amount hard negatives) completed all 144 requested
OpenRouter calls at $0.31287. Each condition used full notice documents; the
law arm added only complete organizer legal units. Two no-law and two law
repeats were issued with the recorded same request settings.

## Gate result: rejected before performance comparison

No arm was eligible for F1 scoring under the preregistration. Source-evidence
validation failed in 6/36 control-r1, 4/36 law-r1, 6/36 control-r2, and 4/36
law-r2 responses. Each failure is a binary-positive LLM response whose supplied
quote was not an unchanged source substring. It was deliberately recorded as a
format/evidence failure rather than silently converted to zero, so no selective
metric or law-minus-control delta is reported.

The failures concentrate in table and evaluation-layout text, especially v4;
some output changes line breaks, while others omit or alter non-whitespace
tokens. This refutes the free-text-evidence active-output topology for this
experiment, not the organizer legal facts themselves.

## INC-043 follow-up

The predeclared offline whitespace-only resolver found 10/21 failed positive
quotes safely resolvable to a unique unchanged source substring (one already
exact, nine whitespace-only). The other 11 were not resolvable. It cannot
retroactively rescore INC-042; it shows that whitespace repair alone cannot
make free quotation submission-safe.

## Next direction

Do not repeat this prompt with minor wording changes. A future active-item LLM
experiment must ask the model to choose from Python-generated source candidate
IDs, then map the chosen ID to the original unchanged source line. Candidate
coverage must be audited independently before that call; the model must retain
the full notice for context and cannot use candidate absence as a negative gate.
