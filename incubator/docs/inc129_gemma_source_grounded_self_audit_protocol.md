# INC-129: Gemma source-grounded self-audit

## Hypothesis

A second Gemma V/E decision can correct a first full joint decision when it
receives that decision as an auditable claim **and retains the same original
notice, metadata, cards, and source-evidence contract**.  This differs from
rejected e-prime/ledger-only approaches: no generated summary replaces source
context, no label is conditionally selected by Python, and the final decision
is again a normal V/E output.

## Fixed topology

1. The direct control is the exact EXP-120 4,000-character card-v6 V/E call.
2. The audit call gets the identical direct prompt plus a deterministic JSON
   rendering of the first call's parsed `v1`--`v24` labels and source-resolved
   evidence.  It must independently re-check every claim against the original
   source and emit a new ordinary V/E object.

The model, temperature, seed, card, ordered context, schema, parser, evidence
resolver, and generation cap are unchanged.  The sole change is the prior
source-grounded judgment appended to the second call.

## Cohort and gates

Use the largest remaining fresh label-blind profile-balanced cohort: six notices
per profile, 24 total.  Previous Gemma pilots have already consumed all but six
local-small records; this is a structural availability bound, not a score-based
sample choice.  There are exactly 48 requests: one direct
and one audit request per notice.  The audit must improve macro positive-F1 by
at least `+0.02`, not reduce micro recall or evidence validity, and both stages
must have <=2% failures.  Only then may the unchanged policy see a fresh
independently selected holdout of the remaining records, balanced as availability
permits,
holdout; otherwise the self-audit topology closes without wording repair.

An eventual submission must run both calls per notice, with the second call's
result used directly; projected runtime is measured only after passing both
cohorts and dev200 confirmation.
