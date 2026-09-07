# INC-026: Structural Evidence Candidate Audit

## Result

INC-026 replaced character-radius lexical windows with intact original
paragraph/table-row blocks. It made no API call, no prediction, and no
label-derived cue edit.

The audit found that the source text itself is consistent with every nonempty
gold evidence substring: there were zero attribution failures. But the dev
evidence field is incomplete for this use. Of 122 non-absence positive cells,
only 54 have nonempty gold evidence and 68 are blank. Blank evidence is
unavailable supervision, not a source or extractor failure.

Among items with enough nonempty evidence to diagnose the method:

- v2 reached 6/7 complete-evidence coverage but had a 52.8% negative candidate
  rate.
- v3 reached 8/8 coverage but a 96.9% negative candidate rate.
- v7 reached only 1/7 coverage; v9 1/3; v22 4/5; and v23 1/5.
- Several apparently perfect scores are based on only one or two nonempty
  evidence cells and are explicitly not promotion evidence.

## Decision

**Failure as a global source-aware candidate gate.** It does not satisfy the
pre-registered requirement of 90% coverage for every non-absence item, and the
available evidence labels are too incomplete to certify broad coverage. Cue
absence must not suppress any final positive. The result also refutes a simple
claim that intact structural blocks alone solve the generic-cue problem: v3
retains near-universal negative activation.

The next architecture should not select source text from lexical cues alone.
The remaining generalizable path is structured fact extraction from explicit
field/value relations (amount, date, ratio, product code, contract method,
and document role), with each extractor audited against raw text independently
of sparse evidence labels. This is a different information representation,
not a third candidate-window repair.
