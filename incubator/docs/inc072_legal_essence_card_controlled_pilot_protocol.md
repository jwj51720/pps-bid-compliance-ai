# INC-072: Corrected Legal-Essence Card Pilot

INC-071 is invalid and is not reused.  INC-072 is a fresh 24-notice,
two-repeat paired study of the 11 cards that passed INC-070's source audit.

Both arms have byte-identical system prompts containing each item name,
absence-detection status, full-source evidence rule, model, temperature, seed,
output schema, metadata, and complete ordered notice documents.  The only
difference is a treatment-user-message block containing the source-audited
`applicability`, `violation_rule`, and `exception_or_boundary` statements.

The cohort is one deterministic hash-selected positive per item plus thirteen
hash-selected comparison notices.  It is an inexpensive falsification round,
not a local score optimization.  Two repeats need 96 calls and cost at most
`$0.40`.  Progress requires both positive deltas, more corrected than newly
wrong cells, and no item losing all cohort true positives.  Otherwise cards
are rejected as a global judgment context and retained only as controlled
vocabulary for a separate e-prime experiment.
