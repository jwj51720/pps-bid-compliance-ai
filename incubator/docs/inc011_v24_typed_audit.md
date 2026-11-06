# INC-011: v24 Typed Reconciliation Audit

This is a no-API, no-auto-label audit. It extracts only conservative candidates
where a source document explicitly states a contract method, named money field,
regional-restriction phrase, or industry-restriction phrase that conflicts with
the corresponding metadata field. Every candidate retains the unchanged source
span and field identity.

The audit may establish candidate recall and a matched-negative error taxonomy;
it may not create a v24 positive rule. A paid follow-up is allowed only if its
candidate recall is sufficient and manual review identifies a single field type
whose normalizations are semantically sound.

## Result and decision

The initial conservative extractor found candidates for seven of eight v24
positives (87.5%) but also for 76.0% of negatives. Contract-method mentions
were the dominant failure source: 16 candidate spans in positives but 639 in
negatives, because an isolated method string can occur in a descriptive or
legal context without stating the notice's actual contract method. One positive
had no candidate at all.

**Do not run a Gemma v24 candidate pilot from this extractor.** It fails the
candidate-recall prerequisite and has no field-specific matched-negative
normalization rule. The next possible v24 action is a document-layout-aware
extractor that requires a field heading/value relation (not merely a method
token); it must first restore 100% candidate recall in the current eight
positives without increasing the matched-negative burden. No automatic v24
positive rule is authorized.

## INC-011R layout repair

The repair accepts only a recognized field heading followed by its value on the
same line/table relation, and compares money only to the matching metadata
field. It excludes unheaded method mentions such as law citations. It remains
an offline candidate audit with no automatic positive label.

The result is 37.5% positive candidate recall (3/8) and 15.1% negative
candidate rate. This is a useful precision signal but fails the recall
prerequisite decisively. The initial broad extractor and the layout-only repair
form a clear trade-off; do not continue lexical repair or run a v24 Gemma pilot.
Future v24 work needs a source-field ontology beyond these four simple pairs,
such as the organizer's exact mapping of which document field corresponds to
which metadata field. Until then, preserve this only as an audit artifact.
