# INC-105: split unlabeled casebook transport gate

Eight fresh notices (orders 17--24) from the label-free INC-080 manifest are
used.  Stage A makes one high-reasoning, 4,096-token call returning only 24
labels plus a compact case signature.  Stage B receives the same full notice
and the immutable Stage-A positive item list, and returns quotes/bases only for
those items; it cannot alter labels.  Its output cap is 2,048 and reasoning is
medium.  The deterministic resolver may turn a uniquely matched quote that
omits only organizer anonymization tags into an unchanged source substring.

This is a provenance/transport experiment, not a label-quality score.  It
advances only if all eight Stage-A records parse, all Stage-B calls complete,
and every positive obtains an exact resolved source substring.
