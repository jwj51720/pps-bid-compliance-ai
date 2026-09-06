# INC-068: Same-Conversation Self-Deliberation Pilot

## Question

Can Gemma retain its own provisional, full-notice legal analysis as an
assistant turn and then improve a fresh final 24-label decision, compared with
one direct complete-notice 24-label decision?

## Controlled topology

INC-027 used a separate typed fact ledger, source-evidence gate, and a second
adjudicator.  This experiment does none of those things.  The treatment uses
one conversation: the first response is a compact provisional 24-item legal
memo without quotes, line IDs, or submission evidence; the second user turn
explicitly calls that memo fallible and asks the same assistant to recheck the
original full notice already retained in the conversation before returning the
final flat labels.  No memo statement is a retrieval, evidence, or label gate.

The control is the same system instruction, metadata, complete ordered notice,
model, seed, and final flat 24-label schema, without the assistant memo turn.

## Cohort, transport, and decision

Use the fixed 20-notice positive-cover seed inherited from INC-054/066 and
two repeats.  Final labels reserve 256 completion tokens: INC-067 demonstrates
that a complete flat 24-label object serializes at that capacity, while
INC-066 demonstrates 128 can truncate before closure.  The memo reserves
1,024 tokens as a transport capacity for coverage of 24 task headings; a
memo missing any heading or ending from output exhaustion invalidates its
repeat.

Score only fully valid paired repeats, reporting Macro F1, TP/FP/FN,
per-item metrics, and changed cells.  Advance only if both treatment-control
deltas are strictly positive and each repeat has more corrected than newly
wrong cells.  Otherwise reject without prompt repair or dev-200 escalation.
Maximum cost is `$0.50`.
