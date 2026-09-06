# INC-127: Gemma operational-contract pilot result

**Decision: reject.  Do not run the holdout or rewrite this contract on the
same cohort.**

| Arm | Macro positive-F1 | Micro recall | Absence FP | Successful calls | Cost |
|---|---:|---:|---:|---:|---:|
| EXP-120-equivalent card-v6 control | 0.111111 | 0.200000 | 0 | 32 / 32 | $0.04685 |
| Operational-contract treatment | 0.104167 | 0.200000 | 0 | 32 / 32 | $0.04836 |
| Treatment − control | **-0.006944** | 0.000000 | 0 | — | — |

All 64 responses passed transport, parsing, and source-evidence postprocessing.
The failure is therefore semantic, not a schema or retry artifact.  The added
operation sequence recovered one `v1` positive but lost the control's `v12`
positive and introduced additional v2/v4 false positives; it fails the
predeclared `+0.02` macro gate.

The cohort has low positive support, so its absolute values do not estimate
EXP-120 dev200 or public performance.  The paired negative sign, unchanged
recall, fresh label-blind cohort, and no transport failures are sufficient to
close this precise prompt-contract branch.  In particular, do not infer that
Luna's `0.427366` legal-ledger gain can be reproduced by merely explaining its
reasoning sequence to Gemma.

The next Gemma direction must be structurally different: a source-preserving
teacher-record/retrieval contract whose records are validated as helpful
*inputs*, not generic examples or a global lossy e-prime.  Before a new paid
call, audit the existing Luna ledger records for a label-blind retrieval key
and source-provenance coverage; generic case RAG and e-prime-only adjudication
remain closed.
