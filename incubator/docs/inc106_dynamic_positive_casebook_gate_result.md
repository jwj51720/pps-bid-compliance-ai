# INC-106: dynamic positive-only evidence schema

On eight fresh unlabeled notices, Stage A completed 7/8 and the dynamic
positive-only Stage B completed 7/7.  This isolates and fixes INC-105's schema
defect: Stage B no longer needs to serialize empty evidence objects for all 24
items.  The one Stage-A failure was an explicit 4,096-token high-reasoning
exhaustion, not a schema error.  After exact/annotation/duplicate resolution,
all three Stage-B positive quotes are unchanged source substrings.

The next fresh gate therefore changes only Stage-A's already justified output
cap to 8,192.
