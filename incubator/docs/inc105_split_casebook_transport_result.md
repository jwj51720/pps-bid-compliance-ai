# INC-105: split unlabeled casebook transport gate — schema failure

Stage A (compact labels plus signature) completed 8/8 fresh unlabeled notices.
It produced one positive and its Stage-B quote resolved to an unchanged source
substring.  Stage B completed only 5/8: three responses were malformed JSON.

The cause is a contract error, not a conclusion about the two-pass concept.
Although the prompt asked for evidence only for Stage-A positives, Stage-B's
JSON schema required 24 evidence objects, forcing the model to serialize empty
fields and recreating the long-output failure.  The current cohort is frozen
and will not be replayed.

The only permissible repair is a fresh-cohort transport test with a schema
whose required keys are exactly the immutable Stage-A positive item list.  It
must preserve the labels and reject any attempted label modification.  No
score, per-item merge, or 20k scale claim follows from INC-105.
