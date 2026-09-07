# INC-036: v3 Performance-Amount Predicate Audit

## Legal predicate shape

v3 is `실적제한 1배수 이상`; the organizer item-table note specifies the
project-budget basis. Both the national and local organizer legal packages cap
a performance-amount restriction at the relevant estimated project price. The
audit considers only an unchanged source line that is explicitly a bidder-
qualification condition: it contains (a) `실적`, (b) an explicit Korean won
amount, (c) an explicit lower-bound term such as `이상` or `초과`, and (d) a
qualification predicate (`보유`, `제출`, `있는 업체`, `있어야`, or
`입찰참가자격`). It parses that stated performance amount and compares it to
raw organizer metadata `배정예산금액`.

The frozen diagnostic is positive only if the parsed performance lower bound is
at least the budget. It requires exactly one money expression in the source
line; a missing or multiple amount, a line without the qualification/lower-
bound condition, or missing budget is unknown/zero. No character window,
learned normalization, metadata bin, model output, or dev-derived amount is
used.

## Guardrails

This is a diagnostic, not a final rule. It must retain unchanged source-line
evidence and report all multi-amount lines/parse ambiguities. An amount written
in a different legal role is never selected by a proximity heuristic or by
choosing a maximum: the audit takes only a single explicit line-level bidder-
qualification performance expression.

The audit may advance only if all v3 positives are covered, no negative is
made positive, and the cited legal default has no unrepresented exception in
the resulting positives. Otherwise the fact extractor is retained without a
prediction rule.
