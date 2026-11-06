# INC-038 Result: Qualification-Family Fact Coverage

## Outcome

This audit emits no violation label. It found complete positive fact coverage
for v1, v2, v4, and v7; v5/v6/v8 each missed at least one positive under the
frozen regional marker, and v9's task-document-only assumption covered none.

The useful result is not the raw coverage alone. v1's institutional fact marker
activates on 94.8% of negatives and the regional marker on about 65.8%, so they
are far too broad for a direct rule. In contrast, the performance-amount fact
has 100% v2 coverage with a 15.0% negative candidate rate; the v4 conjunction
of performance and institutional facts has 100% coverage with a 15.5% negative
candidate rate. They are candidates for a legal-role analysis, not for direct
prediction.

## Rejected assumption

v9 is named as a task-document model issue, but its gold evidence occurs in
heterogeneous document forms including specifications and notices; a
`과업지시서`-only extractor has 0/6 coverage. Do not repair this by adding
development-case model strings. Any future v9 method must first define a
document-type-independent brand/model fact shape.

## Next direction

Analyze v2 and v4 together using the same complete performance facts plus the
organizer's high/low-price applicability and specific-institution legal roles.
The first step is a fact and law applicability audit—not another threshold
rule—because the two labels overlap in several notices and generic amount
comparison already belongs to frozen v3.
