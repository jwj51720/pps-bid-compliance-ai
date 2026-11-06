# INC-052: Flat Candidate-Field Transport Result

All ten synthetic strict-schema requests returned the exact expected flat
binary and candidate-index fields.  Every provider-reported completion was
within the requested 64-token cap; total reported cost was $0.0003002.

**Advance.**  Flat integer candidate indices are an admissible replacement for
the nested `{"위반여부", "evidence_id"}` response object on this model route.
Together with INC-051, this isolates INC-050's persistent malformed outputs to
the nested-schema representation rather than candidate enumeration itself.

The next product experiment must receive a new ID and preserve INC-050's
cohort, prompts, fact sheet, model, settings, and evaluation gates.  Only the
response transport may change: four flat `v*` binary fields and flat `e12/e13`
candidate-index fields (`-1` for none).  INC-050 remains unscorable and is not
combined with the new run.
