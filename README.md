# llm-local-servers

Measured, Makefile-driven local LLM serving. Five managed runtimes --
vLLM (CUDA), Ollama, vLLM-Metal, Splash (Apple Silicon) and LM Studio --
with one portable config per model, host-adaptive launchers, isolated remote-host
operation, and the retained benchmark and capability results for every
host in the fleet. The workload everything is tuned for is deep-context
security-audit calls; [AGENTS.md](AGENTS.md) states the mission and the
invariants.

Serving performance is measured with AuditBench v1 and API compatibility
is gated with Capability Check v1. Both live in the sibling
[llm-audit-bench](https://github.com/tuminoid/llm-audit-bench)
repository (`docs/PROTOCOL.md` and `docs/CAPABILITY.md` are the
canonical protocol documents); this repository holds the runtime
adapters, model configs, and results.

## Setup

1. Clone [llm-audit-bench](https://github.com/tuminoid/llm-audit-bench)
   beside this repository, or point `AUDIT_BENCH_DIR` at an existing
   checkout. The harness is standard-library Python; there is nothing to
   install.
2. Copy `.envrc.example` to `.envrc`, fill in the personal values (the
   remote GPU host alias), and `direnv allow` -- or export the same
   variables from your shell. Committed files carry no personal values.
3. Install the runtime you intend to serve with; prerequisites and
   host-tuning rationale are per runtime in
   [vllm/README.md](vllm/README.md),
   [ollama/README.md](ollama/README.md),
   [vllm-metal/README.md](vllm-metal/README.md),
   [splash/README.md](splash/README.md), and
   [lmstudio/README.md](lmstudio/README.md).

Development needs `shellcheck`, `markdownlint-cli2`, and Python 3.10 or
newer for `make lint` and `make test`.

## Running

Everything runs from the repository root through make; `make help`
prints the full list. The lifecycle verbs are uniform across runtimes:

| Verb | Does |
| -- | -- |
| `make <runtime>-start MODEL=<name>` | Start detached, wait until serving |
| `make <runtime>-stop` | Stop by pidfile, verify the GPU or process group was released |
| `make <runtime>-status` | Process, memory split, context allocation, KV sizing |
| `make <runtime>-logs` | Follow the server log |
| `make <runtime>-bench MODEL=<name>` | Run AuditBench v1 |
| `make <runtime>-capability MODEL=<name>` | Run Capability Check v1 |

where `<runtime>` is `vllm`, `ollama`, `vllm-metal`, `splash`, or `lmstudio`
(plus `ollama-install`, `vllm-metal-install`, `vllm-metal-pull`,
`splash-install`, `splash-pull`, `lmstudio-install`, and `lmstudio-pull` for
runtime and model installation). `MODEL` names a config file in that
runtime's `models/` directory, never a served model ID or registry tag;
there is deliberately no default model.

The vLLM and Ollama runtimes also run on a remote GPU host over ssh:
`make vllm-remote-{bootstrap,start,stop,status,logs,bench,capability}`
and the matching `ollama-remote-*` set, with `HOST=<ssh-host>` supplied
by `.envrc` or the command line. Remote Ollama is fully isolated from
the host's own Ollama (own binary, model cache, state, and port), and
the guards are causal: a target refuses when the live server state
contradicts it, from start on a busy GPU or claimed port to bootstrap
under a running server. Servers bind loopback only; reach a remote one
through `make vllm-remote-tunnel` (localhost:8001) or
`make ollama-remote-tunnel` (localhost:11436).

## Measured overview

Canonical AuditBench v1 medians copied from [vllm/BENCHMARKS.md](vllm/BENCHMARKS.md),
[ollama/BENCHMARKS.md](ollama/BENCHMARKS.md),
[vllm-metal/BENCHMARKS.md](vllm-metal/BENCHMARKS.md), and
[splash/BENCHMARKS.md](splash/BENCHMARKS.md), which hold the
evidence, ranges, caveats, replay results, and history; nothing here is
derived. Capability pass/fail is in [CAPABILITIES.md](CAPABILITIES.md).
Prefill and decode are aggregate tok/s, audit columns are calls/hour,
`@Nx` names the measured concurrency, and `GPU KV / allocation` is the
raw vLLM pool or Ollama's measured allocation.

### Audit conversations per hour, per host

The mission workload: a growing tool-loop conversation resent every
turn, verdict at depth, with 262,144 configured context and 16 tool
steps. Actual verdict input counts are recorded per runtime; Splash
measured about 164k. One row per runtime and model, ranked within a
host only; a MoE or hybrid row and a dense row are not comparable.
`Decode 1x` is the matching operating point's short-prompt decode ceiling.

A100-SXM4-80GB:

| Rank | Runtime and profile | Tier | Cache | Decode 1x | Conv/hour |
| --: | -- | -- | -- | --: | --: |
| 1 | vLLM `qwen3.6-35b-a3b-awq` | MoE | align APC | 147.68 | 85.9 |
| 2 | vLLM `qwen3-coder-30b` | MoE | APC | 149.49 | 45.2 |
| 3 | vLLM `gemma4-26b-a4b-awq` | MoE | APC | 169.40 | 43.8 |
| 4 | Ollama `qwen3.6-35b-a3b` GGUF | MoE | slot cache | 84.58 | 32.0 |
| 5 | Ollama `qwen3-coder-30b` GGUF | MoE | slot cache | 114.41 | 26.0 |
| 6 | vLLM `qwen3.8-27b-dflash2` | dense | align APC + DFlash 2 | 124.16 | 23.3 |
| 7 | Ollama `qwen3.8-27b-native` | dense | slot cache | 74.31 | 15.3 |
| 8 | Ollama `qwen3.8-flash-next-gguf-iq4xs` (125B-A6B) | MoE | slot cache | 51.38 | 10.5 |

Apple M5 Max:

| Rank | Runtime and profile | Tier | Cache | Decode 1x | Conv/hour |
| --: | -- | -- | -- | --: | --: |
| 1 | Ollama `nemotron-3.5-lightning` MLX | hybrid MoE | MLX trie | 141.7 | 34.4 |
| 2 | vLLM-Metal `mimo-v2.6-9b-4bit` | dense | align APC | 69.6 | 15.7 |
| 3 | vLLM-Metal `qwen3.6-35b-a3b-4bit` | MoE | align APC | 102.0 | 12.9 |
| 4 | Splash `qwen3.8-27b` | dense | state/prefix cache + DFlash 2 | 67.31 | 10.29 |
| 5 | Ollama `qwen3.8-flash-next-gguf` (125B-A6B) | MoE | slot cache | 38.69 | 7.2 |
| 6 | vLLM-Metal `nemotron-3.5-lightning-30b-4bit` | hybrid MoE | off | 123.0 | 4.9 |
| 7 | vLLM-Metal `qwen3.8-27b-4bit` | dense | align APC | 28.8 | 4.2 |
| 8 | Ollama `qwen3.8-27b` GGUF | dense | slot cache + MTP | 44.7 | 3.5 |
| 9 | vLLM-Metal `gemma4-31b-4bit` | dense | APC | 26.6 | 2.4 |
| -- | Splash `qwen3.6-35b-a3b` | MoE | state/prefix cache + DFlash 2 | 301.08 | 37.16 (1/2 compliant) |
| -- | vLLM-Metal `ornith1.5-35b-a3b-4bit` | hybrid MoE | align APC | 101.5 | 7.6 (1/2 compliant) |

Splash qwen3.6's 37.16/h and vLLM-Metal ornith's 7.6/h are the rates of
their sole compliant samples; the other sample stopped after one and
fifteen of 16 files respectively. Both are shown unranked because the
conversation campaign failed the fixture gate. vLLM-Metal granite (0/2
compliant on its 131k fixture) has no conversation rate.

Splash fixed-transcript replay on this host, 16 steps and about 164k
verdict input. These are separate workloads from conversation and from
each other; verdict output lengths also differ between models. Details
and ranges are in [splash/BENCHMARKS.md](splash/BENCHMARKS.md).

| Profile | Replay/hour, 32-token probe cap | Concurrent replay/hour, 1,024-token probe cap, 1/2/4 streams |
| -- | --: | --: |
| `qwen3.6-35b-a3b` | 15.09 | 12.91 / 12.35 / 12.38 |
| `qwen3.8-27b` | 10.17 | 4.38 / 4.32 / 4.06 |

Apple M5 Max, 131k shape (9 tool steps, ~115k resident; qwen3.6 is
pinned to 131,072 on the Ollama MLX runner because 262,144 triggers its
memory runaway). Not comparable with the tables above:

| Rank | Runtime and profile | Tier | Cache | Decode 1x | Conv/hour |
| --: | -- | -- | -- | --: | --: |
| 1 | Ollama `qwen3.6:35b-a3b-coding-nvfp4` MLX | MoE | MLX trie | 126.7 | 50.9 |
| 2 | Ollama `qwen3.6:35b-a3b-nvfp4` MLX (base) | MoE | MLX trie | 140.8 | 48.1 |

RTX PRO 3000:

| Rank | Runtime and profile | Tier | Cache | Decode 1x | Conv/hour |
| --: | -- | -- | -- | --: | --: |
| 1 | Ollama `qwen3.5:9b` | dense | slot cache | 37.83 | 9.8 |

Excluded from ranking for fixture non-compliance: both qwen3.5-4b stacks
and the CPU-assisted qwen3.6 on the RTX, GLM 4.7 Flash and Ollama
gemma4-26b on the A100, and Splash qwen3.6 and vLLM-Metal ornith (1/2
conversation samples compliant) and vLLM-Metal granite (0/2) on the M5.
The A100 vLLM `qwen3-coder-30b` rate stands but the profile fails
Capability Check v1 (two tool calls for a one-call fixture).

### A100-SXM4-80GB

Remote host: sm_80, 81,920 MiB VRAM. vLLM rows: 0.29.0 for the two qwen3.8
profiles, 0.28.0 for the rest, Transformers 5.15.1. Ollama rows: isolated
Ollama, 0.34.2 for qwen3.8-27b-native and flash-next, 0.32.14 for the rest;
Flash Attention, q8 KV.

| Runtime and profile | Context | Slots | GPU KV / allocation | 32k prefill | Peak decode | Audit 32k | Audit half | Audit deep | Near-context proof |
| -- | --: | --: | -- | --: | --: | --: | --: | --: | -- |
| vLLM `qwen3.6-35b-a3b-awq` | 262,144 | 8 | 2,714,989 KV | 15,558.4 | 867.22 @8x | 992.75 @8x | 148.07 | 84.59 @4x | 8 x 245,752 in 359.58s |
| Ollama `qwen3.6:35b-a3b` | 262,144 | 1 | 0.00 / 25.34 GiB | 4,165.7 | 84.58 | 176.52 | 64.82 | 42.81 | 245,752 in 85.26s |
| vLLM `gemma4-26b-a4b-awq` | 262,144 | 8 | 1,867,456 KV | 7,603.9 | 1,072.38 @8x | 595.22 @8x | 58.53 | 26.22 @4x | 4 x 245,774 in 625.92s |
| Ollama `gemma4:26b` | 262,144 | 8 | 0.00 / 25.32 GiB | 3,246.7 | 231.48 @8x | 222.32 @8x | 53.51 | 27.68 @4x | 8 x 245,777 in 1,030.85s |
| vLLM `qwen3-coder-30b` | 262,144 | 8 | 513,152 KV | 8,551.3 | 1,019.74 @8x | 515.11 @8x | 61.55 | 27.20 @1x | 2 x 245,762 in 289.67s |
| vLLM `qwen3.8-27b-dflash2` | 262,144 | 8 | 507,737 KV | 2,702.5 | 597.01 @8x | 228.51 @8x | 35.48 | 22.88 @2x | 2 x 245,748 in 323.42s |
| vLLM `qwen3.8-27b` | 262,144 | 8 | 746,456 KV | 2,700.3 | 344.97 @8x | 218.65 @8x | 38.94 | 23.49 @2x | 2 x 245,748 in 326.04s |
| Ollama `qwen3.8-27b-native` | 262,144 | 1 | 0.00 / 17.27 GiB | 1,089.4 | 74.31 | 78.38 | 22.15 | 11.63 | 245,752 in 337.33s |
| Ollama `qwen3.8-flash-next-gguf-iq4xs` | 262,144 | 2 | 0.00 / 62.84 GiB | 958.8 | 83.26 @2x | 63.50 @2x | 15.88 | 8.96 @1x | 2 x 245,748 in 853.61s |
| Ollama `qwen3-coder-30b` | 262,144 | 4 | 0.00 / 70.39 GiB | 2,729.4 | 186.96 @4x | 132.09 @4x | 26.45 | 14.82 @1x | 4 x 245,762 in 1,016.28s |
| vLLM `glm4.7-flash-awq` | 202,752 | 8 | 1,050,624 KV | 7,346.1 | 365.23 @8x | 367.58 @8x | 66.04 | 37.28 @4x | 4 x 190,092 in 419.78s |
| Ollama `glm4.7-flash` | 202,752 | 8 | 0.00 / 63.01 GiB | 1,457.8 | 268.75 @8x | 112.63 @8x | 21.23 | 8.39 @1x | 8 x 190,092 in 3,703.26s |

### Apple M5 Max (128 GB unified memory)

Local host: MacBook Pro `Mac17,6`, 40 GPU cores, macOS 26.6.2. Ollama
MLX rows: managed official Ollama 0.32.14, MLX runner on
`mlx_metal_v4`, safetensors NVFP4 artifacts; the runner serializes
requests to one slot. Ollama GGUF rows run the llama.cpp runner with
q8 KV: flash-next measured on the 0.33.3 runtime with two real slots
(the profile now pins 0.34.2), qwen3.8-27b on 0.34.2 at its native
262,144 with one slot and the registry Modelfile's MTP drafting.
vLLM-Metal rows: pinned plugin venv 0.29.0, serving-default cache pins
(align APC; nemotron cache off), paged KV, NAX prefill.
Splash rows: release 1.0 on macOS 27.0, 64 GiB native memory cap,
four active slots, DFlash 2 and prefix/state caching. Its KV column is
sparse virtual capacity, not committed memory. All eight managed campaign
reports are canonical and publishable. Long-run teardown needed recovery;
the benchmark record retains the failures and verified final release.

| Runtime | Model or profile | Context | KV pool | Prefill 32k/64k/128k tok/s | Decode 1/2/4 tok/s | audit_32k /h | audit_half /h | audit_deep /h |
| -- | -- | --: | --: | --: | --: | --: | --: | --: |
| Splash | `qwen3.6-35b-a3b`, 64 GiB, 4 slots | 262,144 | 4,415,488 virtual | 4,455 / 3,241 / 2,237 | 301.1 / 375.1 / 515.4 | 375.3 @4x | 58.7 | 23.4 @1x |
| Splash | `qwen3.8-27b`, 64 GiB, 4 slots | 262,144 | 1,474,560 virtual | 796 / 704 / 559 | 67.3 / 119.6 / 152.0 | 66.4 @4x | 14.3 | 6.6 @1x |
| vLLM-Metal | `qwen3.6-35b-a3b-4bit` APC (serving), util 0.71, seqs 5 | 262,144 | 1,326,140 | 2,543 / 1,646 / 1,066 | 102.0 / 174.3 / 265.0 | 117.9 @4x | 19.1 | 9.9 @4x |
| vLLM-Metal | `qwen3.8-27b-4bit` APC (serving), util 0.91, seqs 5 | 262,144 | 603,469 | 568 / 450 / 316 | 28.8 / 52.8 / 82.6 | 39.0 @4x | 6.6 | 3.3 @1x |
| vLLM-Metal | `mimo-v2.6-9b-4bit` APC, util 0.90, seqs 5 | 262,144 | 1,323,749 | 1,666 / 1,420 / 989 | 69.6 / 129.8 / 218.0 | 118.0 @4x | 20.1 | 9.9 @1x |
| vLLM-Metal | `nemotron-3.5-lightning-30b-4bit` cache off, util 0.32, seqs 5 | 262,144 | 1,591,012 | 3,359 / 2,738 / 2,323 | 123.0 / 185.6 / 267.0 | 197.4 @2x | 42.9 | 25.9 @1x |
| vLLM-Metal | `ornith1.5-35b-a3b-4bit` APC, util 0.70, seqs 5 | 262,144 | 1,300,439 | 2,623 / 1,664 / 1,075 | 101.5 / 173.5 / 264.3 | 117.5 @4x | 19.0 | 9.9 @4x |
| vLLM-Metal | `granite4.2-30b-4bit` APC, util 0.91, seqs 5 | 131,072 | 331,584 | 558 / 446 / - | 30.8 / 55.6 / 88.6 | 31.0 @2x | 13.8 (65k) | 9.3 (114.7k) |
| vLLM-Metal | `gemma4-31b-4bit` APC, util 0.91, seqs 5 | 262,144 | 617,308 | 355 / 243 / 148 | 26.6 / 47.9 / 72.0 | 17.3 @4x | 2.6 | 1.4 @2x |
| Ollama | `qwen3.8-flash-next-gguf` (125B-A6B, llama.cpp, 0.33.3) | 262,144 | 2 slots | 632 / 518 / 406 | 38.7 / 57.2 / - | 47.4 @2x | 9.7 | 5.1 @1x |
| Ollama | `qwen3.8:27b` (Q4_K_M GGUF, llama.cpp, 0.34.2, MTP) | 262,144 | one slot | 450 / 327 / 206 | 44.7 / - / - | 34.7 @1x | 5.2 | 2.0 @1x |
| Ollama | `nemotron-3.5-lightning:30b-a3b-mlx` | 262,144 | one slot | 4,040 / 3,072 / 2,628 | 141.7 / - / - | 212.8 @1x | 58.3 | 31.1 @1x |
| Ollama | `qwen3.6:35b-a3b-coding-nvfp4` (MLX) | 131,072 | one slot | 3,242 / 2,305 / - | 126.7 / - / - | 180.4 @1x | 88.5 (65k) | 48.7 (114.7k) |
| Ollama | `qwen3.6:35b-a3b-nvfp4` (MLX, base) | 131,072 | one slot | 3,190 / 2,224 / - | 140.8 / - / - | 188.7 @1x | 91.2 (65k) | 47.7 (114.7k) |

The qwen3.6 NVFP4 rows run the 131,072 operating point; their
parenthesized half and deep targets are 65k and 114.7k.

### RTX PRO 3000 Blackwell laptop GPU

Local host: sm_120, 12,227 MiB VRAM, 62 GiB RAM.

| Runtime and profile | Context | Slots | GPU KV / allocation | 32k prefill | Peak decode | Audit 32k | Audit half | Audit deep | Near-context proof |
| -- | --: | --: | -- | --: | --: | --: | --: | --: | -- |
| vLLM `gemma4-e2b-awq` | 131,072 | 2 | 450,444 KV | 4,835.1 | 303.54 @2x | 289.55 @2x | 113.31 | 56.89 @2x | 2 x 122,896 in 124.89s |
| vLLM `qwen3.5-4b-awq` | 131,072 | 2 | 274,432 KV | 4,686.9 | 176.12 @2x | 250.94 @2x | 113.76 | 85.82 @2x | 2 x 122,861 in 87.77s |
| Ollama `gemma4:e2b` | 131,072 | 4 | 0.00 / 2.66 GiB | 3,582.5 | 247.40 @4x | 184.88 @4x | 99.42 | 67.33 @1x | 4 x 122,903 in 217.03s |
| Ollama `qwen3.5:9b` | 262,144 | 1 | 0.00 / 10.21 GiB | 1,654.8 | 37.83 | 70.34 | 22.10 | 12.26 | 245,752 in 311.57s |
| Ollama `qwen3.5:4b` | 131,072 | 1 | 0.00 / 6.04 GiB | 2,057.6 | 67.43 | 100.55 | 59.19 | 41.92 | 122,861 in 84.87s |
| Ollama `gemma4:12b` | 262,144 | 1 | 0.00 / 7.96 GiB | 1,242.8 | 32.36 | 59.82 | 16.67 | 8.31 | 245,777 in 462.12s |
| Ollama `qwen3.6:35b-a3b` (CPU-assisted) | 262,144 | 1 | 14.53 / 10.21 GiB | 303.4 | 30.99 | 25.09 | 7.00 | 4.00 | 245,752 in 927.94s |
| Ollama `qwen3.8:27b` (CPU-assisted) | 131,072 | 1 | 12.49 / 7.64 GiB | 188.3 | 2.93 | 2.70 | 1.83 | 2.15 | 122,861 in 745.62s |
