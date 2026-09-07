# INC-125: Luna official-ledger full-dev confirmation

## Hypothesis

The fixed full-notice Luna policy which supplied profile-specific official-law
ledger context improves decision quality for `v1`--`v23`; direct card-v6 is
retained for `v24`, whose task is metadata/source field alignment rather than
law applicability.

## Why this is now permitted

The same context, model, complete-document rendering, schema, output cap, and
high reasoning setting improved on the two predeclared 32-notice cohorts in
INC-118.  The third disjoint cohort independently improved from `0.22579` to
`0.32879` on 31 evaluable records.  The v24-direct semantic composition was
defined in INC-118 before the third labels were inspected and scored `0.33690`.
This is a full-dev confirmation, not prompt selection.

## Frozen policy

- Model: `gpt-5.6-luna`, OpenAI Responses API, reasoning `high`, output cap
  8,192; all original documents and organizer metadata remain in every call.
- `v1`--`v23`: output from the profile-specific official-law ledger context.
- `v24`: archived INC-088 direct card-v6 output.  This semantic separation was
  declared before the third cohort and avoids treating legal context as a
  solution to a field-alignment task.
- Reuse successful raw outputs from the three exactly matching INC-118 cohorts
  (95 records).  Run the remaining 104 records only; their manifest is all
  remaining dev IDs in organizer order and does not read labels.
- `PPS-DEV-125` was blocked by the provider's biological-risk safety filter in
  INC-118 before model generation.  It is never retried or rephrased.  The
  fixed whole-vector fallback is its archived direct card-v6 response.  This
  is a transport fallback, not an item/label-specific merge.

## Budget and integrity gates

The paid run is exactly 104 requests, concurrency four, with the prior
experiment's $20 declared ceiling.  A response is accepted only if it is the
strict 24-label schema.  On completion, validate source/model/prompt hashes
against INC-118, every source ID occurs once, and record failure rate and
token usage.  Do not selectively retry failed rows; any additional safety or
schema failure uses the same whole-vector direct-card fallback and is reported.

The policy is considered a new Luna result only if all 200 rows are accounted
for, per-item TP/FP/FN and macro positive-F1 are computed, and changed cells
are audited.  It remains a teacher-quality result, not a submission policy:
the final inference path must still run Gemma on every notice.
