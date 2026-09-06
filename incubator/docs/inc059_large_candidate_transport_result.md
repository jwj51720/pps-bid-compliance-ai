# INC-059: Large Flat Candidate Transport Result

All five synthetic responses contained the exact required 24 binary fields and
19 flat evidence-index fields, including an index of 511. The requested
128-token cap was insufficient: valid serializations used 262--417 completion
tokens. This invalidates the original cap gate, not the schema.

**Transport finding:** a source-line Joint-24 response needs a 512-token output
reserve. Flat large-enum fields remain structurally viable; no nested object
or generated quote is required. A later notice experiment must use 512 and
measure actual output completion, with no arbitrary smaller cap.
