# INC-070 Result: Legal-Essence Card Audit

All 24 candidate cards were generated from the organizer item table plus the
complete, hashed legal units already recorded in INC-023, then reviewed in a
separate source-only Gemma call.  Labels and notices were not inputs.

- 48 calls completed for `$0.03328`.
- 11 cards were accepted without unsupported additions: `v4`, `v7`, `v9`,
  `v10`, `v11`, `v12`, `v13`, `v15`, `v18`, `v19`, `v23`.
- 13 did not pass.  Two source-audit responses also exhausted the provider
  route rather than returning valid JSON (`v16`, `v22`).

This is a useful negative constraint, not a license to fill remaining cards
from memory.  The audit exposed substantive ambiguity, including a mismatch
between v14's item label and the supplied statutory amount range.  Any future
use must retain the accepted-card list and source hashes; it must not claim a
validated all-24 legal summary.

Artifacts: `data/derived/legal_essence_cards_v1.json` and
`runs/inc070_legal_essence_card_audit/`.
