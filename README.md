# llm-local-servers

Measured, Makefile-driven local LLM serving. Eight managed runtimes --
vLLM (CUDA), Ollama, vLLM-Metal, Splash (Apple Silicon), LM Studio, ds4,
Kapitsa and Strata (CUDA) -- with one portable config per model, host-adaptive
launchers, isolated remote-host operation, and the retained benchmark and
capability results for every host in the fleet. The workload everything
is tuned for is deep-context security-audit calls; [AGENTS.md](AGENTS.md)
states the mission and the invariants.

Each host keeps the best provider per model: one runtime, chosen by
Capability Check v3 and then the AuditBench session rate. LM Studio is kept
beside it as the entry-level option, since it installs cleanly on every
platform.

Serving performance is measured with AuditBench v2, and engine and model
compatibility (API semantics and clean audit-shaped work) is gated with
Capability Check v3. Both live in the sibling [llm-audit-bench](https://github.com/tuminoid/llm-audit-bench)
repository (`docs/PROTOCOL.md` and `docs/CAPABILITY.md` are the
canonical protocol documents); this repository holds the runtime
adapters, model configs, and results.

New to local serving? [docs/INTRODUCTION.md](docs/INTRODUCTION.md) explains
the concepts these documents assume.

## Setup

1. For bench, capability and development targets, clone
   [llm-audit-bench](https://github.com/tuminoid/llm-audit-bench) beside
   this repository, or point `AUDIT_BENCH_DIR` at an existing checkout.
   The harness is standard-library Python; there is nothing to install.
   Serving does not need it.
2. Copy `.envrc.example` to `.envrc`, fill in your own values (the ssh
   alias of your remote GPU host), and `direnv allow` -- or export the same
   variables from your shell. Committed files carry no host-specific values.
3. Install the runtime you intend to serve with. Host tools are yours
   to provide: `uv`, `python3`, `curl` and `tar` everywhere, plus what a
   runtime names; every target checks the tools it uses and names any
   missing. Prerequisites and host-tuning rationale are per runtime in
   [vllm/README.md](vllm/README.md),
   [ollama/README.md](ollama/README.md),
   [vllm-metal/README.md](vllm-metal/README.md),
   [splash/README.md](splash/README.md),
   [lmstudio/README.md](lmstudio/README.md),
   [ds4/README.md](ds4/README.md),
   [kapitsa/README.md](kapitsa/README.md), and
   [strata/README.md](strata/README.md).

Development needs `shellcheck`, `markdownlint-cli2`, and Python 3.10 or
newer for `make lint` and `make test`. CI installs the linters at the
versions pinned in `uv.lock` and `package-lock.json`.

## Running

Everything runs from the repository root through make; `make help`
prints the full list. The lifecycle verbs are uniform across runtimes:

| Verb | Does |
| -- | -- |
| `make <runtime>-start MODEL=<name>` | Start detached, wait until serving |
| `make <runtime>-stop` | Stop by pidfile, verify the GPU or process group was released |
| `make <runtime>-status` | Process, memory split, context allocation, KV sizing |
| `make <runtime>-logs` | Follow the server log |
| `make <runtime>-bench MODEL=<name>` | Run AuditBench v2 |
| `make <runtime>-capability MODEL=<name>` | Run Capability Check v3 |

where `<runtime>` is `vllm`, `ollama`, `vllm-metal`, `splash`, `lmstudio`,
`ds4`, `kapitsa` or `strata` (plus `ollama-install`, `vllm-metal-install`,
`vllm-metal-pull`, `splash-install`, `splash-pull`, `lmstudio-install`,
`lmstudio-pull`, `ds4-install`, `ds4-pull`, `kapitsa-install`,
`kapitsa-pull`, `strata-install`, and `strata-pull` for runtime and model
installation).
`MODEL` names a config file in that runtime's `models/` directory, never a
served model ID or registry tag; there is deliberately no default model.
`make status` shows whether each local runtime is running, and with which model.

Every bench and capability run retains its JSON under
`~/.local/state/auditbench/` or `~/.local/state/capability-check/` on the
host that ran it. In the llm-audit-bench checkout, `uv run audit-bench
--list` and `uv run capability-check --list` index them, and `--show FILE`
re-prints one.

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

## Using the servers from opencode

Each provider has a generated opencode config; usage, the provider
table and how the files are generated are in
[opencode/README.md](opencode/README.md).

## Measured overview

Every host is measured with AuditBench v2. Canonical medians copied from
[vllm/BENCHMARKS.md](vllm/BENCHMARKS.md),
[ollama/BENCHMARKS.md](ollama/BENCHMARKS.md),
[vllm-metal/BENCHMARKS.md](vllm-metal/BENCHMARKS.md),
[splash/BENCHMARKS.md](splash/BENCHMARKS.md),
[lmstudio/BENCHMARKS.md](lmstudio/BENCHMARKS.md),
[ds4/BENCHMARKS.md](ds4/BENCHMARKS.md),
[kapitsa/BENCHMARKS.md](kapitsa/BENCHMARKS.md) and
[strata/BENCHMARKS.md](strata/BENCHMARKS.md), which hold the
evidence, ranges, caveats, replay results, and history; nothing here is
derived. OWASP vuln score is Capability Check v3's audit aptitude:
true-positive minus false-positive rate on 28 OWASP BenchmarkPython cases
(+1 perfect, 0 chance) with its 95% interval, copied with the compatibility
verdicts and findings from [CAPABILITIES.md](CAPABILITIES.md). Intervals
span about +-0.3, so rows stay ranked by rate.

The mission workload: a growing tool-loop conversation resent every turn,
report or verdict at depth, 16 tool steps at 262,144 configured context
(fewer at shorter contexts), at the declared sampling. Ranked rows pass
Capability Check v3 compatibility. Best sessions/h is their optimal
operating point: the fastest measured stream count whose sessions all
completed, where one stream qualifies as much as N; `@Nx` names that
concurrency. Rows are ranked by the optimal rate within a host
only, and a MoE or hybrid row and a dense row are not comparable.

### A100-SXM4-80GB

Remote host: sm_80, 81,920 MiB VRAM; vLLM 0.31.0 with Transformers 5.15.1,
isolated Ollama 0.40.16 (its rows), Strata 0.2.13 built for sm_80 (its rows).
Sessions per hour by stream count: the vLLM rows ran 1 stream and the largest
of 2/4/8 the pool admits, the Ollama rows the 2.5.0 stream ladder, the Strata
rows their one slot; context, slots, KV pool, completion, the pp512/tg128
reference and the retained JSON names are in
[vllm/BENCHMARKS.md](vllm/BENCHMARKS.md),
[ollama/BENCHMARKS.md](ollama/BENCHMARKS.md) and
[strata/BENCHMARKS.md](strata/BENCHMARKS.md).

| Rank | Model | Runtime | Engine | Tier | Context | OWASP vuln score [95% CI] | Best sessions/h | Report decode 1x |
| --: | -- | -- | -- | -- | --: | -- | --: | --: |
| 1 | `qwen3.6-35b-a3b-awq` | vLLM | vLLM, CUDA | MoE | 262,144 | +0.50 [+0.15, +0.73] | 58.67 @8x | 111.4 |
| 2 | `gemma4-26b-a4b-awq` | vLLM | vLLM, CUDA | MoE | 262,144 | +0.71 [+0.36, +0.89] | 45.99 @8x | 63.6 |
| 3 | `qwen3.8-flash-next-nvfp4` | Strata | Strata | MoE | 262,144 | +0.86 [+0.52, +0.98] | 27.66 @1x | 110.2 |
| 4 | `qwen3.8-27b` | vLLM | vLLM, CUDA | dense | 262,144 | +0.71 [+0.35, +0.90] | 21.48 @4x | 49.8 |
| 5 | `qwen3.8-27b-512k` | vLLM | vLLM, CUDA | dense | 524,288 | +0.64 [+0.28, +0.85] | 19.55 @4x | 36.7 |
| 6 | `nemotron-3.5-bolt-74b-a9b-iq2` | Ollama | llama.cpp | hybrid MoE | 262,144 | +0.43 [+0.05, +0.70] | 15.53 @1x | 119.6 |
| 7 | `qwen3.8-27b-dflash2` | vLLM | vLLM, CUDA | dense | 262,144 | +0.64 [+0.28, +0.85] | 13.04 @2x | 22.8 |
| 8 | `flint-40b-a2b-nvfp4` | Ollama | llama.cpp | MoE | 262,144 | +0.29 [-0.08, +0.58] | 9.94 @1x | 40.7 |
| 9 | `deepseek-v4.1-flash-coder-iq2xxs` | Strata | Strata DeepSeek | MoE | 1,048,576 | +0.86 [+0.52, +0.98] | 9.77 @1x | 50.3 |

Unranked: vLLM `mimo-v2.6-9b-awq` (58.97 / 93.99 @8x) and
`nanbeige4.3-33b-w4a16` (7.19/h) and Ollama `ornith1.5-35b-a3b` (32.21/h)
fail Capability Check v3 compatibility. Strata `deepseek-v4.1-flash-q2`
passes but has no serving rate: part of its experts run on the CPU.
DFlash 2 loses to plain qwen3.8 at the declared sampling (8.40 / 13.04 @2x); see
[vllm/BENCHMARKS.md](vllm/BENCHMARKS.md).

### Apple M5 Max (128 GB unified memory)

Local host: MacBook Pro `Mac17,6`, 40 GPU cores, macOS 27.0. vLLM-Metal
0.31.0, Splash 1.5.0, LM Studio 0.4.25+1, Ollama 0.40.16, ds4, Kapitsa
0.2.36. Context, slots, KV pool,
completion, the pp512/tg128 reference and the retained JSON names are in
[vllm-metal/BENCHMARKS.md](vllm-metal/BENCHMARKS.md),
[splash/BENCHMARKS.md](splash/BENCHMARKS.md),
[lmstudio/BENCHMARKS.md](lmstudio/BENCHMARKS.md),
[ollama/BENCHMARKS.md](ollama/BENCHMARKS.md),
[ds4/BENCHMARKS.md](ds4/BENCHMARKS.md) and
[kapitsa/BENCHMARKS.md](kapitsa/BENCHMARKS.md).

#### Audit throughput

| Rank | Model | Runtime | Engine | Tier | Context | OWASP vuln score [95% CI] | Best sessions/h | Report decode 1x |
| --: | -- | -- | -- | -- | --: | -- | --: | --: |
| 1 | `nemotron-3.5-lightning-30b-mlx` | Ollama | MLX | hybrid MoE | 262,144 | +0.36 [+0.00, +0.62] | 31.07 @1x | 123.3 |
| 2 | `ornith1.5-35b-a3b` | Splash | Splash | MoE | 262,144 | +0.57 [+0.21, +0.79] | 30.72 @2x | 167.4 |
| 3 | `qwen3.8-flash-next-iq3s` | Splash | Splash | MoE | 262,144 | +0.79 [+0.44, +0.94] | 28.73 @2x | 118.3 |
| 4 | `clover-35b-a3b` | Kapitsa | Kapitsa, Metal | MoE | 262,144 | +0.36 [+0.00, +0.62] | 27.58 @1x | 84.4 |
| 5 | `qwen3.6-35b-a3b` | Splash | Splash | MoE | 262,144 | +0.43 [+0.08, +0.67] | 20.90 @1x | 211.5 |
| 6 | `muse-glimmer-30b-mlx` | Ollama | MLX | dense | 131,072 | +0.64 [+0.28, +0.84] | 20.12 @1x | 44.0 |
| 7 | `qwen3.6-35b-a3b-splash` | LM Studio | Splash | MoE | 262,144 | +0.36 [+0.02, +0.60] | 18.70 @1x | 177.0 |
| 8 | `nemotron-3.5-super-mlx` | Ollama | MLX | hybrid MoE | 524,288 | +0.57 [+0.21, +0.79] | 12.79 @1x | 55.3 |
| 9 | `nemotron-3.5-bolt-74b-a9b-q3kxl` | Ollama | llama.cpp | hybrid MoE | 262,144 | +0.36 [-0.01, +0.64] | 9.09 @1x | 32.2 |
| 10 | `qwen3.8-27b` | Splash | Splash | dense | 262,144 | +0.57 [+0.21, +0.79] | 8.57 @1x | 63.0 |
| 11 | `bonsai2-27b-pq2` | Splash | Splash | dense | 262,144 | +0.64 [+0.30, +0.83] | 8.48 @2x | 58.3 |
| 12 | `qwen3.8-27b-splash` | LM Studio | Splash | dense | 262,144 | +0.71 [+0.35, +0.90] | 8.12 @1x | 53.5 |
| 13 | `granite4.2-30b-4bit` | vLLM-Metal | vLLM, MLX | hybrid MoE | 131,072 | +0.57 [+0.21, +0.79] | 3.18 @2x | 10.5 |
| 14 | `nanbeige4.3-33b-q4km` | Ollama | llama.cpp | dense | 262,144 | +0.43 [+0.06, +0.69] | 1.47 @1x | 6.0 |

Unranked: Splash `flint-gguf` (19.49 @2x) and `ornith1.5-122b` (11.87),
Ollama `mimo-v2.6-flash-q2ks` (5.29) and LM Studio `qwen3.8-27b-mlx` fail
Capability Check v3 compatibility; their rates cannot promote them. LM
Studio `qwen3.6-35b-a3b-mlx` passes but its runs are noncanonical by design
(off-by-one token allowance). Details are in each runtime's BENCHMARKS.md.

#### Interactive use

These profiles serve interactive agentic sessions and are not ranked for
audits.

Ollama `gemma4-26b-mlx` (Gemma 4 26B-A4B, MLX NVFP4, 262,144) passes
Capability Check v3; a generic model, it serves interactive use (25.63
sessions/h in an unpublishable session run, one report recalling no
findings). Details are in [ollama/BENCHMARKS.md](ollama/BENCHMARKS.md).

ds4 serves large MoE models, one slot. `qwen3.8-flash-next-q4` passes
Capability Check v3 and runs 10.00 sessions/h; Splash serves the same model for
audits 2.9x faster, so ds4 keeps it for interactive use. Speed is from the
262,144 runs, one stream, in tok/s. At 524,288 a 50-step session to about 445k
tokens took Qwen 14 min (report 57.0 tok/s) and V4 Flash 2.2 h, its
checkpoints evicted at depth. ds4 has no `response_format`, so schema
enforcement, which never gates, is broken. Details are in
[ds4/BENCHMARKS.md](ds4/BENCHMARKS.md).

| Model | Context | Capability v3 | Tool calls | Turn decode, mid session | Report decode, ~160k deep | Session prefill | Interactive use |
| -- | --: | -- | -- | --: | --: | --: | -- |
| `qwen3.8-flash-next-q4` | 524,288 (YaRN) | pass, +0.86 | pass | 69.3 | 60.9 | 1,277 | yes, the pick |
| `deepseek-v4-flash-q2` | 524,288 | pass, +0.71 | pass | 33.4 | 27.2 | 420 | yes, slower |
| `glm5.3-flash-q2` | 262,144 | fail | fail: string-typed arguments | 54.2 | 26.9 | 364 | no |
| `deepseek-v4.1-flash-q2` | 262,144 | pass, +0.71 | pass | 14.7 | 14.2 | 629 | yes, slow: SSD streaming |

### RTX PRO 3000 Blackwell laptop GPU

Local host: sm_120, 12,227 MiB VRAM, 62 GiB RAM; Ollama 0.40.6 (the 0.40.16
default is not measured there). Details are
in [ollama/BENCHMARKS.md](ollama/BENCHMARKS.md).

| Rank | Model | Runtime | Engine | Tier | Context | OWASP vuln score [95% CI] | Best sessions/h | Report decode 1x |
| --: | -- | -- | -- | -- | --: | -- | --: | --: |
| 1 | `qwen3.6-35b-a3b-reap48` | Ollama | llama.cpp | MoE | 262,144 | +0.07 [-0.14, +0.26] | 6.74 @1x | 19.3 |
| 2 | `saluki-27b` | Ollama | llama.cpp | dense | 163,840 | +0.29 [-0.09, +0.59] | 4.56 @1x | 11.4 |

Unranked: Ollama `lfm2.5-24b-a2b` (7.49/h at 131,072, all on GPU) fails
Capability Check v3 compatibility and its 1x run is incomplete; it is the
RTX's interactive profile.
