# INC-097: absence specialist — input audit and stop decision

## Status

This is an incomplete diagnostic run, **not** a candidate for promotion or
merging.  It made 236 requests for 200 development notices: 195 final
successful records and five final `429` failures.  No retry or replacement
request is authorized until the existing input/output audit identifies a
testable prompt defect.  The incomplete five-record score is therefore not a
valid dev-200 result.

## Hypothesis tested

A separate full-context high-reasoning judgement for the five rule-defined
absence items (`v10`, `v11`, `v16`, `v18`, `v20`) would better distinguish
applicability from the presence of a required restriction than the joint
24-item call.

All successful calls received the complete organizer notice documents,
organizer metadata, and the same item cards as the direct Luna comparator.
Thus a false negative cannot be attributed to a document being withheld in
this experiment.

## Observed diagnostic, before any further model call

The specialist's partial v11 result is 2 TP, 4 FP, 4 FN (F1 0.333).  The
joint high-reasoning comparator had 0 TP, 0 FP, 6 FN.  The two recovered true
positives have an explicit restriction in the source:

- `PPS-DEV-14`: direct-production certificate is an eligibility condition.
- `PPS-DEV-060`: direct-production certificate is an eligibility condition.

The four newly introduced false positives instead contain incidental policy,
post-award, or general-information mentions of small businesses, e.g.
`PPS-DEV-158` references the relevant statute only in a subcontracting
provision, and `PPS-DEV-162` contains a public-purchase financing notice.
They are not a tender-participation restriction.  This establishes a concrete
reasoning error: the prompt's B condition needs an explicit *bidder eligibility
versus incidental mention* distinction.  It is not evidence that the document
input was too short.

Four v11 positives remain missed despite the full inputs.  One (`PPS-DEV-061`)
has no source cue beyond the organizer applicability metadata; the others mix
restriction terms with unrelated legal context.  Those are separate cases and
must not be patched by a numeric cutoff or a blanket metadata rule.

## Decision

Do not continue the five-item broad specialist, do not use its predictions,
and do not make an xhigh retry.  The next paid experiment, if any, must first
be specified from this audit as a narrow *source-role classification* test:
whether a supplied span is an actual bidder-eligibility restriction, an
exception, or incidental/post-award text.  It must have a small predeclared
cohort and a fixed request ceiling.  Before it, construct the deterministic
span inventory from the current documents and inspect it without an API call.
