# INC-107: compact two-pass casebook transport gate — passed

Eight fresh unlabeled notices used the same compact Stage-A label/signature
contract as INC-106, with high-reasoning output cap 8,192, followed by the
immutable-label, dynamic-positive-only Stage B.

| Gate | Result |
| --- | ---: |
| Stage A schema-valid | 8 / 8 |
| Stage B schema-valid | 8 / 8 |
| Stage-A positive labels | 3 |
| Positive evidence resolved to unchanged source substring | 3 / 3 |

One quote crossed a table-cell insertion in the source.  The deterministic
resolver returned the unique <=500-character original window including that
intervening source text; it did not synthesize a cleaned sentence.  Resolver
tests cover exact, anonymization-tag omission, duplicate exact text, ambiguous
normalization rejection, and this ordered-anchor case.

This passes only the **transport/provenance** gate.  It does not establish
teacher label accuracy or a dev score.  The next authorized action is a
checkpointed 64-notice unlabeled casebook scale run, then a direct-vs-case-RAG
Gemma ablation on dev.
