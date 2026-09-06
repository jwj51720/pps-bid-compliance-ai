# INC-100: v11 source-role diagnostic gate

## Hypothesis

Once the organizer's exact product-code applicability state is supplied, a
focused Luna prompt can separate a qualifying bidder-eligibility restriction
from incidental/post-award mentions.  This should preserve the two recovered
v11 positives while eliminating the four observed false-positive mechanism.

## Fixed diagnostic cohort and budget

The fixed ten IDs are recorded in
`data/derived/inc100_v11_role_audit_ids.json`: the six current dev v11
positives and four false positives newly introduced by INC-097.  This is a
mechanism audit, deliberately **not** a performance estimate.  It makes at
most ten OpenAI calls (`gpt-5.6-luna`, `reasoning=medium`, 2,048 maximum output
tokens, concurrency two); no retries after a transport failure.

## Input and output contract

Each call receives every organizer document, all organizer metadata, the v11
card, and a deterministic exact-code status.  `not_matched` is a fact from the
organizer competition-product CSV; `unknown_no_exact_code` is not negative
evidence.  The output separately declares applicability, source role,
restriction status, an unchanged source quote when one exists, and v11.

## Gate

This passes only when all four exact-code `not_matched` cases are declared
noncompetitive/v11=0 and both currently recovered positives remain v11=1.  A
failure is analyzed from raw output; it does not justify a larger call.  Even
on pass, a fresh complete dev-200 confirmation is a separate decision.
