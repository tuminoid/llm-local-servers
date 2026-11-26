# Apple M5 Max, 128 GB

Measured on a MacBook Pro (`Mac17,6`) with the M5 Max, 40 GPU cores and
128 GB of unified memory, macOS 27.0.1. Memory, not compute, decides what
fits: weights, KV cache and the operating system share the 128 GB, so the
largest models need a memory cap and leave little headroom at depth.
Concurrency rarely beats one stream here.

The tables are rendered from
[apple-m5-max-128gb.json](apple-m5-max-128gb.json), which
`make results-import` fills from the retained harness JSON; never edit a
table by hand.

## Audit ranking

Canonical [AuditBench v3](https://github.com/tuminoid/llm-audit-bench)
`session` profile at each conf's declared sampling: tool steps from 32k
evidence, 16 at 262,144 and above and 9 at 131,072, report at depth. The
Splash rows ran 2026-11-26 on Splash 1.7.3 and llm-audit-bench 3.0.0,
except Ornith 1.5 122B's (2026-10-31, Splash 1.5.0). The LM Studio,
vLLM-Metal and ds4 rows ran 2026-11-24/25 on llm-audit-bench 3.0.0. The
Ollama and Kapitsa rows ran 2026-11-15/16 on llm-audit-bench 2.5.0, whose
session code 3.0.0 ships unchanged. Runtimes: LM Studio 0.4.25+1 (Splash
engine 1.3.0, mlx-llm 1.14.0), vLLM-Metal 0.31.0, Ollama 0.40.16, ds4
`0aaea5a` and Kapitsa 0.2.36. The ds4 `glm5.3-flash-q2` row ran 2026-11-26
with `ds4/glm-tool-args.patch`. The harness climbs 1, 2, 4, 8
streams within admission and the KV pool while each rung completes every
session and gains 10%.

A ranked row passes Capability Check v3 compatibility and publishes its
optimal operating point: the fastest measured stream count whose sessions
all completed. Complete counts sessions whose report ended on its own and
named at least 7/8 of its findings. KV pool is the engine's own where it
reports one; Ollama's is its allocation, configured context times slots.
pp512/tg128 is the llama-bench-method reference (one stream, greedy, depth
~0), not a serving result; it is unavailable where the engine cannot force
an exact output length. The OWASP vuln score is Capability Check v3's audit
aptitude: true-positive minus false-positive rate on 28 OWASP
BenchmarkPython cases (+1 perfect, 0 chance) with its 95% interval; the
intervals span about +-0.3, so rows stay ranked by rate.

<!-- results:audit -->

| Rank | Profile | Runtime | Engine | Tier | Context | Slots | KV pool | Best sessions/h | Other stream counts | Complete | Out tok/session 1x | Prefill tok/s 1x | Report decode 1x | pp512 / tg128 | OWASP vuln score [95% CI] | Publishable | Session JSON |
| --: | -- | -- | -- | -- | --: | --: | --: | --: | -- | -- | --: | --: | --: | -- | -- | -- | -- |
| 1 | `ornith1.5-35b-a3b` | Splash | Splash | MoE | 262,144 | 4 | 4,448,256 | 36.05 @1x | 2x 35.78 | 1x 3/3, 2x 4/4 | 7,262 | 2,554.8 | 176.9 | 6,433 / 336.2 | +0.71 [+0.36, +0.89] | yes | `20261126T024425.195684+0000_splash_ornith1-5-35b-a3b_session.json` |
| 2 | `nemotron-3.5-lightning-30b-mlx` | Ollama | MLX | hybrid MoE | 262,144 | 1 | 262,144 allocated | 31.07 @1x | -- | 3/3 | 6,104 | 2,330.8 | 123.3 | 3,372 / 178.7 | +0.36 [+0.00, +0.62] | yes | `20261115T174450.386607+0000_ollama_nemotron-3-5-lightning-30b-mlx_session.json` |
| 3 | `inkling-2-mini` | Splash | Splash | MoE | 262,144 | 4 | 477,184 | 27.90 @2x | 1x 25.96 | 1x 2/2, 2x 6/6 | 4,706 | 1,760.6 | 91.8 | 2,856 / 115.2 | +0.64 [+0.28, +0.84] | yes | `20261126T031224.963713+0000_splash_inkling-2-mini_session.json` |
| 4 | `qwen3.8-flash-next-iq3s` | Splash | Splash | MoE | 262,144 | 4 | 3,309,568 | 27.78 @2x | 1x 27.01 | 1x 3/3, 2x 6/6 | 6,451 | 2,025.1 | 112.9 | 2,153 / 152.2 | +0.79 [+0.44, +0.94] | yes | `20261126T033856.107930+0000_splash_qwen3-8-flash-next-iq3s_session.json` |
| 5 | `clover-35b-a3b` | Kapitsa | Kapitsa, Metal | MoE | 262,144 | 4 | 4,367,951 | 27.58 @1x | 2x 27.01 | 1x 3/3, 2x 6/6 | 3,900 | 1,787.1 | 84.4 | unavailable | +0.36 [+0.00, +0.62] | yes | `20261115T155501.941627+0000_kapitsa_clover-35b-a3b_session.json` |
| 6 | `qwen3.6-35b-a3b` | Splash | Splash | MoE | 262,144 | 4 | 4,358,144 | 25.61 @1x | 2x 26.92 | 1x 3/3, 2x 5/6 | 5,768 | 2,478.5 | 207.1 | 6,613 / 464.8 | +0.43 [+0.08, +0.67] | yes | `20261126T011537.996892+0000_splash_qwen3-6-35b-a3b_session.json` |
| 7 | `flint-gguf` | Splash | Splash | MoE | 262,144 | 4 | 802,816 | 23.81 @1x | 2x 25.39 | 1x 3/3, 2x 5/6 | 10,108 | 1,872.1 | 147.3 | 5,183 / 228.5 | +0.29 [-0.07, +0.57] | yes | `20261126T015113.461985+0000_splash_flint-gguf_session.json` |
| 8 | `muse-glimmer-30b-mlx` | Ollama | MLX | dense | 131,072 | 1 | 131,072 allocated | 20.12 @1x | -- | 2/2 | 1,514 | 699.0 | 44.0 | unavailable | +0.64 [+0.28, +0.84] | yes | `20261115T163512.190267+0000_ollama_muse-glimmer-30b-mlx_session.json` |
| 9 | `qwen3.6-35b-a3b-splash` | LM Studio | Splash | MoE | 262,144 | 1 | 262,144 | 19.59 @1x | -- | 3/3 | 5,552 | -- | 196.2 | 3,784 / 411.5 | +0.43 [+0.08, +0.67] | yes | `20261125T051059.051941+0000_lmstudio_qwen3-6-35b-a3b-splash_session.json` |
| 10 | `nemotron-3.5-super-mlx` | Ollama | MLX | hybrid MoE | 524,288 | 1 | 524,288 allocated | 12.79 @1x | -- | 3/3 | 5,961 | 939.4 | 55.3 | unavailable | +0.57 [+0.21, +0.79] | yes | `20261115T170024.380238+0000_ollama_nemotron-3-5-super-mlx_session.json` |
| 11 | `qwen3.8-27b` | Splash | Splash | dense | 262,144 | 4 | 1,417,216 | 11.76 @4x | 1x 9.87, 2x 11.14 | 1x 3/3, 2x 6/6, 4x 12/12 | 9,769 | 736.7 | 66.5 | 1,361 / 146.5 | +0.86 [+0.52, +0.98] | yes | `20261126T041444.959567+0000_splash_qwen3-8-27b_session.json` |
| 12 | `bonsai2.5-27b-pq2` | Splash | Splash | dense | 262,144 | 4 | 1,671,168 | 9.89 @2x | 1x 9.47 | 1x 3/3, 2x 4/4 | 9,483 | 618.5 | 73.7 | 1,051 / 205.2 | +0.64 [+0.30, +0.83] | yes | `20261126T083600.610103+0000_splash_bonsai2-5-27b-pq2_session.json` |
| 13 | `qwen3.8-27b-splash` | LM Studio | Splash | dense | 262,144 | 1 | 262,144 | 9.42 @1x | -- | 3/3 | 3,967 | -- | 56.3 | unavailable | +0.79 [+0.44, +0.94] | yes | `20261125T054544.743268+0000_lmstudio_qwen3-8-27b-splash_session.json` |
| 14 | `nemotron-3.5-bolt-74b-a9b-q3kxl` | Ollama | llama.cpp | hybrid MoE | 262,144 | 1 | 262,144 allocated | 9.09 @1x | -- | 2/2 | 6,056 | 743.0 | 32.2 | unavailable | +0.36 [-0.01, +0.64] | yes | `20261115T183056.692043+0000_ollama_nemotron-3-5-bolt-74b-a9b-q3kxl_session.json` |
| 15 | `granite4.2-30b-4bit` | vLLM-Metal | vLLM, MLX | hybrid MoE | 131,072 | 5 | 331,584 | 2.94 @2x | 1x 2.62 | 1x 2/2, 2x 4/4 | 14,529 | 351.5 | 10.8 | 856 / 30.7 | +0.57 [+0.21, +0.79] | yes | `20261125T021927.129766+0000_vllm-metal_granite4-2-30b-4bit_session.json` |
| 16 | `nanbeige4.3-33b-q4km` | Ollama | llama.cpp | dense | 262,144 | 1 | 262,144 allocated | 1.47 @1x | -- | 2/2 | 9,242 | 128.4 | 6.0 | unavailable | +0.43 [+0.06, +0.69] | yes | `20261115T223449.004542+0000_ollama_nanbeige4-3-33b-q4km_session.json` |
| -- | `qwen3.6-35b-a3b-mlx` | LM Studio | MLX | MoE | 262,144 | 4 | 1,048,576 | 16.05 @1x | 2x 11.05 | 1x 2/2, 2x 3/4 | 4,440 | -- | 71.6 | 2,754 / 148.8 | +0.36 [+0.02, +0.60] | no (noncanonical_settings) | `20261125T013213.017922+0000_lmstudio_qwen3-6-35b-a3b-mlx_session.json` |
| -- | `ornith1.5-122b` | Splash | Splash | MoE | 262,144 | 4 | 1,974,272 | 11.87 @1x | 2x 11.80 | 1x 2/2, 2x 4/4 | 6,254 | 744.2 | 73.5 | 1,807 / 170.1 | not scored | yes | `20261031T125002.145677+0000_splash_ornith1-5-122b_session.json` |
| -- | `mimo-v2.6-flash-q2ks` | Ollama | llama.cpp | MoE | 262,144 | 1 | 262,144 allocated | 5.29 @1x | -- | 3/3 | 3,720 | 313.7 | 22.3 | unavailable | not scored | yes | `20261116T010801.194651+0000_ollama_mimo-v2-6-flash-q2ks_session.json` |
| -- | `qwen3.8-27b-mlx` | LM Studio | MLX | dense | -- | -- | -- | no session | -- | -- | -- | -- | -- | -- | not scored | -- | -- |

<!-- /results:audit -->

- `nemotron-3.5-lightning-30b-mlx` and the other Ollama MLX profiles run on
  the MLX runner, which serializes requests to one slot.
  `nemotron-3.5-super-mlx` (Super VL 120B-A12B, NVFP4) holds 74.41 GiB at
  524,288 and leaves about 14 GiB available at that depth.
- `ornith1.5-35b-a3b` (DeepReinforce's MLX 4-bit, text-only) decodes with the
  Qwen3.6-35B-A3B DFlash2 draft: Ornith is a structural twin of that model.
- `qwen3.8-flash-next-iq3s` (Qwen3.8-Flash-Next 125B-A6B, ISTA-DASLab's
  GSQ-RCO IQ3_S, 83.6 GB) is the Flash-Next build that audits best here;
  ds4 serves the same model for interactive use at a third of the rate.
- `clover-35b-a3b` decodes self-speculatively on Kapitsa; two streams hold
  the rate, so one is its operating point.
- `qwen3.6-35b-a3b` on Splash peaks at one stream: one 2x session was
  incomplete, and most of its calls stream no reasoning.
- The two `qwen3.8-27b` rows serve the same MLX 4-bit model: LM Studio's
  Splash engine one request at a time, native Splash with four slots, all
  four used at its operating point. `bonsai2.5-27b-pq2` (Ternary Bonsai 2.5
  27B, PQ2_0) runs 84% of native Splash's rate in less than half its weight
  memory.
- `inkling-2-mini` (Inkling 2 Mini, Unsloth UD-Q4_K_M) decodes with its
  DFlash2 draft.
- `nemotron-3.5-bolt-74b-a9b-q3kxl` (Unsloth UD-Q3_K_XL, 39 GB) runs all 89
  layers on the GPU; Bolt's NVFP4 build would put its tensors on the CPU
  under llama.cpp's Metal backend.
- `granite4.2-30b-4bit` runs on vLLM-Metal, slow at 131k; on Ollama its
  session fails on a stream that ends without a usage chunk.
- `nanbeige4.3-33b-q4km` (dense 33B) decodes 16.9 falling to 6.3 tok/s
  through a session; its 245,755-token cold prefill takes 2,750 s.
- `ornith1.5-122b`, Ollama `mimo-v2.6-flash-q2ks` and LM
  Studio `qwen3.8-27b-mlx` fail Capability Check v3 compatibility, so their
  rates cannot rank them. LM Studio `qwen3.6-35b-a3b-mlx` passes, but its
  MLX engine needs the protocol's off-by-one token allowance, so its runs
  are noncanonical by design. `qwen3.8-27b-mlx` has no session.

## Interactive profiles

These profiles serve interactive agentic sessions and are not ranked for
audits. ds4 serves large MoE models on one slot; its interactive decode
measurements are in [ds4/BENCHMARKS.md](../../ds4/BENCHMARKS.md).

<!-- results:interactive -->

| Profile | Runtime | Engine | Tier | Context | Slots | KV pool | Sessions/h by streams | Complete | Out tok/session 1x | Prefill tok/s 1x | Report decode 1x | pp512 / tg128 | Publishable | Session JSON |
| -- | -- | -- | -- | --: | --: | --: | -- | -- | --: | --: | --: | -- | -- | -- |
| `glm5.3-flash-q2` | ds4 | ds4, Metal | MoE | 262,144 | 1 | 262,144 | 1x 4.86 | 2/2 | 2,558 | 365.6 | 26.9 | 352 / 35.1 | yes | `20261126T215646.522189+0000_ds4_glm5-3-flash-q2_session.json` |
| `qwen3.8-flash-next-q4` | ds4 | ds4, Metal | MoE | 524,288 | 1 | 524,288 | 1x 9.57 | 3/3 | 5,896 | 1,265.0 | 62.7 | unavailable | yes | `20261124T205128.945378+0000_ds4_qwen3-8-flash-next-q4_session.json` |
| `gemma4-26b-mlx` | Ollama | MLX | MoE | 262,144 | 1 | 262,144 allocated | 1x 25.63 | 2/3 | 1,723 | 1,679.1 | 35.0 | unavailable | no (incomplete_sessions) | `20261116T081609.374316+0000_ollama_gemma4-26b-mlx_session.json` |

<!-- /results:interactive -->

- `qwen3.8-flash-next-q4` on ds4 runs at 524,288 (YaRN); 76-81% of each
  session's prompt tokens come from cache, against about 90% on Splash,
  because ds4 cannot rewind its live state to a shared prefix.
- `gemma4-26b-mlx` (Gemma 4 26B-A4B, the registry's NVFP4 build) passes
  Capability Check v3, but one of three reports recalled no findings, so the
  run is unpublishable.
- ds4 `deepseek-v4-flash-q2` and `deepseek-v4.1-flash-q2` have no
  AuditBench v3 session; their capability rows are below.

## Capability Check

Capability Check v3 (llm-audit-bench 3.0.0), run 2026-11-19/22 on the
runtimes above, the LM Studio Splash-engine rows re-checked on engine 1.3.0
on 2026-11-25, the Splash rows on Splash 1.7.3 on 2026-11-25/26, ds4
`glm5.3-flash-q2` on 2026-11-26 with the GLM tool-argument patch.
The protocol and the column mapping are in llm-audit-bench
`docs/CAPABILITY.md`, the campaign runbook in
[CAPABILITIES.md](../../CAPABILITIES.md). Campaign marks the profiles this
hardware's campaigns run. Model identity shows the first 12 characters of
the digest or revision; every row's live identity matched the one pinned in
its model config. An audit row's score is in the audit ranking.

<!-- results:capability -->

| Runtime | Profile | Campaign | Identity | Reasoning | Thinking off | Tool call | Streaming tool call | Tool loop | JSON | Unaided document | Schema enforced | Clean samples | Compatibility | Audit aptitude | Model identity | Artifact |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| Kapitsa | `clover-35b-a3b` | yes | passed | passed | supported | supported | supported | supported | supported | valid | unsupported (refused) | 34 of 36 (94%); fitness 8 of 8 | passed | sound 8 of 8 | `4b0402b65e52` | `20261119T160555.416930+0000_kapitsa_clover-35b-a3b.json` |
| LM Studio | `qwen3.6-35b-a3b-splash` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `0f4714b2db37` | `20261125T051058.649609+0000_lmstudio_qwen3-6-35b-a3b-splash.json` |
| LM Studio | `qwen3.8-27b-splash` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `9d27070b71f7` | `20261125T054544.352552+0000_lmstudio_qwen3-8-27b-splash.json` |
| Ollama | `muse-glimmer-30b-mlx` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `015fa21845be` | `20261119T154421.554447+0000_ollama_muse-glimmer-30b-mlx.json` |
| Ollama | `nanbeige4.3-33b-q4km` | yes | passed | passed | supported | supported | supported | supported | supported | valid | unsupported (refused) | 35 of 36 (97%); fitness 8 of 8 | passed | sound 8 of 8 | `f630b1711fd6` | `20261120T163001.592389+0000_ollama_nanbeige4-3-33b-q4km.json` |
| Ollama | `nemotron-3.5-bolt-74b-a9b-q3kxl` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 35 of 36 (97%); fitness 8 of 8 | passed | sound 8 of 8 | `bdeed349c1c2` | `20261120T025423.974659+0000_ollama_nemotron-3-5-bolt-74b-a9b-q3kxl.json` |
| Ollama | `nemotron-3.5-lightning-30b-mlx` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 35 of 36 (97%); fitness 8 of 8 | passed | sound 6 of 8 | `d1e17d7dabac` | `20261119T153335.892402+0000_ollama_nemotron-3-5-lightning-30b-mlx.json` |
| Ollama | `nemotron-3.5-super-mlx` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `aba4cee1e75e` | `20261120T000927.447388+0000_ollama_nemotron-3-5-super-mlx.json` |
| Splash | `bonsai2.5-27b-pq2` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `28a7093cc25b` | `20261126T011514.131637+0000_splash_bonsai2-5-27b-pq2.json` |
| Splash | `flint-gguf` | yes | passed | passed | untested | supported | supported | supported | supported | valid | whitespace_runaway (broken) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `20468edfc38a` | `20261125T215934.907846+0000_splash_flint-gguf.json` |
| Splash | `inkling-2-mini` | yes | passed | passed | untested | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `8078d149286e` | `20261125T222933.339127+0000_splash_inkling-2-mini.json` |
| Splash | `ornith1.5-35b-a3b` | yes | passed | passed | supported | supported | supported | supported | supported | json_only | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `19504d912fa8` | `20261125T221226.947488+0000_splash_ornith1-5-35b-a3b.json` |
| Splash | `qwen3.6-35b-a3b` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 6 of 8 | `38740b847e4c` | `20261125T214029.579805+0000_splash_qwen3-6-35b-a3b.json` |
| Splash | `qwen3.8-27b` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 35 of 36 (97%); fitness 7 of 8 | passed | sound 6 of 7 | `10c35caafbb8` | `20261125T235459.370786+0000_splash_qwen3-8-27b.json` |
| Splash | `qwen3.8-flash-next-iq3s` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 7 of 8 | `ed59f92082b1` | `20261125T230437.201806+0000_splash_qwen3-8-flash-next-iq3s.json` |
| vLLM-Metal | `granite4.2-30b-4bit` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `d3f143b44006` | `20261119T175225.897910+0000_vllm-metal_granite4-2-30b-4bit.json` |
| LM Studio | `qwen3.6-35b-a3b-mlx` | yes | passed | passed | untested | supported | supported | supported | supported | valid | ignored (broken) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `38740b847e4c` | `20261120T170233.333159+0000_lmstudio_qwen3-6-35b-a3b-mlx.json` |
| LM Studio | `qwen3.8-27b-mlx` | yes | passed | passed | untested | supported | supported | supported | supported | valid | ignored (broken) | 24 of 31 (77%); fitness 7 of 8 | failed (clean_rate) | not scored | `10c35caafbb8` | `20261120T185445.662511+0000_lmstudio_qwen3-8-27b-mlx.json` |
| Ollama | `mimo-v2.6-flash-q2ks` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 23 of 27 (85%); fitness 7 of 8 | failed (clean_rate) | not scored | `aecb7b7e21a4` | `20261120T042350.276175+0000_ollama_mimo-v2-6-flash-q2ks.json` |
| Splash | `ornith1.5-122b` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 14 of 19 (74%); fitness 8 of 8 | failed (clean_rate) | not scored | `06a57aba4fba` | `20261125T231824.661553+0000_splash_ornith1-5-122b.json` |
| ds4 | `glm5.3-flash-q2` | yes | passed | passed | supported | supported | supported | supported | supported | valid | ignored (broken) | 33 of 36 (92%); fitness 7 of 8 | passed | +0.64 [+0.28, +0.84]; sound 7 of 7 | `b2fa29d7a6b4` | `20261126T215646.241610+0000_ds4_glm5-3-flash-q2.json` |
| ds4 | `qwen3.8-flash-next-q4` | yes | passed | passed | supported | supported | supported | supported | supported | valid | ignored (broken) | 36 of 36 (100%); fitness 8 of 8 | passed | +0.86 [+0.52, +0.98]; sound 8 of 8 | `d600fe1a43d2` | `20261119T225509.672284+0000_ds4_qwen3-8-flash-next-q4.json` |
| ds4 | `deepseek-v4-flash-q2` | no | passed | passed | supported | supported | supported | supported | supported | valid | ignored (broken) | 33 of 36 (92%); fitness 7 of 8 | passed | +0.71 [+0.36, +0.89]; sound 6 of 7 | `f71f23d552d6` | `20261120T201931.719098+0000_ds4_deepseek-v4-flash-q2.json` |
| ds4 | `deepseek-v4.1-flash-q2` | no | passed | passed | supported | supported | supported | supported | supported | valid | ignored (broken) | 34 of 36 (94%); fitness 8 of 8 | passed | +0.71 [+0.36, +0.89]; sound 8 of 8 | `9dcee51692e6` | `20261122T023508.810868+0000_ds4_deepseek-v4-1-flash-q2.json` |
| Ollama | `gemma4-26b-mlx` | yes | passed | passed | supported | supported | supported | supported | supported | valid | whitespace_runaway (broken) | 36 of 36 (100%); fitness 8 of 8 | passed | +0.64 [+0.28, +0.85]; sound 7 of 8 | `f60799545325` | `20261119T145038.089065+0000_ollama_gemma4-26b-mlx.json` |

<!-- /results:capability -->

- Splash `ornith1.5-122b` fails on clean rate, 14 of 19: five
  vulnerability answers fail the format, past the floor, which stops the
  check after 11 of 28 cases. Its 35B sibling passes 36 of 36.
- LM Studio `qwen3.8-27b-mlx` fails on clean rate, 24 of 31: mlx-llm 1.14.0
  crashed on a Metal resource limit with four requests in flight. The
  Splash-engine profile of the same model passes 36 of 36.
- Ollama `mimo-v2.6-flash-q2ks` fails on clean rate, 23 of 27 (two format
  failures, two runaways).
- ds4 `glm5.3-flash-q2` passes with the repository's GLM tool-argument
  patch; unpatched ds4 returns every argument as a JSON string (see
  [ds4/BENCHMARKS.md](../../ds4/BENCHMARKS.md#capability-check-v3)).
- Schema enforcement never gates. It is broken on Ollama `gemma4-26b-mlx`
  and Splash `flint-gguf` (whitespace runaway), ignored by both LM Studio
  MLX profiles and by ds4, which has no `response_format`, and refused by
  Ollama Nanbeige and Kapitsa.
