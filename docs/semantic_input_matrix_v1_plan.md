# Semantic-input matrix v1: offline admission audit

## Question

Before another paid prompt experiment, what information does the exact
canonical input contain for each `v1`–`v24`, and what required information is
absent or structurally omitted?

This is not an F1 experiment and does not authorize a new card, rule, RAG,
grouping, or merge policy.

## Fixed inputs and scope

- Policy under audit: root `config.yaml`, `official_baseline_v1`, one ordered
  4,000-character context, V+E output.
- Legal-condition source/provenance: `docs/semantic_input_contract_v1.md` and
  ignored organizer-derived `data/derived/legal_condition_ledger_v1.json`.
- Notice population: all dev-200 records; no labels are read.
- Exact renderer: `BaselinePipeline` and the same prompt construction used by
  experiments/submission, with `MockClient`; no API request is sent.

## Completion gates

The audit may be considered complete only when all are true:

1. Contract table contains `v1`–`v24` exactly once, with no shorthand such as
   “same as v6” in the required metadata/CSV field.
2. Each contract item has at least one retained ledger provenance entry.
3. Each exact baseline item-table line is found in the rendered system
   message, and the report separately marks whether its 1 condition, material
   0 condition, and CSV applicability fact are actually rendered.
4. The audit counts, across dev-200, each document type as rendered, present
   but omitted by the 4,000-character policy, or absent from the notice.
5. Exact offline messages are exported and read for a short complete notice,
   a truncated notice, and an attachment-bearing notice.

## Human review samples and conclusion

The generated files are deliberately ignored with other output artifacts:

- `outputs/semantic-input-matrix-v1/rendered_inputs/pps-dev-062.messages.md`:
  short complete announcement context.
- `outputs/semantic-input-matrix-v1/rendered_inputs/pps-dev-042.messages.md`:
  announcement cut at the 4,000-character boundary.
- `outputs/semantic-input-matrix-v1/rendered_inputs/pps-dev-01.messages.md`:
  attachment-bearing notice; its attachment is explicitly reported as
  omitted after the announcement is truncated.

Human review conclusion: the exact baseline correctly contains all 24 raw
item-table lines, standard metadata fields when keys exist, and an ordered
announcement context. It does **not** contain item-specific legal
applicability/exception conditions, friendly exact competition-product facts,
or any admitted attachment in dev-200. Thus it is a valid organizer-control
prompt, but it cannot by itself test the semantic legal-condition hypothesis.

## Reproduction

```bash
.venv/bin/python scripts/audit_semantic_input_matrix.py \
  --config config.yaml \
  --output-dir outputs/semantic-input-matrix-v1
.venv/bin/python -m pytest tests/test_semantic_input_matrix.py
```

Read `outputs/semantic-input-matrix-v1/semantic_input_matrix.md` and its
three rendered message files before proposing a paid candidate. A future
candidate must name its base config, allowed policy changes, and precisely
which currently-missing contract fields it will render; it must then rerun
this audit against that candidate configuration.
