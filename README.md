# llm-local-servers

Measured, Makefile-driven local LLM serving. Three managed runtimes --
vLLM (CUDA), Ollama, and vLLM-Metal (Apple Silicon) -- with one portable
config per model, host-adaptive launchers, isolated remote-host
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
   [vllm-metal/README.md](vllm-metal/README.md), and
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

where `<runtime>` is `vllm`, `ollama`, `vllm-metal`, or `lmstudio` (plus
`ollama-install`, `vllm-metal-install`, `vllm-metal-pull`,
`lmstudio-install`, and `lmstudio-pull` for runtime and model
installation). `MODEL` names a config file in that runtime's `models/`
directory, never a served model ID or registry tag; there is deliberately
no default model. LM Studio is local-only and adds no `-remote-*` family
(its desktop-app dependency does not fit the isolated-shared-host
pattern).

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

Decision-oriented summary of the measured operating points. The tables
copy canonical AuditBench v1 medians from
[vllm/BENCHMARKS.md](vllm/BENCHMARKS.md),
[ollama/BENCHMARKS.md](ollama/BENCHMARKS.md), and
[vllm-metal/BENCHMARKS.md](vllm-metal/BENCHMARKS.md), which hold the
evidence, memory analysis, ranges, per-model caveats, and history;
missing values are never derived. Capability pass/fail records are in
[CAPABILITIES.md](CAPABILITIES.md). Prefill and
decode are aggregate tok/s, audit columns are calls/hour, a `@Nx`
suffix names the measured concurrency, and `GPU KV / allocation` is
the raw vLLM pool or Ollama's measured CPU/GPU model allocation
(Ollama exposes no fungible pool).

The LM Studio runtime carries no rows yet: its llama.cpp and MLX engines
are the same ones `ollama/` and `vllm-metal/` already measure, so a row is
added only once a canonical AuditBench run proves it earns a place rather
than duplicating those numbers. See
[lmstudio/BENCHMARKS.md](lmstudio/BENCHMARKS.md) for status.

### Audit conversations per hour, fleet-wide

The conversation profile is the mission workload: a growing tool-loop
conversation resent every turn, findings verdict at depth (see the
AuditBench protocol). One row per host/runtime pair and per model --
each model's best measured compliant profile at its serving cache mode
-- so each row also certifies the model held the tool-loop protocol end
to end. Dominated variants (a model's slower hosts, runtimes, digests,
or cache modes) live in the runtime BENCHMARKS. MoE/hybrid and dense
models rank separately: active-parameter count dominates prefill
economics, so the tiers are not throughput-comparable. Contexts differ
per operating point (131k-shape rows are marked), so compare within a
tier.

MoE and hybrid (sparse-active):

| Rank | Host / runtime / best profile | Cache | Conv/hour |
| --: | -- | -- | --: |
| 1 | A100 vLLM `qwen3.6-35b-a3b-awq` | align APC | 85.9 |
| 2 | M5 Ollama `qwen3.6 coding NVFP4` (131k shape) | MLX trie | 50.9 |
| 3 | A100 vLLM `qwen3-coder-30b` | APC | 45.2 |
| 4 | A100 vLLM `gemma4-26b-a4b-awq` | APC | 43.8 |
| 5 | M5 Ollama `nemotron-3.5-lightning` | MLX trie | 34.4 |
| 6 | A100 Ollama `qwen3.6-35b-a3b` GGUF | slot cache | 32.0 |
| 7 | M5 vLLM-Metal `qwen3.6-35b-a3b-4bit` | align APC | 12.5 |
| 8 | M5 Ollama `qwen3.8-flash-next-gguf` (125B-A6B) | slot cache | 7.2 |

Dense:

| Rank | Host / runtime / best profile | Cache | Conv/hour |
| --: | -- | -- | --: |
| 1 | A100 vLLM `qwen3.8-27b-dflash2` | align APC + DFlash 2 | 23.4 |
| 2 | A100 Ollama `qwen3.8-27b-native` | slot cache | 14.5 |
| 3 | RTX Ollama `qwen3.5:9b` | slot cache | 9.8 |
| 4 | M5 vLLM-Metal `gemma4-31b-4bit` | APC | 2.4 |

