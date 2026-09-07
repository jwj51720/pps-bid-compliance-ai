# INC-037: Independent v3/v21 Rule Composition Audit

## Purpose

This is a composition audit, not a new fitted policy. It applies the already
specified INC-034 (v21) and INC-036 (v3) source-and-metadata predicates to the
immutable INC-018 `single_full` predictions. Only the four cells `v3`, `e3`,
`v21`, and `e21` may change. All other cells must be byte-identical to the
baseline prediction file.

## Preconditions and controls

- Both rules are independently defined from the organizer item table, raw
  metadata, and organizer legal package; neither contains a development-set
  numeric threshold or a source-window length.
- A rule positive must have an unchanged source-line evidence string. The audit
  fails if any positive evidence cannot be found in that notice's source.
- The labeled dev set evaluates the replacement, while the 20,000-record
  `train_unlabeled` corpus is used only to inspect parser coverage, reason
  classes, and source-evidence validity. It is not called the hidden test set
  and supplies no score estimate.

## Decision gate

Record the composition's dev metrics and complete manifests. It may become a
submission-candidate component only after a separate implementation audit shows
the same rule can be packaged under the competition constraints. Its perfect
development performance alone is insufficient to tune, expand, or claim hidden
test performance.
