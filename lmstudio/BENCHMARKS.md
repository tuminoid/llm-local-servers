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

The server has been exercised end-to-end on a CUDA host (lifecycle,
readiness, a real `/v1/chat/completions` reply with reasoning, live
identity verification, and VRAM release on stop), but that host's 8 GB GPU
cannot hold the 27B configs at their native context, so no serving rate
was captured there. Capture canonical rows on a host that fits the config,
one per artifact:

- `qwen3.6-27b-gguf` on any GPU/CPU host with enough memory (llama.cpp).
- `qwen3.6-27b-mlx` on Apple Silicon (MLX), the same-host comparison
  against the vLLM-Metal MLX operating point.

## Capability Check v1

Not yet run. Both configs expect reasoning required, tools required, and
the `enable-thinking-false` disable control. Run `make lmstudio-capability
MODEL=<name>` against a loaded model before promoting either for agent
workloads.
