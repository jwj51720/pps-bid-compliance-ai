# EXP134 — two-way G02 label-blind holdout result

## Gates

- Preflight: passed with no effective policy differences from EXP133.
- Actual-message review: `PPS-DEV-094`, `046`, and `082`. G01/G02 user
  messages were byte-identical within each notice; the reviewed overflow and
  omitted-document markers were genuine organizer-context markers.
- Exact tokenizer admission: 20 records, 40 calls, maximum 4,162 input tokens.
- Grouped mock: completed all 20 rows.

## Result

| Run | macro positive F1 | G02 five-item mean F1 | evidence validity |
| --- | ---: | ---: | ---: |
| EXP128A exact organizer control | 0.12500 | 0.20000 | 0.74194 |
| EXP131 four-way diagnostic | 0.20833 | 0.40000 | 0.73077 |
| EXP134 two-way actual execution | **0.20833** | **0.40000** | 0.65385 |

The two-way policy matches the four-way result while requiring half as many
calls, and improves over the exact organizer control. Parsing was clean. Its
evidence validity is lower than the control and the cohort is small, so it is
not a submission candidate yet. Run dev-200 without any policy edit; compare
quality, evidence, and 2× call/runtime cost before deciding whether the output
scope gain is real enough to retain.
