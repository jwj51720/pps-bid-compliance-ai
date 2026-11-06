# INC-051: Structured-Output Transport Audit Result

## Result

| Representation | Calls | Valid | Cap breaches | Reported cost |
|---|---:|---:|---:|---:|
| Nested strict JSON schema | 1 | 0 | 1 | $0.0032844 |
| Flat strict JSON schema | 10 | 10 | 0 | $0.0001480 |
| JSON-object mode | 10 | 10 | 0 | $0.0001480 |

The nested-schema arm's very first response consumed 8,192 completion tokens
of whitespace, violating the requested 64-token cap.  Per the preregistered
early-rejection amendment, its in-flight next request was terminated and no
further identical nested calls were made.  Flat strict-schema and JSON-object
mode both returned exactly the expected four binary values in all ten
repetitions; each reported 26 completion tokens.

The complete audit cost was $0.0035804.  It used no competition data or labels.

## Decision

**Promote flat strict JSON schema as the current binary-decision transport
contract.**  It meets the 10/10 validity and completion-bound gate.  Reject
the nested object-per-item schema for this provider/model route.  JSON-object
mode also passes this synthetic transport test, but flat strict schema has the
stronger field-level contract and is preferred for the next isolated test.

This does not prove that a flat schema with dynamic evidence candidate IDs is
safe.  INC-050 needs exactly that shape for v12/v13.  Before rerunning any
product judgment, run a small no-competition-data audit with flat binary fields
plus flat candidate-index fields.  If it passes, rerun INC-050 under a new
experiment id with only the response transport changed; do not mix or score
the failed INC-050 records.

## Reproduction

```bash
python incubator/src/inc051_structured_output_transport_audit.py --mode preflight
python incubator/src/inc051_structured_output_transport_audit.py --mode run
```
