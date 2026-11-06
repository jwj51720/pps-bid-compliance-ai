# EXP135 — two-way G02 dev-200 confirmation

EXP135 is policy-identical to EXP133/134. The only change is evaluation on all
200 development notices. It is justified only because the exact control was
beaten on both frozen fast-20 and independent holdout-20 cohorts.

Before the paid run, reuse no cached provider output: run a fresh preflight,
review the exact actual inputs for complete and overflow representative notices,
perform all-record exact tokenizer admission, and complete a grouped mock. The
expected execution is 200 × 2 = 400 calls.

Compare against EXP109's exact organizer control (`0.22350`). Record per-item
TP/FP/FN, parse failures, evidence validity, output tokens, and total call
latency. Reject the execution partition if dev-200 does not improve quality or
if its 2× call cost cannot plausibly fit the competition runtime envelope.
