# INC-050: Competition-Product Applicability Fact-Sheet Pilot Result

## Validity outcome

**Unscorable; no treatment conclusion.**  The protocol required complete
paired repeats.  After 144 initial calls and one preregistered identical
recovery call for each malformed response, four record/arm cells remained
unparseable:

| Arm | Valid / 36 | Remaining malformed IDs |
|---|---:|---|
| `control_r1` | 36 | none |
| `facts_r1` | 34 | PPS-DEV-121, PPS-DEV-057 |
| `control_r2` | 35 | PPS-DEV-060 |
| `facts_r2` | 35 | PPS-DEV-068 |

All failures had the same transport shape: the response started a JSON object
then produced whitespace until OpenRouter returned exactly 8,192 completion
tokens.  This occurred despite requesting strict JSON schema and
`max_tokens=500`; the provider-reported completion limit was 8,192.  The
initial attempt and its usage are retained under `initial_attempt` for every
recovered record.  Twenty-one of 25 initial format failures recovered on the
one permitted retry, demonstrating that they are not negative judgments; the
remaining four prevent an unbiased paired score.

Actual reported cost including failed and recovery calls was $0.23548565,
within the predeclared $0.40 ceiling.

## What is and is not learned

The one complete arm, `control_r1`, produced target Macro F1 0.18706 on the
36-notice pilot (v10 0.000, v11 0.000, v12 0.36364, v13 0.38462).  It is **not
a comparator result**: neither fact arm completed, and the second control is
also incomplete.  No per-item correction, prompt choice, or product-policy
decision may use this value.

The engineering result is useful and general: strict schema plus an advertised
short completion cap does not by itself guarantee bounded structured output on
this provider/model route.  Before the next paid Gemma treatment, the shared
incubator transport must have an explicit malformed-output recovery contract
and must separately profile provider-enforced completion behavior.  Simply
increasing the requested output cap is not a remedy—the failure already spent
the provider's 8,192-token ceiling as whitespace.

## Decision

Do not rerun INC-050 with a wording tweak, retry more than once, drop failed
rows, or compare incomplete arms.  Its factual applicability hypothesis remains
untested.  The next broad work item is an offline/low-cost structured-output
transport audit that compares schema representations and validates whether a
provider response can be bounded and recovered without silently changing a
legal-decision prompt.  Only then can this frozen product fact-sheet pilot be
re-executed as a new, explicitly named experiment.
