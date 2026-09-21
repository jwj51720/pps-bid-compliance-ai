# EXP314 generation-limit anomaly audit

Scope: offline transport/config inspection; no paid repeat, prompt or provider parameter change.

EXP314 PPS-DEV-069 reports completion8192, finish_reason length, raw20451 characters,
mostly whitespace after a partial JSON object. Request preview and resolved config max_tokens
are2500. Other99 records in EXP314–318 have no over-limit/length anomaly.

Traced `scripts/run_experiment.py::_make_client` → `OpenRouterClient.__init__` →
`complete` → `requests.post(json=payload)`: max_tokens is passed unchanged; no local8192
default, reasoning override, truncation or usage substitution occurs on this path.
Added mocked runner-to-HTTP regression test with actual EXP314 config: payload max_tokens2500,
require_parametersTrue, configured temperature/seed preserved. Added oversized-response test:
reported8192 and malformed content are preserved for diagnostics, never turned into a label rule.
`pytest -q tests/test_openrouter.py`:3passed. Comparison analyzer now records configured cap,
over-limit/length IDs and raw size in isolated summary; precisely069 is flagged.

This proves local current code propagation, not the historical network payload or provider
implementation. Historical raw HTTP request, response generation ID and endpoint provider were
not preserved in these prediction records; therefore exact upstream cause remains unproven.
Do not claim the provider ignored the cap as established fact or infer evaluator vLLM behavior.
Do not rerun/select a favorable response to clean the experiment.

Implications: exclude anomalous response from descriptive speed/typical-completion comparisons,
but retain it in total runtime and malformed-rate reporting.069 is gold-negative recovered0;
it does not explain corrected-card recovery of fast positive039, nor holdout FP increase4→11.
V/E label comparison remains a failed generalization; V-only shorter completion is not a label gain.

Next transport observability should preserve sanitized generation ID/provider/HTTP request
settings for reproducibility without secrets or prompt-policy changes. This is separate from
any new accuracy experiment and does not itself establish a better strategy.
