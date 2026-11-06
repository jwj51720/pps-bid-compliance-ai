# EXP135 prompt visibility audit

This is a post-hoc diagnostic only. Development labels/evidence are used to
measure whether an already-rendered organizer-format 4,000-character input
contained a gold fact; they are never used in a model prompt, routing rule, or
label correction.

## Actual context finding

The target documents for `v9` are specifications/task documents, yet the
organizer-format context takes the beginning of the announcement first. Of the
six v9-positive development notices:

| Visibility class | count |
| --- | ---: |
| Gold source visible in the actual 4,000-character context | 0 |
| Gold source in omitted 규격서 | 3 |
| Positive label has no organizer evidence text to locate | 3 |

The three deterministically inaccessible examples are:

- `PPS-DEV-09`: `Chipset: GB10 Grace Blackwell Superchip` in `규격서:D1`;
- `PPS-DEV-12`: `제조사·모델명 : 아크론브라스(Akron Brass) 터보젯(TurboJet)`
  in `규격서:D1`;
- `PPS-DEV-23`: `DJI Matrice 4E/T 시리즈 인텔리전트 플라이트 배터리일 것` in
  `규격서:D1`.

For each, the actual user input has `[절단]` and `[미수록 문서]`; none of the
quoted model terms appears in it. This is a source-coverage limitation, not a
card wording or inference failure.

## Consequence

Do not try to compensate with a broader card, a keyword rule, or a positive
default. The smallest warranted next test is a separate v9 execution group
with complete source-document passes, while retaining EXP135's normal context
for every other item. It must be evaluated as a runtime-risk ablation and its
actual messages must be reviewed before any paid call.

Audit artifacts: `outputs/exp135_prompt_visibility_audit/report.{json,md}`.
