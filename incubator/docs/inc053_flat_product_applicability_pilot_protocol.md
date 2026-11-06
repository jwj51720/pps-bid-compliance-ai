# INC-053: Flat-Transport Competition-Product Applicability Pilot

This is a new execution of the frozen INC-050 product applicability hypothesis,
not a repair or continuation of its predictions.  It retains the exact same
36-notice cohort selection, full ordered notices, metadata, fact-sheet text,
candidate-line construction, four v10--v13 definitions, control/facts arms,
two repeats, model, seed, and scoring gates.

The sole changed variable is response transport, justified by INC-051 and
INC-052.  Instead of nested objects, every response has flat fields:

```text
v10, v11, v12, v13: 0 or 1
e12, e13: -1 for no evidence, otherwise zero-based index in the supplied
           unchanged candidate-line list
```

`v10`/`v11` remain absence items.  `v12`/`v13` positives without a valid
candidate index are downgraded to zero.  A missing candidate never requires a
zero judgment because the full notice remains available.  INC-052 validates
this field shape 10/10 without competition data.  The same $0.40 cost ceiling
and both-repeat promotion gate from INC-050 apply.

INC-050 remains unscorable and is never used as a control, seed result, or
partial ensemble.