The qwen3.5-4b profiles are excluded despite leading the RTX rates:
their fixture compliance is variant-split and cache-mode sensitive, and
the RTX host has no Capability Check v1 record yet (see
[CAPABILITIES.md](CAPABILITIES.md)); their measured rates stay in the
RTX table below and the runtime BENCHMARKS.

The A100 vLLM `qwen3-coder-30b` row keeps its measured rate but is not
promotable for agent workloads: under automatic tool choice it returns
two tool calls for a one-call fixture, streaming and non-streaming
alike, which is a capability failure no throughput number overrides.
Its Ollama pairing passes the same checks; the evidence is in
[CAPABILITIES.md](CAPABILITIES.md) and the diagnosis in the model conf.

Cache and speculation policy, not model speed, dominates the spread
behind each row: on the A100 alone the same qwen3.8 weights span 4.1
(vLLM cache-off, retired) through 14.5 (Ollama slot cache) and 20.2
(vLLM align APC) to 23.4 conv/hour (align APC plus the DFlash 2
drafter). Profiles that deviated from the fixture (GLM 4.7
Flash on both A100 runtimes, among others) are excluded here, not slow;
the per-case stories are in the runtime BENCHMARKS, and the replay
profile below still measures server performance for them.

### Audit replay: server performance without model cooperation

The replay profiles resend recorded audit conversations, so they price
the server without model cooperation; full trials and gates are in each
runtime's BENCHMARKS.md. Conclusions so far: on the A100, align APC is
worth 6.1x end to end on qwen3.8 (its conf now pins APC on after the
same-day correctness gate) and roughly 2x over Ollama's implicit slot
cache on qwen3.6 (18.3 vs 9.92 replays/hour, same fixture); DFlash 2
speculation on qwen3.8 is depth-dependent -- 2.4x shallow decode and
+16% conversations, but neutral at verdict depth, with the crossover
around 64-100k resident tokens; and GLM 4.7
Flash -- conversation-non-compliant everywhere -- serves the shape well
on vLLM. On the RTX,
replay prices APC at 1.32-1.73x end to end, and verdict decode at depth
is the ceiling. On the M5, the audit gap against the A100 is
single-stream decode bandwidth at depth, not caching (cached fractions
identical); the concurrent-replay profile puts the knee at two agents
on both hybrids, with shared-prefix caching real but minor at audit
depth, while the A100 is still scaling at four concurrent agents on
qwen3.6 (2.28x aggregate).

### RTX PRO 3000 Blackwell laptop GPU

Local host: sm_120, 12,227 MiB VRAM, 62 GiB RAM.

| Runtime and profile | Context | Slots | GPU KV / allocation | 32k prefill | Peak decode | Audit 32k | Audit half | Audit deep | Near-context proof |
| -- | --: | --: | -- | --: | --: | --: | --: | --: | -- |
| vLLM `gemma4-e2b-awq` | 131,072 | 2 | 450,444 KV | 4,835.1 | 303.54 @2x | 289.55 @2x | 113.31 | 56.89 @2x | 2 x 122,896 in 124.89s |
| vLLM `qwen3.5-4b-awq` | 131,072 | 2 | 274,432 KV | 4,686.9 | 176.12 @2x | 250.94 @2x | 113.76 | 85.82 @2x | 2 x 122,861 in 87.77s |
| Ollama `gemma4:e2b` | 131,072 | 4 | 0.00 / 2.66 GiB | 3,582.5 | 247.40 @4x | 184.88 @4x | 99.42 | 67.33 @1x | 4 x 122,903 in 217.03s |
| Ollama `qwen3.5:9b` | 262,144 | 1 | 0.00 / 10.21 GiB | 1,654.8 | 37.83 | 70.34 | 22.10 | 12.26 | 245,752 in 311.57s |

