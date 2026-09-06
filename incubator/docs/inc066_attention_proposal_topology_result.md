# INC-066: Independent Attention-Proposal Topology Result

## Execution validity

The 20-notice, two-repeat run made all planned provider calls (40 control
requests and 40 locator-plus-final treatment jobs, 120 provider calls total).
It is **unscorable**.  The common flat 24-label final response exhausted its
128-token completion reservation before the object closed in most calls.
Because this occurred in both arms, a treatment-control F1 comparison would
confound the proposed topology with incomplete output serialization.

| Arm | r1 valid final objects | r2 valid final objects |
|---|---:|---:|
| Complete-notice control | 2/20 | 3/20 |
| Attention treatment | 6/20 | 1/20 |

The raw partial objects, usage, and failures are retained under
`incubator/runs/inc066_attention_proposal_topology_pilot/`.  Reported cost was
`$0.12107719`.

## Independent locator finding

This failure nevertheless yields a decisive semantic observation that is not
caused by the final-output cap.  Every one of the 40 locator calls produced a
valid 24-field object, but all 960 proposed IDs were `-1`.  Thus an
unconditioned request to select the one most material source line per legal
item does not create attention proposals at all; it declines every item.

This differs from INC-062, where a locator conditioned on an already-fixed
positive found a nonnegative line in 71/71 calls.  The missing variable is not
line-ID serialization.  It is the need for an upstream decision before Gemma
will commit to a relevant line.  Adding a retry, changing a line-count/rank
rule, or changing the locator wording after observing this would not isolate
the preregistered cognitive variable.

## Decision

**Reject this topology before score.**  Do not rerun merely with a larger
final-output reserve: that would repair the common transport issue but cannot
make an all-`-1` attention appendix informative.  Do not tune the locator into
a label-producing prompt, because that becomes the already tested direct
joint-grounding or extract-then-adjudicate topology.

The general lesson is sharper than “structured output sometimes fails”:
flat-schema transport can be valid while its semantic contract is vacuous.
Future experiment preflight must check both (1) serialization reserve for a
complete schema object and (2) non-vacuous task output, before spending a
paired scoring budget.

## Reproduction

```bash
python incubator/src/inc066_attention_proposal_topology_pilot.py --mode preflight
python incubator/src/inc066_attention_proposal_topology_pilot.py --mode run --workers 16
python incubator/src/inc066_attention_proposal_topology_pilot.py --mode aggregate
```
