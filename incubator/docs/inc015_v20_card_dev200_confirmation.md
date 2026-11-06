# INC-015: Frozen v20 Card, All-Dev Confirmation

INC-014 selected ten negatives, so it cannot establish the card's negative
behavior. This confirmation freezes the exact card SHA, system contract,
Gemma model, generation parameters, full-document rendering, and schema. It
runs each of all 200 dev notices twice: no card versus the frozen card.

The sole changed variable is the card. Exact Gemma chat-template token
admission is required before any provider request. The cost projection uses
the per-token price observed in INC-014 and must fit the registered ceiling.

Success requires higher v20 F1, non-decreasing recall, no additional false
positives, and all 400 calls to return valid structured output. Even a pass is
only an incubator candidate: integration still requires a shared-pipeline and
submission-parity proposal.

## Result

All 400 calls completed with valid structured output. Control was TP/FP/FN
3/2/2 (precision 0.60, recall 0.60, F1 0.60); the frozen-card treatment was
4/11/1 (0.26667, 0.80, 0.40). Actual cost was $0.67498, below the $1.50
ceiling and the $0.73408 projection. The success gate failed: treatment added
one true positive but nine net false positives and reduced F1 by 0.20.

The negative failure has two modes. Six of the nine newly positive negatives
had no audited SW-applicability cue, showing that the card can make absence of
the notice declaration too salient before applicability is established. Two
negatives were positive in both arms; one contains a visible
software-participation restriction, so mere fact-card context also does not
guarantee semantic recognition of a declaration. The one remaining false
negative was stable in both arms. The five labeled positives include low-price
procurement examples, so an automatic amount threshold gate would be an
unsupported and harmful repair.

Decision: reject the current single-shot law-card policy. Preserve its source
facts, but do not use this prompt/card combination as v20 treatment or merge
it into the root pipeline. The next candidate, if pursued, must be a separate
diagnostic-predicate experiment: require the model to identify a source-backed
SW-applicability finding and a source-backed declaration-present/absent finding
before a deterministic merge may emit v20. It must be audited offline first;
no amount-only, metadata-only, or cue-only gate is permitted.
