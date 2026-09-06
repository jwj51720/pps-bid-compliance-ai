# INC-077: Post-Essence Research Reset

## Evidence accumulated after the initial reset

| Branch | Controlled evidence | Decision |
|---|---|---|
| Short organizer-law essence injected into judgment | INC-072: +0.00260, -0.05801 | Reject: precision suppression costs recall and is not repeat-safe. |
| Semantic e-prime then e-prime-only decision with full-source fallback | INC-073: 55.56% / 44.44% positive fact coverage; -0.09963, +0.00380 | Reject joint extraction: a nonempty summary can still omit decisive facts. |
| Evidence-local document attention | INC-074/075: announcement evidence locality, but -0.02381, +0.35119 | Reject: source evidence location does not establish decision locality. |
| More procedural formalization | INC-065 plus v22 review | No high-loss observable item: v22 is already F1 0.909; remaining errors lack a complete necessary fact predicate. |

These are genuine topology changes, not repetitions of the same generic
prompt: legal compression, semantic extraction/fallback, document topology,
and formal-predicate observability have all been tested.

## Research conclusion

Under the present constraints—only organizer data, no learned classifier or
fine-tune, full notice must be seen, Gemma/BGE only—there is no supported path
to a large `+0.23` Macro-F1 increase from context engineering.  The remaining
high-loss labels require semantic interpretation of product applicability,
exceptions, bidder role, or cross-document procedure facts that are neither
fully supplied by metadata nor recoverable by a high-recall lexical/BGE gate.

This is not a claim that performance is maximized.  It is a decision to stop
spending on unreplicated prompt/context variants.  Future work becomes
admissible only with a materially new source of information or a method that
changes the information bottleneck, for example:

1. the exact offline Gemma submission tokenizer/runtime, enabling a real
   complete-law admission study rather than an OpenRouter approximation;
2. organizer-provided structured applicability fields or clarified label
   policies for product/SW/exception cases;
3. competition permission for a learned/finetuned component or a new final
   model; or
4. a source-grounded item fact whose *all-positive coverage and low-negative
   activation* pass offline on the frozen exploratory fold, followed by a
   one-time confirmation on the frozen opposite fold.

## Runtime recheck (current environment)

INC-077 rechecked this rather than relying on prior notes.  `PPS_MODEL_DIR`
and `PPS_EMBED_DIR` are unset, and no local `tokenizer.json` or
`tokenizer_config.json` is present in the workspace.  The tracked submission
entrypoint constructs the admission tokenizer from `PPS_MODEL_DIR`; therefore
neither an OpenRouter token report nor character length is a valid substitute.
The exact complete-law admission branch remains unavailable in this environment
until the evaluator-compatible model directory is supplied.

## Governance

INC-076's 100/100 split is now mandatory for any new paid hypothesis.  Do not
choose prompt wording, numeric cutoff, document subset, or ensemble on both
folds.  Explore one fold, freeze, confirm once on the other, then consider an
all-dev run.  This protects the unknown 1,900-test distribution better than
continuing breadth through dev-local variants.
