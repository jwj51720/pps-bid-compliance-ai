# EXP142 — semantic verifier input preview only

EXP142 is intentionally `lifecycle: preview`; its runner rejects every
non-mock invocation. It is not a paid experiment, performance result, or
submission candidate.

The purpose is to render the three-call A/B/C design from
`bounded_multicall_verifier_strategy_v1.md` and inspect it against
`semantic_input_contract_v1.md`.

- A: exact organizer 24-item control; no cards and no product CSV context.
- B: `v1`–`v9`, `v19`, `v21`–`v24`; official-interpretation cards only.
- C: `v10`–`v18`, `v20`; the same cards plus friendly exact organizer-product
  CSV facts only.

The current preview deliberately does **not** yet add profile-specific
applicability text. Review must decide whether the profile can be inferred
reliably from visible human-readable metadata, or whether a narrowly rendered
profile fact is needed. No remote call is permitted until that decision and
the all-item semantic span audit are recorded.

## 2026-09-07 rendered-input audit result: reject before provider call

The preview rendered and was read for national, local-general, local-small,
and local-negotiated notices, including an overflow notice and notices with
attachments. The required human-readable metadata and the C-group friendly
competition-product text render correctly; internal route names and raw code
arrays do not enter the model messages.

However, all three groups still use the organizer-format 4,000-character
context. In actual messages, local-small and local-general examples include
`[절단]` and `[미수록 문서]`. That makes the proposed final delegation invalid:

- B is the sole final source for `v9`, but its card requires
  규격서·과업지시서·제안요청서 evidence and these attachments can be omitted.
- C is the sole final source for `v10`, `v11`, `v16`, `v18`, and `v20`, but
  their cards require absence across all supplied documents. An omitted
  document prevents a valid absence conclusion.
- B and C together replace every A key, so the A full call would be discarded
  rather than act as a verifier.

The preview is therefore an input-audit artifact only, not a partial test of
the three-call strategy. Do not change `lifecycle: preview` or run it against
a provider. Any successor must give each final item a document scope matching
`docs/semantic_input_contract_v1.md`, then re-run the rendered-input audit.
