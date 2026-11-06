# EXP140 — independent confirmation of the two-call G02 overlay

EXP140 is policy-identical to EXP139. It changes only the frozen record cohort
to `configs/dev_prompt_holdout_v1.json`, selected without labels or prior
outcomes. It tests whether EXP139's fast-panel improvement survives outside
the selection panel.

Before the remote run, re-export and read exact inputs for a complete notice
(`PPS-DEV-062`), a holdout overflow notice (`PPS-DEV-094`), and a holdout
notice with attachments (`PPS-DEV-27`). Then run preflight, exact-tokenizer
admission for all holdout records, and a clean mock. Expected cost: 40 calls.
Compare against EXP128A, the exact organizer single-call holdout control. No
dev-200 run or submission promotion follows from a holdout regression.

## Pre-call review record (2026-09-07)

Passed. The first draft used the nonexistent zero-padded ID `PPS-DEV-027`; it
was corrected to the actual organizer ID `PPS-DEV-27` before any provider
call.

- Rendered messages: `outputs/exp-140-two-call-g02-overlay-holdout/prompt_review/`
  for `PPS-DEV-062`, `PPS-DEV-094`, and `PPS-DEV-27`.
- Review conclusion: G01 has exactly 24 response keys and the exact organizer
  profile; G02 has only `v6`, `v7`, `v8`, `v9`, `v19`. The paired calls have
  identical user notice/metadata content. The first record is complete;
  overflow and attachment records visibly retain the organizer's 4,000-char
  truncation. No cards, law/RAG, product context, or internal routing text is
  present.
- Full cohort exact-tokenizer admission:
  `outputs/exp-140-two-call-g02-overlay-holdout/prompt_review_holdout/admission.json`
  records 20 notices, 40 calls, max 4,084 tokens.
- Mock completed at
  `outputs/exp-140-two-call-g02-overlay-holdout/mock/_mock/`.
