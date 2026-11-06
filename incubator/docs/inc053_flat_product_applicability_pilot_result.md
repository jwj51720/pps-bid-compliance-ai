# INC-053: Flat-Transport Competition-Product Applicability Result

## Validity

All 144 calls completed and parsed successfully (36/36 in every arm).  This
confirms the flat response transport fixed INC-050's nested-schema failure
without altering full-notice input or the frozen product experiment design.
Reported cost was $0.12221215.

## Paired outcome

| Repeat | Control Macro F1 | Fact-sheet Macro F1 | Delta |
|---|---:|---:|---:|
| r1 | 0.16450 | 0.11513 | **-0.04937** |
| r2 | 0.24444 | 0.14643 | **-0.09802** |

The direction is consistently negative.  The fact sheet reduced v12 false
positives (r1: 4 to 1; r2: 3 to 0), but it did not recover its five missed
positives in either repeat.  More importantly it harmed v13: F1 fell from
0.47619 to 0.21053 in r1 and from 0.55556 to 0.30000 in r2, driven by lost true
positives (5 to 2, then 5 to 3) without a compensating false-positive drop.
v10/v11 remained near-zero recall in every arm.

The variation between controls (0.16450 vs 0.24444) reinforces why both
repeats are required, but it cannot explain the concordant treatment loss.

## Decision

**Reject the product applicability fact-sheet topology.**  It fails every
promotion condition: neither repeat improves target F1, target recall declines
for the important non-absence item v13, and the direction is consistently
negative.  Do not run an all-dev confirmation, reword this sheet, or compose
any product correction from it.

What remains reusable is infrastructure only: full-notice flat binary/candidate
index transport had 100% call validity, and source candidates retained their
unchanged evidence contract.  The next broad branch should not add another
product fact card; it should address a distinct residual family or a different
decision topology.

## Reproduction

```bash
python incubator/src/inc053_flat_product_applicability_pilot.py --mode preflight
python incubator/src/inc053_flat_product_applicability_pilot.py --mode run-all --workers 16
python incubator/src/inc053_flat_product_applicability_pilot.py --mode aggregate
```
