# INC-129: Gemma source-grounded self-audit result

**Decision: reject.  Do not run a holdout or revise the audit wording.**

| Stage | Calls | Macro positive-F1 | Micro recall | Positive-evidence valid rate | Cost |
|---|---:|---:|---:|---:|---:|
| Direct EXP-120-equivalent V/E | 24 / 24 | 0.048611 | 0.117647 | 0.916667 | $0.03532 |
| Source-preserving audit V/E | 24 / 24 | 0.048611 | 0.117647 | 0.923077 | $0.03745 |
| Audit − direct | — | **0.000000** | 0.000000 | +0.006410 | — |

All 48 requests were schema-valid and source-evidence postprocessing completed.
The second call changed exactly one label: it turned `PPS-DEV-065/v21` from 0
to a false-positive 1, citing `제안사 단독 입찰만 가능(공동수급 불허)`.  That sentence is
an unchanged source substring, but it does not imply the item’s joint-share
violation condition.  Therefore the slightly higher positive-evidence rate is
not a quality gain.

This directly rejects the remaining source-preserving two-call idea in which a
prior V/E judgment is supplied as a claim list while the full original notice
remains available.  A second Gemma pass adds runtime and one new semantic error
without recovering any positive.  Do not use it for submission, run the
availability-constrained holdout, or make a cell-selective merge.
