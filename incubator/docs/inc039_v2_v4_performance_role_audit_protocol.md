# INC-039: v2/v4 Performance-Restriction Role Audit

## Legal distinction under test

The organizer's national guideline prohibits using performance to restrict
competition for a below-notice-amount manufacturing/service contract. Its
separate restriction guidance also prohibits demanding completed performance
issued by a specified institution while excluding equivalent private or other
public performance. v2 and v4 may consequently co-occur; they are not
mutually-exclusive price bins.

This audit does not infer an unprovided numeric notice amount. It uses raw
`입찰추정가격` only as an auditable fact and separately detects these two
source roles:

1. a bidder-qualification performance lower-bound, using the frozen INC-036
   role constraints; and
2. a performance condition that also constrains the issuer, recipient, or
   required subject through an explicit relational phrase (`발주`, `납품`,
   `수요기관`, `대상`, or an institutional noun).

## Controls

Every retained fact is an unchanged source line with document type and offset.
The role-2 marker is a recall-oriented fact finder, never a legal conclusion:
it may match legitimate sector descriptions. It has no character window,
numeric cutoff, model output, or development-derived exception list.

## Gate

Report candidate coverage and negative activation for v2/v4 separately,
overlap between their gold labels, raw-price distributions, and each positive's
source role. Advance only if the raw data and complete organizer law provide a
price applicability value and a legally interpretable role distinction. If the
notice amount is absent or a role remains semantic/ambiguous, use an active
source-grounded LLM adjudication experiment rather than an automatic rule.
