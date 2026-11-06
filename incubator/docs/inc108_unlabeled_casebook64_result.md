# INC-108: checkpointed 64-notice unlabeled casebook scale — passed

This run changed only corpus coverage from the INC-107 contract.  It used the
next 64 fixed, label-free rows of the INC-080 manifest, full original notices,
high-reasoning compact labels/signatures (8,192 cap), immutable dynamic
positive-only evidence (medium, 2,048 cap), and the deterministic source-span
resolver.

| Measure | Result |
| --- | ---: |
| Stage-A records | 63 / 64 (98.4%) |
| Stage-B records for successful Stage A | 63 / 63 |
| Teacher-positive labels | 25 |
| Exact resolved positive source evidence | 24 / 25 (96.0%) |

The one Stage-A loss was an explicit `max_output_tokens` incomplete response;
it remains a recorded failure and was not replayed.  The one unresolved v24
positive had an empty model quote, not a fabricated source string.  The
permitted record-quality gate is met (>=98% schema success and >=90% grounded
positive evidence).  The resulting label distribution contains 13 item types,
including v2/v3/v4/v6/v7/v9/v10/v13/v15/v17/v19/v22/v24.

This is not a claim about teacher accuracy or leaderboard score.  It authorizes
only the next experiment: a fixed dev direct-versus-case-RAG Gemma ablation
using this static, unlabeled-only casebook.  Do not use dev labels as retrieved
cases or scale to 20k before that ablation.
