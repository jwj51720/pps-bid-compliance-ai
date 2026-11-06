# INC-067: Gemma 4 Thinking-Mode Transport Gate

## Rationale

The official Gemma 4 documentation states that Gemma 4 supports a system role
and an explicit thinking trigger (`<|think|>` at the start of the system
instruction).  The current experiments use neither.  Before changing a
competition prompt, this synthetic audit asks whether the OpenRouter
`google/gemma-4-26b-a4b-it` route preserves a thinking-mode request while
still returning a complete strict flat JSON object.

## Frozen synthetic task

There is no competition document or label.  Each response must emit a known
24-field alternating binary object.  The two arms differ only in whether the
system instruction begins with the Gemma-4 thinking trigger.  Each arm has six
independent calls with the same provider model, seed, temperature, schema, and
256-token completion reservation.

The 256-token reserve is a transport capacity for a complete 24-field JSON
object.  It is not chosen from dev scores: INC-066 directly observed that 128
tokens can end before the final fields, while the fixed schema contains all 24
fields.

## Measurements and gate

Record strict JSON/value validity, completion usage, reported reasoning-token
usage when available, and any visible thought-channel marker.  The arm is
transport-safe only if all six outputs are complete and exact, with no request
exceeding the requested completion cap.

This audit does not claim that thinking improves legal decisions.  It only
authorizes a later paired full-notice experiment if the provider actually
preserves both thinking behavior and valid structured output.  If the trigger
is ignored, leaks thought text into JSON, raises cost beyond the small cap, or
destabilizes output, no decision experiment follows.

Maximum spend: `$0.05`.
