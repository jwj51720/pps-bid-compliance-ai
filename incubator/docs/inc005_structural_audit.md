# INC-005: Offline Structural Audit

## Locked scope

This is a zero-cost, no-model-call audit of saved inputs and responses from
INC-001 through INC-004. It excludes the duplicate-writer and seed-mismatched
INC-004 artifacts. It measures three separate mechanisms:

1. document-character coverage under the 4,000-character input budget;
2. output-token use, finish reasons, raw-response retention, and parseability;
3. evidence-validation warnings, independently from the predicted label.

The audit cannot recover the malformed INC-004 response because the current
runner discarded raw content when parsing raised. That is itself a finding: a
future runner must checkpoint raw provider content before attempting parsing.

## Decision gates

- If completion usage approaches the configured cap or finish reasons show
  length truncation, test output-schema/output-budget changes before input
  changes.
- If document coverage is consistently low, test an ordered multi-pass or
  document-selection policy before adding rules or retrieval.
- If parse failures or invalid-evidence warnings are material, add deterministic
  raw-response retention and recovery instrumentation before comparing new
  judgment prompts.
- If none is material, proceed to a small, item-specific rule/prompt ablation
  on a fixed broad cohort.

## Result

The audit covers 110 requests from the four valid artifact sets. There were no
`length` finish reasons, and completion use was only 10--18% of prompt-token
use. Increasing the output budget is therefore not justified.

The input result is the opposite: the 4,000-character document prefix covered
only 30.76% of source-document characters across audited requests (20.77% in
INC-001), and only 15 of 110 requests contained a complete notice. This is a
coverage limitation, not an observed model-context limit. The submission
policy permits up to 32,768 model tokens, whereas these prompts used roughly
3,700--3,900 prompt tokens per request.

All retained raw responses were parseable (109/109), but one response that
failed parsing was discarded before it could be retained. Evidence warnings
were 38 in 110 requests: 32 were `v13`, three `v19`, and two `v15`. Thus
evidence alignment and raw-before-parse checkpointing are real engineering
requirements, but do not explain the broad loss of document coverage.

## Decision

Run one bounded input-coverage ablation next: retain the Joint-24 prompt,
schema, model, seed, and output cap, and compare only 4,000 versus 12,000
ordered document characters on the frozen INC-001 24-notice cohort. The
12,000-character arm remains far below the 32k admission ceiling and tests a
middle ground rather than repeating the historical all-document experiment.
