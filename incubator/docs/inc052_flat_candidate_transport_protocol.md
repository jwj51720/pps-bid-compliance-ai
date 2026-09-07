# INC-052: Flat Candidate-Field Transport Audit

## Purpose

INC-051 promotes flat binary JSON fields but does not validate the only
remaining requirement for the product pilot: selecting source evidence without
a nested object.  This no-data audit tests flat integer candidate indices.

Each of ten calls receives the same synthetic instruction and strict flat
schema: `v10`, `v11`, `v12`, `v13` are binary fields, while `e12` and `e13`
are integer enums `-1..4` (`-1` means no evidence).  The expected answer is
`0,1,0,1,-1,3`.  Requests use the identical model route and 64-token cap from
INC-051.  No competition data, legal content, or labels are sent.

Advance requires 10/10 exact valid responses with no provider completion over
64.  The $0.04 ceiling safely covers ten observed normal responses and a
runaway failure.  Success permits a *new* product applicability pilot whose
only architectural difference from INC-050 is flat fields; it does not make
INC-050 scorable or choose any product decision policy.
