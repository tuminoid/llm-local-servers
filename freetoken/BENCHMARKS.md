# FreeToken benchmarks

## A100-SXM4-80GB

Results on this hardware are on its page,
[NVIDIA A100 SXM4 80GB](../docs/hardware/nvidia-a100-sxm4-80gb.md).

## Dropped profiles: A100-SXM4-80GB

FreeToken 0.2.3, 2026-11-26/27, llm-audit-bench 3.0.0, canonical `session`
profile at each checkpoint's sampling, 262,144 context. Every run below was
publishable; each profile was dropped because another runtime on this
hardware serves the same model faster, or because it failed Capability
Check v3.

| Model and GGUF | MoE strategy | Admission | Capability | Best sessions/h | Other stream counts | Served instead by |
| -- | -- | --: | -- | --: | -- | -- |
| Qwen3.6-35B-A3B, unsloth UD-Q4_K_M | fused | 8 | passed | 51.06 @4x | 1x 33.37, 2x 43.17, 8x 48.22 (22/24) | vLLM AWQ, 60.39 @8x |
| Qwen3.8-27B, unsloth UD-Q4_K_M | dense | 8 | passed | 13.00 @4x | 1x 9.22, 2x 10.99 | vLLM W4A16, 23.48 @4x |
| Gemma-4-26B-A4B, unsloth UD-Q4_K_M | fused | 8 | passed | 23.52 @1x | 2x 7.19 | vLLM AWQ, 45.74 @4x |
| Qwen3.8-Flash-Next, ISTA-DASLab IQ3_S | fused | 8 | passed, 36/36 | 31.22 @2x | 1x 23.13 | Strata NVFP4, 36.51 @1x |
| Flint, unsloth UD-Q4_K_XL | fused | 8 | failed | -- | -- | -- |
| GLM-5.3-Flash, unsloth UD-IQ2_XXS | offload | 1 | failed, 26/30 | -- | -- | UD-Q2_K_XL |
| GLM-5.3-Flash, unsloth UD-Q3_K_XL | offload | 1 | passed, 35/36 | 8.56 @1x | -- | UD-Q2_K_XL |

- Gemma's two-stream rung fell to 7.19 sessions/h while its per-stream
  decode held (108 against 101 tok/s); the cause was not established.
- Flint's every fitness sample emitted `!` until the 65,536-token answer
  cap. Engine numerics and the artifact were not separated; retest with a
  greedy depth probe on FreeToken against the same GGUF on llama.cpp.
- GLM-5.3 by quant, all at one stream with experts offloaded: runaways
  3 of 30 (UD-IQ2_XXS), 2 of 36 (UD-Q2_K_XL) and 1 of 36 (UD-Q3_K_XL).
  UD-Q3_K_XL decoded its reports at 23.4 tok/s against UD-Q2_K_XL's 38.1 and
  wrote fewer tokens per session, so the two land within 4% of each other;
  UD-Q2_K_XL stays as the interactive profile for its decode rate.

## Cached-token count on a cold call

FreeToken 0.2.3 with `--enable-cache-report` returns no
`prompt_tokens_details` at all on a call with no prefix-cache hit, streamed
or not, and `cached_tokens` only once a call hits the cache (2026-11-27,
Qwen3.6-35B-A3B: a cold 13,927-token prompt reported none, its repeat
13,888 cached). Every session's first step is such a call, so AuditBench
cannot tell zero cached tokens from an unreported count and publishes no
session prefill rate for FreeToken rows. Retest: a zero-hit call reports
`cached_tokens: 0`.
