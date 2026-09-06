# INC-048 Result: Source Fragment Ontology

## Result

The audit supports complete unchanged source lines as the first evidence
retrieval unit. For the many items with nonempty organizer dev evidence, line
coverage is generally 100% (including v2, v3, v4, v7, v9, v19, and v22).
Punctuation-bound sentence fragments frequently split table/layout evidence and
lose containment: v2 is 42.9%, v7 42.9%, and v22 40.0% on their nonempty gold
evidence subsets.

There are 93,748 source lines and 141,266 sentence spans across dev; only 51
source units exceed 500 characters. Several labels have mostly empty organizer
evidence cells, so this audit measures supplied-evidence preservation rather
than proving that other positives have no source evidence.

## Decision

Use unchanged source lines as immutable retrieval/evidence candidates. Do not
mechanically split lines for final evidence. Token-level and sentence fragments
may support lexical/BGE indexing but cannot be selected as final evidence unless
they themselves are unchanged, contained, and ≤500 characters. This is a
foundation for the proposed extract→retrieve→candidate-ID adjudication route,
not a score improvement by itself.
