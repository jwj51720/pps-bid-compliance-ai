# INC-008: Full-Notice Exact-Admission Pilot

INC-007 shows that full notices fit the actual Gemma prompt budget across all
dev-200 notices. This paired pilot tests whether the INC-006 coverage gain
continues when the arbitrary 12,000-character prefix is replaced by the full,
exact-token-admitted notice.

The frozen 24-notice cohort, Joint-24 prompt, metadata, system prompt, model,
seed, output schema, output cap, and evidence validator are identical. The
only change is source context: ordered 12,000-character prefix versus all
ordered source documents. Preflight rejects a notice if full input exceeds the
30,268-token budget; no silent truncation or multi-pass merge occurs in this
pilot.

Success requires full-notice Macro F1 at least the prefix arm plus 0.02,
non-decreasing micro recall, evidence-validity decline no worse than 0.05, and
no item with more than three new false positives. If it succeeds, the full
notice policy—not a fixed character count—receives a dev-200 confirmation.

## Result

All 48 requests succeeded with `stop` finish reasons and unique checkpoint
keys. The full-notice arm used 312,563 prompt tokens versus 188,885 for the
prefix arm, and cost $0.04767 versus $0.03206.

| Policy | Macro F1 | TP / FP / FN | Micro recall | Evidence validity |
|---|---:|---:|---:|---:|
| 12,000-character prefix | 0.15899 | 9 / 29 / 28 | 0.24324 | 0.81579 |
| Full exact-admitted notice | 0.15926 | 10 / 28 / 27 | 0.27027 | 0.76316 |

The full arm gained one TP and removed one FP, but Macro F1 changed by only
+0.00026, far below the +0.02 gate. Evidence validity declined by 5.26
percentage points, slightly beyond the -0.05 safety limit. It also consumed
about 66% more prompt tokens and $0.01560 more API cost for the cohort.

## Decision

**Failure: reject generic full-notice expansion.** INC-006 established that a
very short prefix is inadequate; INC-008 establishes that whole-notice context
does not turn that coverage signal into a general solution. Neither 12,000
characters nor full context becomes a final policy.

The next branch should select *relevant* source spans rather than tune a global
length. Build an offline, deterministic candidate-window audit first: sentence,
paragraph, and table-row spans with source offsets; lexical/numeric cues and
metadata fields linked to item families; and per-item positive/hard-negative
coverage. Its first paid test should compare a fixed Joint-24 prefix against an
active item-family prompt supplied with only the source-local candidate windows
and exact metadata facts. It must not add a broad legal bundle or a new global
context length in the same experiment.
