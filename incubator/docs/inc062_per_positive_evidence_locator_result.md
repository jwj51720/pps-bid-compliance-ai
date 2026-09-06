# INC-062: Per-Positive Source-Line Locator Result

The locator completed all 71 fixed non-absence positive jobs from INC-041 on
the INC-054 cohort.  Every response parsed and selected a valid nonnegative
unchanged source line no longer than 500 characters; no response returned
`-1`.  Reported cost was $0.0792197.

For the limited subset where the fixed upstream cell is dev-positive and the
organizer supplied nonempty evidence, 8/11 selected source lines contain the
organizer evidence verbatim.  The three misses are `PPS-DEV-01/v1`,
`PPS-DEV-23/v9`, and `PPS-DEV-03/v2`.

## Decision

**Advance evidence transport only.**  Separating location after a single fixed
positive claim solves the semantic contract failure of INC-060 (71/71 valid
IDs versus its many positive-without-ID cells).  It does not establish label
accuracy, evidence semantic correctness on all cells, or a Macro F1 gain.
Any final policy must separately audit semantic grounding and runtime cost on
the actual upstream prediction schedule.  It must never turn locator failure
into a label change without a preregistered decision experiment.