The practical RTX choices are vLLM Gemma for peak decode and cold-32k audit
throughput, vLLM Qwen for stronger late-audit throughput, Ollama Gemma E2B for
four-slot capacity, and Ollama Qwen3.5 9B for a fully resident 262k model.
The remaining measured profiles (Ollama qwen3.5:4b and gemma4:12b, and the
CPU-assisted qwen3.6 and qwen3.8 capability profiles) are in
[vllm/BENCHMARKS.md](vllm/BENCHMARKS.md) and
[ollama/BENCHMARKS.md](ollama/BENCHMARKS.md).

### A100-SXM4-80GB

Remote host: sm_80, 81,920 MiB VRAM. vLLM rows: 0.28.0, Transformers
5.15.1 (re-canonicalized within ~2% of the earlier 0.27.1 rates).
Ollama rows: isolated Ollama 0.32.14, Flash Attention, q8 KV.

| Runtime and profile | Context | Slots | GPU KV / allocation | 32k prefill | Peak decode | Audit 32k | Audit half | Audit deep | Near-context proof |
| -- | --: | --: | -- | --: | --: | --: | --: | --: | -- |
| vLLM `qwen3.6-35b-a3b-awq` | 262,144 | 8 | 2,714,989 KV | 15,558.4 | 867.22 @8x | 992.75 @8x | 148.07 | 84.59 @4x | 8 x 245,752 in 359.58s |
| Ollama `qwen3.6:35b-a3b` | 262,144 | 1 | 0.00 / 25.34 GiB | 4,165.7 | 84.58 | 176.52 | 64.82 | 42.81 | 245,752 in 85.26s |
| vLLM `gemma4-26b-a4b-awq` | 262,144 | 8 | 1,867,456 KV | 7,603.9 | 1,072.38 @8x | 595.22 @8x | 58.53 | 26.22 @4x | 4 x 245,774 in 625.92s |
| Ollama `gemma4:26b` | 262,144 | 8 | 0.00 / 25.32 GiB | 3,246.7 | 231.48 @8x | 222.32 @8x | 53.51 | 27.68 @4x | 8 x 245,777 in 1,030.85s |
| vLLM `qwen3-coder-30b` | 262,144 | 8 | 513,152 KV | 8,551.3 | 1,019.74 @8x | 515.11 @8x | 61.55 | 27.20 @1x | 2 x 245,762 in 289.67s |
| vLLM `qwen3.8-27b-dflash2` | 262,144 | 8 | 498,225 KV | 2,721.2 | 592.04 @8x | 227.99 @8x | 34.77 | 22.84 @1x | 2 x 245,748 in 322.29s |

The A100 audit workhorse is vLLM Qwen3.6: it leads every prompt-heavy phase,
reaches 992.75 cold-32k calls/hour, and proves eight simultaneous near-full
contexts. vLLM Gemma and Qwen Coder lead pure aggregate decode, but their
32k audit rates are only 60% and 52% of Qwen3.6; Gemma is also the best
Ollama audit profile. The qwen3.8 DFlash 2 row is the dense model with its
pinned speculative drafter: 2.4x plain decode and +27% cold-32k calls at
one stream, fading with depth (its half/deep cells sit at or below the
plain profile's; the crossover analysis is in
[vllm/BENCHMARKS.md](vllm/BENCHMARKS.md)). The remaining measured
profiles (both GLM 4.7 Flash stacks, plain qwen3.8 on both runtimes, and
Ollama qwen3-coder) are in [vllm/BENCHMARKS.md](vllm/BENCHMARKS.md) and
[ollama/BENCHMARKS.md](ollama/BENCHMARKS.md).

### Apple M5 Max (128 GB unified memory)

