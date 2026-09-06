# EXP-123 public-submission decision dossier

## Exact artifact

- Archive: `dist/pps_20260906_233304.zip` (submitted)
- SHA-256: `9b28391d63e2f8a4dcf42af8b225de30c3479dce96df310c17572b599e8b0907`
- Policy: EXP-120's single full-notice Gemma V/E call, card-v6, ordered
  4,000-character context, plus the source-complete frozen overrides for v2,
  v3, and v21.

## What is and is not changed

The archive retains the required actual-notice Gemma call for every notice.
Only v2/v3/v21 are replaced after normal pipeline finalization.  The other 21
labels and all their evidence stay on the EXP-120 path.  The overrides are not
lexical score tuning:

- v2 requires the organizer-provided 230M statutory amount, a below-threshold
  notice estimate, and explicit bidder-performance eligibility source text;
- v3 requires exactly one explicit qualification-performance amount at least
  the raw allocation budget;
- v21 requires an explicit joint-contract share below the statutory default,
  excluding divided-performance contracts.

## Validation completed

1. ZIP integrity test passed; archive contains 18 required source/static
   members, including `src/frozen_rules.py`.
2. A fresh extracted staging directory ran `script.py --mock` against the
   organizer mock fixture without exception.
3. The staged CSV has 49 ordered columns, 10 fixture rows, and unique IDs.
4. The 20,000-record format audit found positive activation rates v2 `0.850%`,
   v3 `0.410%`, v21 `0.045%`; all positive evidence is an unchanged source
   substring at most 500 characters.
5. The fixed INC-076 folds improve independently: `+0.056944` and `+0.083333`.

## Score expectation and risk

| Policy | Local dev200 | Public leaderboard |
|---|---:|---:|
| EXP-120 submitted control | 0.248932 | 0.244317 |
| EXP-123 candidate | 0.317797 | unmeasured |

The EXP-120 local/public delta (`-0.004615`) shows this policy family can align,
but it does **not** prove EXP-123's `+0.068865` transfers.  The three rules
were discovered and audited on dev200, so a public submission is the only
valid generalization measurement.  A result above EXP-120 promotes the
candidate; a result materially below it rejects the rule-composition transfer
and closes further dev-derived rule expansion.

## Archive correction

`pps_20260907_001734.zip` was a later duplicate repackage with identical member
contents, not a new policy. It was never a distinct submission candidate and
has been removed to prevent ambiguity. The archive named above is the only
EXP-123 artifact submitted to the public leaderboard.
