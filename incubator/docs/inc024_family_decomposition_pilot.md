# INC-024: Joint Output versus Family Decomposition

## Question and controlled comparison

Does splitting a complete notice into four fixed output families improve the
judgment mechanism, independently of RAG, law cards, input truncation, or
candidate selection? The pre-registered protocol is in
`inc024_family_decomposition_preregistration.md`.

Both arms received identical complete ordered documents and metadata. The
control made one 24-item call; treatment made four calls for the fixed families
and concatenated their disjoint outputs. Neither arm received legal text,
product facts, candidate windows, nor any length-based context rule.

## Execution

- Cohort: 12 deterministic label-stratified notices, ID hash
  `0105e8a1fd76b8df621bf49c010d61b25144d6046e9d3963ea1da2e8c074c546`.
- Calls: 60 / 60 successful; no provider context rejection or parse failure.
- Cost: `$0.09153945` (predeclared ceiling `$0.50`).
- Source and prompt hashes, responses, predictions, and metrics are retained
  under ignored `incubator/runs/inc024_family_decomposition_pilot/`.

## Result

| Arm | Macro F1 | TP / FP / FN | Micro recall | Evidence validity |
|---|---:|---:|---:|---:|
| Joint 24-item | 0.15933 | 8 / 15 / 11 | 0.42105 | 1.000 |
| Four families | 0.12460 | 9 / 19 / 10 | 0.47368 | 1.000 |
| Family − joint | -0.03472 | +1 / +4 / -1 | +0.05263 | 0.000 |

The changed-cell ledger contains 6 corrections and 9 introduced errors. The
additional recall came mainly from v17 and v21, but it did not form a safe
family-wide effect: the treatment lost the sole v2 true positive and added
new positives to all-negative notices (notably v3, v15, v17, v23, v24).
The products family remains structurally unstable: v13 produces seven false
positives even in the treatment, and v12/v14/v15 positives were still missed.

## Decision

**Failure.** The pre-registered success gate required at least four net
corrected cells, no family recall loss beyond two cells, and no all-negative
notice with more than one new positive. The observed net is -3, and the
all-negative safety condition fails. Output-family decomposition is therefore
rejected as a standalone global architecture and will not receive a prompt
repair or dev-200 confirmation.

The meaningful next direction is not a fifth wording of this decomposition.
It is a separate evidence-first candidate architecture: evaluate offline
whether a provenance-preserving candidate extractor covers each non-absence
gold evidence while rejecting hard-negative cues, then let Gemma adjudicate
only source-local candidates. Absence and metadata-comparison items remain
separate full-coverage/typed-fact tasks. This changes the information supplied
to the model, rather than merely changing the number of output calls.
