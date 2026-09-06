# INC-128: Luna ledger profile-stability audit

INC-128 is an offline stratification of the policy fixed before INC-125
full-dev aggregation.  It is not a new model result or a profile-specific
policy selection.

| Profile | Records | Direct-card Luna | Ledger hybrid | Delta | Positive cells |
|---|---:|---:|---:|---:|---:|
| national | 84 | 0.28321 | 0.32779 | +0.04458 | 61 |
| local general | 46 | 0.26273 | 0.32731 | +0.06458 | 44 |
| local negotiated | 41 | 0.32970 | 0.34159 | +0.01189 | 42 |
| local small | 29 | 0.14583 | 0.14583 | 0.00000 | 6 |

The full-dev Luna improvement is not confined to one profile: it appears in
both national and local-general notices.  Its absence in local-small notices
is unsurprising given only six positive cells, but is not a license to create a
profile-specific output merge.

## Gemma transfer check and decision

Before considering a profile-gated Gemma legal-context experiment, INC-122's
already completed paired outputs were scored by the same profile labels.  Its
national rows regress from `0.12500` (card) to `0.08333` (compact official-law
summary); local-general has zero positive F1 in both arms.  Thus the available
Gemma evidence does not support the Luna-derived profile mechanism.

**Decision:** close profile-gated legal-summary transfer.  Do not spend a new
Gemma cohort on it.  The remaining submission-relevant policy is the
source-complete EXP-123 correction of EXP-120, whose public score must be
measured by an explicit leaderboard submission rather than another local
prompt variation.
