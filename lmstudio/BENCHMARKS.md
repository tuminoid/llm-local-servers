# LM Studio benchmark results

Measured baselines for the script-managed LM Studio server. The
cross-runtime summary is [../README.md](../README.md); the same-engine
comparisons are the llama.cpp path in
[../ollama/BENCHMARKS.md](../ollama/BENCHMARKS.md) and the MLX path in
[../vllm-metal/BENCHMARKS.md](../vllm-metal/BENCHMARKS.md).

All serving measurements here use the shared
[AuditBench v1](https://github.com/tuminoid/llm-audit-bench) protocol,
driving LM Studio's OpenAI-compatible endpoint. A publishable row is
`canonical: true` and `publishable: true`: the canonical 1/2/4/8 workload
on a clean commit, with checked model identity (key, format, quant,
architecture via `lms ps`) and the live resolved launch profile.

## Status

No canonical AuditBench results are recorded yet. LM Studio's engines are
the same llama.cpp (GGUF) and MLX that `ollama/` and `vllm-metal/` already
measure, so a row belongs here only once a run proves LM Studio earns a
place rather than duplicating those numbers on the same host and model.

The server and the AuditBench adapter have been exercised end-to-end on a
CUDA host (`cachyos-x8664`, 8 GB GPU, 31 GB RAM): full lifecycle, readiness,
a real `/v1/chat/completions` reply with reasoning, live identity
verification against `lms ps`, the AuditBench plan driving prefill,
near-context, decode, and `audit_32k` phases, and VRAM release on stop.
That proves the pipeline, not a serving rate: the numbers below are
exploratory (`canonical=false`, one sample, one stream, `qwen3.5-9b-gguf`
at 131,072 context with heavy CPU offload on an 8 GB card), recorded only
as adapter evidence and explicitly not publishable.

| phase | prompt | wall | input tok/s | output-e2e tok/s | calls/h |
| -- | -- | -- | -- | -- | -- |
| prefill_32k | 32,780 | 45.1s | 727 | 0.02 | 79.9 |
| prefill_64k | 65,547 | 99.6s | 658 | 0.01 | 36.2 |
| capacity_near | 122,861 | 286.7s | 429 | 0.00 | 12.6 |
| decode | 66 | 156.6s | 0.4 | 6.54 | 23.0 |
| audit_32k | 32,780 | 593.3s | 55 | 1.73 | 6.07 |

Those rates reflect an 8 GB card doing mostly CPU inference, not the
runtime's ceiling. Capture canonical rows on a host that fits the native
context, one per artifact:

- `qwen3.6-27b-gguf` on any GPU/CPU host with enough memory (llama.cpp).
- `qwen3.6-27b-mlx` on Apple Silicon (MLX), the same-host comparison
  against the vLLM-Metal MLX operating point.
- `qwen3.5-9b-gguf` is the small dense profile for proving the lifecycle
  on a modest host; AuditBench still needs its full 131,072-token context
  to run, so give it a host that holds that comfortably before quoting a
  rate.

## Capability Check v1

Not yet run. Both configs expect reasoning required, tools required, and
the `enable-thinking-false` disable control. Run `make lmstudio-capability
MODEL=<name>` against a loaded model before promoting either for agent
workloads.
