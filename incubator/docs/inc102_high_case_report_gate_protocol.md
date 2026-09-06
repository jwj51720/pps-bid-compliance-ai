# INC-102: high-reasoning direct case-report gate

## Hypothesis

INC-087's direct full-notice case report made 14 corrected versus seven
introduced label changes on its frozen 64-notice cohort, even though its
reasoning effort was not specified.  Requiring a short per-item basis and
source quote may therefore focus the high-reasoning direct model on
applicability, actual bidder eligibility, exceptions, and corresponding
metadata fields without removing the original notice.

## Controlled pilot

Use the first 16 IDs of the existing label-free INC-085 structural manifest.
The only material change from the INC-088 comparator is the output contract:
each item returns `{v, basis, quote}` instead of `v`; prompt source, metadata,
cards, model, and `reasoning=high` are retained.  The output cap is 8,192,
because INC-088 and INC-101 directly established that high reasoning can reach
an incomplete result at 4,096.  This is a fixed transport adequacy setting,
not a score-tuned threshold.

At most 16 calls are made, with concurrency two.  The run records raw output
and validates every positive quote as an unchanged source substring.  Invalid
quotes do not change raw labels in the diagnostic score; their rate is a
separate deployment gate.

## Promotion gate

At least 14 successful calls, at least 95% valid positive quotes, and a
positive macro-F1 delta versus INC-088 on exactly the same IDs are required to
advance to a label-free 64-notice confirmation.  Otherwise this output shape
is rejected; no label-wise merge or selective quote gate is allowed.
