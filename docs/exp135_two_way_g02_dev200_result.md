# EXP135 — two-way G02 dev-200 result

## Pre-call verification

The policy is identical to EXP133/134. Before the paid run:

- preflight found no effective policy difference from EXP133;
- the exact rendered inputs for `PPS-DEV-062` (complete), `042` (announcement
  overflow), and `01` (overflow plus omitted attachments) were read;
- the two user messages in each reviewed notice were byte-identical, while the
  system prompt and JSON schema contained exactly their group-local items;
- full dev admission found 200 records × 2 groups = 400 calls, with a maximum
  of 4,284 Gemma-token inputs; and
- grouped mock completed all 200 rows.

The message exports are in
`outputs/exp-135-two-way-g02-dev200/input_review/`; full admission is in
`outputs/exp-135-two-way-g02-dev200/admission_dev200/`.

## Result

| Run | calls | macro positive F1 | evidence validity | joint evidence F1 |
| --- | ---: | ---: | ---: | ---: |
| EXP109 exact organizer control | 200 | 0.22350 | 0.78495 | 0.28258 |
| EXP132 four-way partition | 800 | 0.22181 | 0.75862 | 0.35067 |
| EXP135 two-way partition | 400 | **0.24694** | **0.81272** | 0.29679 |

The five G02 items (`v6`, `v7`, `v8`, `v9`, `v19`) improve from mean F1
`0.23410` to `0.46974`. In particular, `v7` is 0.600, `v8` is 0.667, and
`v19` is 0.615. The remaining 19 items decline from mean F1 `0.22071` to
`0.18831`; this is why the total gain is modest despite the G02 gain.

The 400 calls had 2,687.6 seconds summed provider latency, versus 2,029.3
seconds for EXP109's 200 calls and 3,503.2 seconds for EXP132's 800 calls.
Two G02 responses were malformed (`PPS-DEV-097`: whitespace runaway despite
the requested output cap; `PPS-DEV-182`: `{"v` truncation), and were safely
zero-filled after the configured attempts. Validation passed, but logged the
usual non-fatal evidence warnings. This is a diagnostic result, not a
submission promotion: local runtime and malformed-output resilience must be
tested in the actual vLLM package before any such decision.

## Consequence

Output scope is a genuine signal: it reproduces on fast-20, independent
holdout-20, and dev-200. It is not yet a general solution. The next prompt
audit must explain why shrinking the G01 output scope harms its 19 items while
the same operation substantially helps G02; do not introduce item-level label
rules from these dev labels.
