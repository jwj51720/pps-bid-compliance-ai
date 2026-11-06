# INC-101: full-context augmented fact-ledger gate

## Hypothesis

The strong full-notice Luna path fails mainly on compositional predicates and
cross-item confusion, not missing attachments.  A first pass that extracts a
small, typed, source-quoted fact ledger can help a second pass **only when the
second pass keeps every original notice document**.  This is deliberately
different from rejected INC-085, whose final adjudicator saw a ledger only.

## Fixed pilot

Use the first 16 records of INC-085's already frozen, label-free structural
manifest.  Selection was determined before labels by metadata/document
structure and source length; labels are read only after calls finish.  Each
notice receives two Luna calls: Stage A `medium` reasoning, 4,096 output-token
cap; Stage B `high`, 4,096 cap.  At most 32 requests are made, concurrency two.
No per-item or per-case merge is permitted.

## Contract

Stage A extracts nine typed observable fact groups with exact source quotes;
it cannot emit a compliance label.  Stage B receives the validated ledger,
the same cards and metadata, **and full original documents**, then emits all
24 labels.  Invalid ledger quotes are cleared rather than trusted.  A failed
stage leaves that notice out of the pairwise pilot score; it is never replaced
with a prediction from another method.

## Gate

The pilot must complete at least 14 paired records, retain at least 60% valid
nonempty ledger entries, and improve macro positive F1 versus INC-088 on the
same IDs without a new false-positive concentration.  Otherwise stop this
topology.  Passing is only permission for a 64-notice confirmation, not for a
dev-200 merge.
