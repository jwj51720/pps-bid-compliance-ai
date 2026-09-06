# INC-067: Gemma 4 Thinking-Mode Transport Gate Result

## Result

| Arm | Exact valid | Completion tokens | Reported reasoning tokens | Visible thought marker |
|---|---:|---:|---:|---:|
| Standard system instruction | 6/6 | 234 each | 0 each | 0/6 |
| System instruction beginning with `<|think|>` | 6/6 | 234 each | 0 each | 0/6 |

The synthetic 24-field strict JSON object is transport-safe with a
256-token reservation; this independently explains why the 128-token final
objects in INC-066 could not close.  The reported total cost was `$0.00136476`.

However, the thinking-trigger arm has no observable difference from standard:
the exact output size, visible output form, and provider-reported reasoning
usage are identical in all six paired repetitions.  This does not prove that
the provider removed an internal model mechanism.  It proves that this route
does not expose a measurable, reproducible thinking-mode variable while strict
JSON is required.

## Decision

**Reject thinking-trigger prompt changes as a decision experiment variable.**
There is no controlled provider-level activation signal to test against legal
F1.  Do not infer hidden thinking quality from the official Gemma capability,
and do not spend a full-notice budget on a text token that has no observed
effect here.  Retain the 256-token flat-object reservation only as a transport
fact for future 24-label experiments; it is not a score-tuned cutoff.

Official reference consulted: Google’s Gemma 4 prompt-formatting and thinking
documentation describes the system-role trigger, but the OpenRouter strict
JSON route did not surface it in this audit.

## Reproduction

```bash
python incubator/src/inc067_gemma4_thinking_transport_audit.py --mode preflight
python incubator/src/inc067_gemma4_thinking_transport_audit.py --mode run
python incubator/src/inc067_gemma4_thinking_transport_audit.py --mode aggregate
```
