# INC-059: Large Flat Candidate-Index Transport Audit

INC-052 validates only six flat fields with five candidate indices.  A
source-line-grounded Joint-24 architecture needs one candidate ID among up to
hundreds of original lines.  This synthetic transport audit tests a strict flat
schema with 24 binary fields and 19 evidence-index fields, each allowing
`-1..767`.  It sends no competition data.

### Output-reserve amendment

The first five calls produced exact valid JSON but used 262--417 completion
tokens, because 43 required fields cannot fit in the originally requested
128-token reserve.  This is a serialization lower-bound observation, not a
model failure.  The line-ID architecture must reserve 512 output tokens.  The
initial five calls establish schema/value validity; a later notice pilot must
use the 512 reserve and record actual completion sizes.
