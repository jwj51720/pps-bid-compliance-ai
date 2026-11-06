# INC-127: Gemma operational-contract pilot

## Hypothesis

The EXP-120 Gemma policy may benefit from explicitly sequencing three semantic
operations already implied by its cards: distinguish actual bidder eligibility
from incidental/post-award text; establish applicability before absence; and
compare only matching fields for v24.  This is not new legal context, a rule,
e-prime, retrieval, output-schema change, or character cutoff.

## One controlled change

Both arms use the exact EXP-120 candidate system prompt, decision cards v6,
ordered 4,000-character original-document context, metadata, model,
temperature, seed, 1,200-token V/E schema, parsing, and evidence resolver.
The treatment appends one global operational-contract block.  It does not add
law text, examples, teacher output, or label-derived facts.

## Cohort, budget, and gates

A fresh profile-balanced 32-record cohort is selected by SHA-256 after
excluding every prior Gemma pilot/confirmation record.  Selection and messages
do not read labels.  There are exactly 64 requests, maximum 16 concurrent,
and a `$0.12` experiment ceiling.

Promotion requires treatment macro positive-F1 at least `+0.02` over paired
control, non-decreasing micro recall, absence-item FP increase no more than
one, and failure rate at most 2% in both arms.  Only then is the exact same
contract run on an independently frozen holdout 32.  Failure closes this
contract branch; wording variants on the same cohort are forbidden.
