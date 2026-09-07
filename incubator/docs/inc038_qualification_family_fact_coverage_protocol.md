# INC-038: Qualification-Family Source-Fact Coverage Audit

## Question

After freezing v3 and v21, inspect the remaining related `v1`--`v9` shapes
without fitting another rule: institution qualification (v1), performance
restriction (v2/v4), regional qualification (v5/v6/v7), their co-occurrence
(v8), and a model/manufacturer expression in a task document (v9).

## Frozen source facts

The audit scans every unchanged nonempty source line. It records, with document
type and offset, the following semantic fact markers:

- institution qualification: institutional noun plus a participation/
  qualification expression;
- performance: `실적` plus a Korean won amount;
- regional qualification: a regional-restriction anchor such as `본점`,
  `영업소`, `소재지`, `관할구역`, or `지역제한`;
- task-model: a `과업지시서` line with model/manufacturer terminology.

v8 is a notice-level conjunction of independently retained performance and
regional facts; it is explicitly not a violation prediction. No source window,
development-derived number, metadata-state label, model output, or legal
conclusion is emitted.

## Measures and gate

For each item, report gold-positive candidate recall, negative candidate rate,
source-document distribution, and retained source provenance. This label use is
diagnostic only. An item may advance only if its candidate facts cover every
positive and an organizer-law predicate can distinguish the candidate's legal
roles without a dev-tuned cutoff. Otherwise it remains a possible target for a
source-grounded LLM call, not a deterministic rule.
