# INC-017: Source-Validated v20 Predicate Diagnostic

INC-015 rejected the direct law-card question because it leaked applicability:
the model often treated a missing declaration as a violation before proving the
notice was a software business. INC-017 retains the frozen law facts and full
notice, but replaces one v20 output with three source-auditable predicates:
SW applicability, declaration status, and exception status.

For a `yes` SW finding, `present` declaration, or `present` exception, the
model must return an unchanged document substring of at most 500 characters.
Python validates it. Invalid positive predicate evidence is downgraded to
`uncertain`; all unknowns merge conservatively to v20=0. The merge emits v20=1
only for `SW=yes AND declaration=absent AND exception=not_present`.

This is a 200-notice all-dev experiment. Its preregistered success condition
is v20 F1 above the no-card INC-015 control (0.60), FP at most 2, recall at
least 0.60, and no transport/schema failure. It is a new policy candidate, not
a root-pipeline change.

## Result

All 200 calls returned valid schema output at $0.32832, below the $0.50 ceiling.
The deterministic predicate merge produced TP/FP/FN 3/14/2 (precision 0.17647,
recall 0.60, F1 0.27273), failing every performance gate except transport.
The model emitted declaration `absent` for 198/200 notices, so merely splitting
the field did not make it recognize an existing declaration. Ten invalid
positive-predicate evidence strings were conservatively downgraded; two were
labeled positives.

Post-hoc inspection is diagnostic only, not a new result: accepting the raw
model predicates and requiring the offline SW candidate would restore all five
positives but still yield 9 FP (F1 0.52632); additionally masking the two
declaration candidates yields 8 FP (F1 0.55556). Neither beats the 0.60
no-card control, and these variants must not be selected from the same dev set.

Decision: reject the decomposed v20 predicate policy. The bottleneck is not
token admission or an absence merge; it is trustworthy semantic recognition of
the required declaration. Further v20 wording/postprocessing sweeps would be
dev-overfitting. Park v20 and redirect the next research cycle to another
high-error item with a clearer source predicate.
