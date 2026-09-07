# INC-101: full-context augmented fact-ledger gate — rejected

## Completed evidence

This tested the distinct topology that INC-085 did not: a first Luna pass made
a typed fact ledger, but the high-reasoning final pass retained every source
document as well as the ledger.  The source-validating ledger was reasonably
dense (73.5% nonempty fact-group entries among completed pairs), so this is not
a trivial empty-context failure.

Three of 16 final calls ended with the explicit API reason
`max_output_tokens` at the predeclared 4,096-token cap.  The protocol forbids
changing the cap or replaying only those cases after seeing results.  Therefore
only 13 paired notices are valid for the pilot, below its predeclared minimum
of 14.

| Same 13 frozen IDs | Macro positive F1 |
| --- | ---: |
| INC-088 direct full-context high | 0.08333 |
| INC-101 augmented ledger + full context | 0.08333 |

Only two notices changed labels: `PPS-DEV-056` changed v24 from 1 to 0 and
`PPS-DEV-183` changed v7 from 1 to 0.  Neither produced a macro improvement on
the paired sample.  Thus the ledger did not reliably alter the direct model's
reasoning despite preserving the documents.

## Decision

Reject this topology and do not repair it by increasing output caps or running
the planned 64/200 continuation.  The observation is useful nevertheless:
generating a generic cross-item factual summary consumes reasoning/output
budget without resolving the hard conditional predicates.  The next branch
must instead make one *semantic operation* explicit inside the original direct
call, while retaining the whole source; it should not add a generic first-pass
summary.
