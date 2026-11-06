# EXP133 — two-way G02 output-scope result

## Gates

- Focused regression suite: 54 passed.
- Controlled-difference preflight: passed.
- Actual-message review: `PPS-DEV-062` (complete), `042` (announcement
  overflow), and `01` (announcement plus omitted attachments). In each notice,
  G01/G02 user messages were byte-identical; only the active keys in the
  system/schema differed.
- Exact tokenizer admission: 20 records, 40 calls, maximum 4,093 input tokens.
- Grouped mock: completed all 20 rows.

Exports are under
`outputs/exp-133-two-way-g02-fast-panel/input_review/` and
`outputs/exp-133-two-way-g02-fast-panel/admission_fast20/`.

## Result

| Run | macro positive F1 | G02 five-item mean F1 | evidence validity |
| --- | ---: | ---: | ---: |
| EXP125A exact organizer control | 0.17196 | 0.10000 | 0.75676 |
| EXP130 four-way diagnostic | 0.30020 | 0.26667 | 0.82927 |
| EXP133 two-way actual execution | **0.26151** | **0.43333** | 0.76744 |

No parse errors occurred. G02 improved `v6` (F1 0.50), `v7` (0.667), and
`v19` (1.0); `v8` and `v9` remained zero on this small cohort. The fast-panel
criterion is met, but it is not sufficient for a policy promotion. EXP134 is
the required independent confirmation.
