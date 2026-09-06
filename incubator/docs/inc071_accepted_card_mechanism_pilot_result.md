# INC-071 Result: Invalid Card-Effect Comparison

This run is **not evidence for or against legal-essence cards**.

The intended comparison was complete notice and 11-item nested `v/e` output,
with treatment adding only the audited cards.  Post-run audit found that the
control system prompt omitted the corresponding 11 item names and
absence-detection definitions, while treatment acquired those names through
the card payload.  Thus at least two material variables changed.

The run made 128 calls ($0.14113 total).  One control response exhausted the
800-token structural reserve and was malformed.  On the remaining 31 paired
rows, treatment had 0.24646 target Macro F1 versus 0.10830 control; the
second complete repeat was 0.21861 versus 0.07468.  These deltas are
uninterpretable because of the missing-control definition contract, and must
not be promoted, composed, or quoted as a card result.

Two valid engineering observations remain:

1. The treatment responses were compact (roughly 174–389 completion tokens),
   while the under-specified control commonly generated 400–2,079 tokens and
   one malformed 800-token response.  This shows that item-definition
   completeness is a required transport invariant.
2. A corrected experiment must supply an identical item-definition and
   absence/evidence contract to both arms, use only the 11 audited cards in
   treatment, and treat the cards as the sole variable.  It needs fresh,
   separately recorded responses rather than overwriting INC-071.

The raw requests/responses remain under
`runs/inc071_accepted_card_mechanism_pilot/` for audit.
