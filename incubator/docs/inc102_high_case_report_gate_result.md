# INC-102: high-reasoning direct case-report gate — rejected

All 16 pre-frozen structural notices completed, and all 12 predicted-positive
quotes were unchanged source substrings.  The 8,192 cap therefore resolves the
high-reasoning output-completeness problem for this output contract.

It did not improve the decision metric:

| Same 16 IDs | Macro positive F1 |
| --- | ---: |
| INC-088 direct high | 0.15278 |
| INC-102 high case report | 0.15278 |

There were four changed labels: three direct false positives became correct
zeros (`v10`, `v13`, `v7`), but one new v23 false positive offset them under
the macro-F1 objective.  This is useful precision behavior, but the
predeclared positive-delta gate fails.  Do not scale this as a direct-label
topology or construct a label-wise merge.

The validated positive quote rate does support a different, non-score claim:
the case-report format can serve as a provenance-bearing *teacher-record*
contract for the permitted unlabeled casebook branch, which is tested
separately in INC-103.
