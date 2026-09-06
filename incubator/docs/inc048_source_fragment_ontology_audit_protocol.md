# INC-048: Source Fragment Ontology Audit

## Purpose

Build the non-learned source side of the proposed extract→retrieve→adjudicate
architecture before any more provider spend. This is a global evidence
infrastructure audit across all 24 items, not a label classifier.

## Frozen fragmentation

For every original document retain three nested, unchanged fragment types:

1. the complete nonempty line;
2. punctuation-delimited sentence-like spans within that line (Korean/Latin
   terminal punctuation, table delimiters, and bullet boundaries); and
3. whitespace-delimited tokens for retrieval indexing only, never as submitted
   evidence.

No fixed character window, dev-selected maximum segment length, rewriting, or
cross-line concatenation is allowed. A selectable evidence fragment is a line
or sentence span at most 500 characters; longer units remain provenance records
but are not automatically shortened.

## Audit

Using organizer dev evidence solely for measurement, report per-item positive
gold-evidence coverage by line and sentence fragment, empty-evidence positives,
over-500 fragments, candidate cardinality, and document-type provenance. This
does not change predictions and does not infer that missing supplied evidence
means source evidence is unavailable.

## Gate

Only a fragmentation level that preserves source containment and broad
nonempty-evidence coverage may feed a future lexical/BGE retrieval experiment.
Retrieval will rank these immutable fragments; it must return an ID whose
original source span becomes final evidence.
