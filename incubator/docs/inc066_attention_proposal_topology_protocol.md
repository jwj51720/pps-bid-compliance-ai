# INC-066: Independent Attention-Proposal Topology Pilot

## Question

Can a separate, non-decisional full-notice pass improve the final joint legal
judgment by proposing one source line per item as *optional attention*, while
the final pass still reads every original document and is free to ignore every
proposal?

This is the remaining faithful version of the evidence-first idea.  It does
not use retrieval as a gate and does not force a positive judgment to cite the
proposed line.

## Why this is distinct from closed experiments

- INC-027 extracted a global typed fact ledger and then made its adjudicator
  depend on that ledger.  It lost recall.
- INC-054 made a label-only full-notice decision without any independent
  attention information.  It underperformed.
- INC-060 required each joint positive to co-generate a line ID; that semantic
  coupling failed in 45 responses.
- INC-064 used a legal memo to rank BGE candidates and rejects candidate
  gating.

INC-066 changes exactly one cognitive variable relative to a label-only
control: an independent locator supplies an item-indexed source-line attention
appendix.  It makes no 0/1 decision, sees the complete original notice, and is
not a source, eligibility, or output-validation gate.

## Frozen cohort and arms

Use the deterministic positive-cover seed of the existing INC-054 cohort: one
SHA-256-selected dev positive per item, before its random filler is added.
Several items share the same selected notice, so the fixed unique cohort has
20 notices while still covering every item.  This is a 20-notice mechanism cohort whose selection rule is frozen from an
older experiment, not selected for a result in this experiment.  It is not a
dev-200 claim.

For each notice, run two independent repeats of each arm at the same
Gemma-4-26B provider settings.

1. **Control:** metadata plus every complete source document; flat 24 binary
   output only.
2. **Attention treatment:** first, metadata plus the same complete line-
   numbered source documents and item table.  It returns exactly one `a1`…
   `a24` line ID (or `-1`) per item, with no label, quote, or violation claim.
   Second, metadata plus every same complete source document, item table, and
   the exact selected source line for each item.  It returns the same flat 24
   binary output as control.  The final prompt explicitly says proposals are
   fallible navigation hints, not evidence or a reason to make either label.

The locator's 24-ID schema uses a 512-token completion reservation because
INC-059 empirically established that a serialized 24-field dynamic-enum object
requires 262–417 completion tokens.  This is a schema serialization lower
bound, not a character, score, or candidate-count tuning parameter.  The
candidate cardinality is exactly one per required task item, not a rank cutoff.
No original document or selected line is truncated.

## Validity, scoring, and cost

The primary result is each repeat's treatment-minus-control Macro F1 on this
same cohort, with TP/FP/FN and all changed cells.  Both locator and final
responses must parse and meet their schemas; any failure makes that treatment
repeat unscorable, with no response repair or label fallback.  There is no
evidence submission claim in this pilot.

Maximum calls: 120 (20 notices × 2 repeats × [one control + locator + final]).
Maximum reported cost: `$0.50`.

## Decision rule

- **Advance:** both repeated treatment-control Macro-F1 deltas are strictly
  positive; neither treatment introduces more new errors than corrected cells;
  all calls are valid.  Then preregister a distinct 48-notice confirmation.
- **Partial:** locator transport is valid and the direction is positive in one
  repeat only.  Record the instability; no prompt edit or dev-200 escalation.
- **Reject:** either treatment repeat is non-positive, malformed, or adds at
  least as many errors as corrections.  Do not tune locator wording, line
  counts, candidate selection, or final decision wording.
