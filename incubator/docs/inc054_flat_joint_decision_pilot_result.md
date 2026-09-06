# INC-054: Flat Joint-24 Decision-Only Result

All 96 calls parsed successfully, so this is a valid label-quality diagnostic.
The flat decision-only topology failed both repetitions against the immutable
INC-041 reference on the same 48 notices:

| Arm | Macro F1 | Delta vs INC-041 |
|---|---:|---:|
| INC-041 reference | 0.30907 | — |
| Flat label-only r1 | 0.20584 | -0.10323 |
| Flat label-only r2 | 0.26547 | -0.04361 |

The output contract itself was stable, but removing evidence generation did
not improve legal attention.  Both runs lost much of the reference's v2/v3/v21
performance; r1 also produced four v3 false positives.  Some unrelated items
rose in one repeat (for example r2 v6/v20), but the changes are sparse and
inconsistent and cannot offset the loss.

**Reject decision-only output separation.**  Do not run an all-dev version,
recover evidence after the fact, or combine it with the reference.  Flat fields
remain the required transport representation, but the model must continue to
perform source-grounded decision/evidence work in a later end-to-end topology.
Reported diagnostic cost was $0.0864152.
