# INC-131: v9 specification-second-pass feasibility audit

## Question

EXP-120's ordered 4,000-character input can place a specification after the
announcement.  Since INC-074 attributes every **nonempty** v9 organizer
evidence string to a specification, could a complete-specification second pass
be a source-topology justified correction?

## Offline source check

All six dev v9 positives were inspected only for document availability and
organizer evidence placement:

| Positive type | Count |
|---|---:|
| Specification contains nonempty organizer v9 evidence | 3 |
| Specification exists but organizer v9 evidence is blank | 2 |
| No specification document | 1 |

The three evidenced specifications are 2,493, 5,016, and 8,748 characters;
other positive specifications are 7,005 and 8,222 characters.  Thus a fixed
4,000-character specification prefix would itself be an arbitrary and
incomplete input policy.  Full specification admission would require exact
token packing/splitting, while still leaving one positive with no specification
and two positives without source evidence.

INC-047 independently found generic technical/product identifier cues in
95.4% of v9 negatives.  A specification pass can therefore locate text but
does not supply a complete binding-specification-versus-description predicate.

## Decision

Do not launch a v9 specification-only second-pass experiment or construct an
OR merge with EXP-120.  It would combine incomplete positive coverage with a
near-universal negative cue and repeat the rejected document-local attention
pattern.  Preserve the original full-notice Gemma call and do not use document
type alone as a label trigger.
