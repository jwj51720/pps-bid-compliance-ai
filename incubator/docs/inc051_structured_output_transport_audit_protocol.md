# INC-051: Structured-Output Transport Audit

## Purpose

INC-050 showed a critical confound: some strict-schema responses ignored the
requested 500-token cap and emitted whitespace through the provider's 8,192
completion-token ceiling.  This experiment isolates output transport from legal
reasoning, documents, labels, retrieval, and prompt quality.  It asks which
compact response representation can reliably carry four binary decisions on
the current Gemma/OpenRouter route.

## Fixed request

Every request uses the same model, temperature, seed, provider routing,
`max_tokens=64`, and a synthetic instruction to output the fixed values
`v10=0, v11=1, v12=0, v13=1`.  No competition notice, dev label, or legal text
is sent or evaluated.  The expected values make semantic correctness
irrelevant: only schema/transport validity is measured.

Three representations are compared, ten independent requests each:

1. `nested_schema`: the object-per-item pattern used by INC-050, but without
   evidence IDs;
2. `flat_schema`: a strict schema with four integer fields directly;
3. `json_object`: OpenRouter JSON-object mode with the same flat fields stated
   in the prompt; Python validates keys and integer values.

The order is deterministically interleaved by repetition to avoid assigning a
transient provider period to one arm.  A response is valid only if JSON parses,
has exactly the four required keys, and has the expected values.  Whitespace,
extra text, wrong keys, wrong values, HTTP failures, and a completion count
above 64 are failures.

### Early rejection amendment

The first `nested_schema` request breached the 64-token cap by emitting 8,192
whitespace tokens.  A cap breach already satisfies that arm's reject condition,
so no additional identical nested requests are informative and they only risk
repeating the known runaway charge.  The in-flight second nested request was
terminated before a response was recorded.  Subsequent repetitions retain the
same original flat-schema and JSON-object requests, interleaved with each
other; the nested arm is reported as early-rejected with one observed call.

## Cost and decision

There are 30 calls.  The ceiling is $0.12, calculated conservatively from the
observed failure cost in INC-050; execution stops before a new request if the
recorded spend would exceed the ceiling.

- **Advance:** an arm has 10/10 valid outputs and every provider-reported
  completion is at most 64 tokens.  It is eligible as the transport format for
  a later decision experiment.
- **Partial:** at least 9/10 valid, no cap breach, and a clearly lower failure
  rate than the other formats.  Use only with a bounded recovery policy.
- **Reject:** any cap breach, no arm at 9/10, or cost failure.  Do not run
  another large prompt treatment before changing provider/model transport.

This selects a transport contract only; it does not select a legal decision
prompt, evidence policy, or submission output format.