Local host: MacBook Pro `Mac17,6`, 40 GPU cores, macOS 26.6.2. Ollama
MLX rows: managed official Ollama 0.32.14, MLX runner on
`mlx_metal_v4`, safetensors NVFP4 artifacts; the runner serializes
requests to one slot. The flash-next row runs the llama.cpp runner on
the split 0.33.3 managed runtime with two real slots and q8 KV.
vLLM-Metal rows: pinned plugin venv, paged KV, NAX prefill active.
Calls/hour includes prefill; each profile passed its
near-context proof at 1x and its maximum fitting concurrency
(evidence in [vllm-metal/BENCHMARKS.md](vllm-metal/BENCHMARKS.md) and
[ollama/BENCHMARKS.md](ollama/BENCHMARKS.md), alongside the bring-up
history, memory ceilings, and hard-reset analysis).

| Runtime | Model or profile | Context | KV pool | Prefill 32k/64k/128k tok/s | Decode 1/2/4 tok/s | audit_32k /h | audit_half /h | audit_deep /h |
| -- | -- | --: | --: | --: | --: | --: | --: | --: |
| vLLM-Metal | `qwen3.6-35b-a3b-4bit` APC (serving), util 0.71, seqs 5 | 262,144 | 1,324,084 | 2,824 / 1,574 / 1,063 | 98.4 / 168.6 / 258.1 | 112.6 @4x | 18.8 | 9.9 @1x |
| vLLM-Metal | `qwen3.8-27b-4bit` APC (serving), util 0.91, seqs 5 | 262,144 | 611,156 | 570 / 458 / 318 | 28.6 / 53.4 / 83.3 | 39.4 @4x | 6.7 | 3.3 @1x |
| vLLM-Metal | `qwen3.8-27b-uncensored-4bit` 512k YaRN, APC | 524,288 | 617,494 | 519 / 434 / 313 | 28.6 / 53.6 / 85.1 | 39.6 @4x | 2.3 (262k) | 0.97 (459k) |
| Ollama | `qwen3.8-flash-next-gguf` (125B-A6B, llama.cpp, 0.33.3) | 262,144 | 2 slots | 632 / 518 / 406 | 38.7 / 57.2 / - | 47.4 @2x | 9.7 | 5.1 @1x |
| Ollama | `nemotron-3.5-lightning:30b-a3b-mlx` | 262,144 | one slot | 4,040 / 3,072 / 2,628 | 141.7 / - / - | 212.8 @1x | 58.3 | 31.1 @1x |
| Ollama | `qwen3.6:35b-a3b-coding-nvfp4` (MLX) | 131,072 | one slot | 3,242 / 2,305 / - | 126.7 / - / - | 180.4 @1x | 88.5 (65k) | 48.7 (114.7k) |

The MoE holds a ~3x calls/hour advantage over qwen3.8 at every audit
depth; the dense qwen3.8 batches better and is the quality profile, not
the throughput profile. Nemotron 3.5 Lightning is the host's
audit-cadence and depth leader (its Mamba/attention hybrid holds
prefill nearly flat with depth), but its ceiling is the one-slot MLX
runner -- the vLLM-Metal path that would give it concurrency is blocked
on a plugin bug (see the model conf) -- and it has no secaudit quality
record yet. The NVFP4 row runs the 131,072 operating point, so its half
and deep targets are 65k and 114.7k (parenthesized to keep the columns
honest); at the shared 32k depth that one MLX stream still beats the
vLLM-Metal MoE serving profile 1.6x. The uncensored 512k row's targets
run deeper for the same reason (262k half, 459k deep, parenthesized),
and its 491,514-token capacity proof is the fleet's first canonical
completion beyond a checkpoint's native window. NVFP4 safetensors do not load
under mlx-lm at the current plugin pin, so the Ollama registry remains
the only NVFP4 path on this host. The remaining measured profiles
(the cache-off control rows, gemma4-31b, and the rate-identical base
NVFP4 digest) are in
[vllm-metal/BENCHMARKS.md](vllm-metal/BENCHMARKS.md) and
[ollama/BENCHMARKS.md](ollama/BENCHMARKS.md).
