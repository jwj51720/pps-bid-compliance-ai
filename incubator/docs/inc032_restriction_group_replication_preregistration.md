# INC-032: Restriction-Group Output Replication

## Rationale

INC-030 rejects complete legal context, but its control arm provides a distinct
signal: with the same whole notice and no law, outputting only v4/v6/v7/v8
achieved 0.30948 target Macro F1. The preserved INC-018 joint-24 artifact has
zero F1 on each of these labels. This could be useful output attention, or an
artifact of provider variation and a non-contemporary comparator.

## Frozen treatment

Issue exactly one fresh call for each of the 200 dev notices using the **INC-030
control** message, schema, complete-document renderer, model, temperature,
seed, evidence gate and retry policy. There is no law context, RAG, example,
rule, retrieval, source window, or prompt repair. The only comparison is the
already completed INC-030 control run; both contain actual complete notices.

Maximum spend is 200 calls and $0.30. Raw response, usage, parse failures and
per-notice result are checkpointed independently under a file lock.

## Gate

This is a replication gate, not a metric search. It passes only if all hold:

1. fresh target Macro F1 is at least 0.25;
2. fresh target micro recall is at least 0.36;
3. target Macro F1 differs from INC-030 control by no more than 0.05;
4. retained positive evidence validity is 100%; and
5. transport/parse failure is at most 5%.

If it passes, calculate two isolated 24-label compositions by replacing only
v4/v6/v7/v8 in the immutable INC-018 single-full predictions with each
independent group run. Promote to a submission-component confirmation only if
both composed Macro F1 values exceed INC-018 by at least 0.02 and no untouched
label changes. If it fails, reject restricted-group output as unstable; do not
try another prompt wording or output partition.
