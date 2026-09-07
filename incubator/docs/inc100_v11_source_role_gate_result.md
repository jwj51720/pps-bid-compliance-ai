# INC-100: v11 source-role diagnostic gate — stopped

## Transport correction

The first ten-call diagnostic had a response-recording defect: OpenAI returned
`200/completed` but the script did not retain its content when its parser found
none.  Those outputs cannot be reconstructed because `store=false`; they are
invalid and are not scored.  The recorder was fixed and one bounded transport
probe was then run.  No remaining cohort call was made after the probe.

## Probe result

`PPS-DEV-14` has a direct-production certificate as a bidder qualification and
is a dev v11 positive.  The corrected probe emitted:

```json
{
  "applicability": "competitive",
  "source_role": "bidder_eligibility",
  "restriction_status": "required_competition_restriction_present",
  "v11": 0
}
```

The source-role part is reasonable, but the legal conclusion is wrong: a
direct-production certificate is the requirement relevant to v10 and does not
by itself satisfy v11's required *small-businesses-only competition*
restriction.  This is direct evidence of cross-item legal-condition
contamination, not missing source content or a token limit.

## Decision and next design constraint

INC-100 fails its predeclared gate.  Do not run the remaining nine requests or
promote INC-099's dev-only merge.  The next v11 prompt must state a mutually
exclusive condition table before asking for a label:

- direct-production certificate alone: **not** a v11 restriction;
- small-business confirmation, general SME information, or post-award policy
  notice alone: **not** a v11 restriction;
- only an actual bidder-eligibility condition that restricts competition to the
  legally required small-business group can satisfy the v11 restriction test.

This table is a restatement of the item distinction, not a fitted numerical
rule.  It must first be tested on a fresh, predeclared mechanism cohort with
the exact-code state included from the start; only then can a complete
dev-200 Luna confirmation be justified.
