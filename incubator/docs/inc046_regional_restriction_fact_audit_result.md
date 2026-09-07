# INC-046 Result: Regional-Restriction Fact Audit

The audit does not authorize a regional automatic rule. v5, v6, and v8 source
facts miss one positive each; generic regional facts activate in about 47% of
their negatives. Although v7 fact coverage is complete, its negative activation
is also 46.6%, and three v7 positives lack a metadata region-code value.

All positives have contract law, estimated price, regional-restriction flag,
and method metadata, but several lack region codes. Therefore a code-only
hierarchy or a generic source cue would both be unsound. The low 2.1% v8
conjunction activation is promising as a future fact *review* stratum, but its
missing positive blocks it as a candidate gate.

Decision: park the v5--v8 automatic branch. Do not introduce a dev-derived
regional lexicon or use generic region facts as a negative gate. This preserves
the family for a future source-grounded, law-complete method only after its
missing layout cases and administrative-unit ontology are independently solved.
