# INC-054: Flat Joint-24 Decision-Only Pilot

## Question

Can the verified flat response transport improve global 24-item legal judgment
by removing simultaneous free-text evidence generation from the model's output
task?  This is a broad output-topology question, not an item-rule experiment.

## Scope and invariant

The model receives the same full ordered notice, metadata, and all 24 item
definitions as the global joint baseline.  It outputs one flat JSON object
with `v1` through `v24` binary fields only.  No product card, retrieval,
decision threshold, document omission, legal text, prompt wording change, or
post-hoc label correction is allowed.

This is explicitly a **label-quality diagnostic**, not a submission policy:
evidence is not invented or recovered here.  Any successful label topology
would require a later independent source-evidence transport and validation
experiment before it can affect a final pipeline.

## Cohort and repeats

The pilot cohort contains one deterministic hash-selected positive notice per
item (duplicates collapsed), then deterministic hash-selected remaining
notices to reach 48.  Labels choose only positive coverage, not prompts or
selection among alternatives.  Both flat runs use identical model, seed,
temperature, complete documents, and schema; they measure provider variation.
The historical INC-041 immutable composition supplies a fixed diagnostic
reference on the same IDs but is not a contemporaneous causal control.

## Gates

Both runs must parse 100%, have provider completion no greater than the
requested flat transport cap, and improve pilot Macro F1 over the fixed
reference by at least 0.05 with no more than two items losing all recovered
true positives.  Otherwise reject decision-only output separation.  Even a
pass only authorizes a separately preregistered all-dev repeated confirmation
and evidence feasibility test.
