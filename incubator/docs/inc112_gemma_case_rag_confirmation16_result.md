# INC-112: Gemma case-RAG fresh confirmation — rejected

INC-111's eight-notice pilot had a +0.04167 paired macro-F1 signal.  INC-112
used 16 fresh rows from the same pre-existing label-free structural manifest,
with the identical full-notice Gemma prompt, BGE casebook index, top-three
context format, model, decoding, and evaluation.  Both arms completed 16/16.

| Fresh 16 IDs | Macro positive F1 |
| --- | ---: |
| Direct Gemma | 0.05556 |
| Gemma + top-3 case-RAG | 0.05556 |

The RAG prompt changed five cells: it corrected two direct false positives but
introduced three new false positives.  It therefore provides no replicated
net effect.  A quarter of retrieved top-three cases happened to contain a
teacher-positive label, but that does not establish an actionable precedent
signal and must not justify a corpus-scale expenditure.

**Decision:** reject the current 64-casebook BGE case-RAG topology.  Do not
scale this casebook to 2k/20k and do not merge INC-111's small-pilot outputs.
The casebook and resolver remain reusable provenance infrastructure, but the
next Luna performance branch must target an independently diagnosed judgment
operation rather than add non-authoritative examples to Gemma.
