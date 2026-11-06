# INC-117: item-level e-prime transport gate (invalidated)

## Purpose

Test the proposed two-step direction without claiming a score: first extract a
short, source-grounded `eprime` for each of v10--v18 from a full notice, then
only proceed to adjudication if the extraction is transport-safe.

## What happened

This run is **invalid as an experiment**. Three independently started local
processes overlapped after a terminal invocation returned before its child
process had finished. They submitted duplicate requests. All processes were
stopped as soon as the overlap was observed. The raw rows are preserved in
`runs/inc117_item_eprime_transport_pilot/extract.jsonl` for cost/audit
transparency and must not be used for a metric or selection decision.

Recorded output: 14 successful request rows, but only 7 unique notices; the
eighth notice (`PPS-DEV-188`) had no completed extraction. No adjudication
stage was run.

## Transport audit of the completed unique notices

The latest completed extraction per notice had 63 nonempty e-primes. Their
single proposed quotes resolved unchanged to source in 61 cases; 2 did not.
Both failures were `PPS-DEV-176` v15/v17. The e-prime correctly recognized a
620,000,000 won amount, but copied its quote as `*영세율 적용함.` whereas the
source ends `*영세율 적용`. This is a generated near-quote, not admissible
evidence.

This is sufficient to fail the gate: a compact summary coupled to one quote
cannot be assumed source-faithful merely because its broad conclusion is
correct. The design must emit independently resolvable source anchors for each
atomic fact, or treat e-prime solely as non-evidence reasoning aid and retain a
deterministic original-source retrieval step for final evidence.

## Consequence

Do not run Stage B or scale this form of the method. Before another paid call,
change the extractor contract to atomic facts with one source anchor per fact,
add an exclusive run lock, and run a local schema/resolution smoke test. The
next model pilot must begin only after those gates pass.
