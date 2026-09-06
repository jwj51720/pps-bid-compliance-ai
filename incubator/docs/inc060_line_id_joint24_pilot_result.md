# INC-060: Source-Line-ID Joint-24 Result

**Unscorable; reject this direct grounding contract.**  All 96 responses were
valid JSON within the 512-token reserve, but 45 violated the semantic response
contract by returning a non-absence positive label with evidence index `-1`.

| Repeat | Valid record/arm calls | Label/evidence-contract failures |
|---|---:|---:|
| r1 | 28/48 | 20 |
| r2 | 23/48 | 25 |

The failures are not free-text quoting or transport failures: they are flat,
parseable objects with inconsistent positive/evidence fields.  Under the
predeclared contract each would have to downgrade its positive to zero, but
that would make this a different, high-recall-loss policy.  No partial score,
row dropping, or after-the-fact source retrieval is valid.

INC-059 remains useful only for serialization sizing: 512 is enough to carry
the fields.  INC-060 shows that asking Gemma to select an evidence line for
every Joint-24 positive does not create a reliable semantic grounding channel.
Do not repair it by prompt wording or retry more records.
