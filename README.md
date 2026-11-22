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

Each provider, an access path to one runtime, has a ready opencode config
at `opencode/<provider>/opencode.json`. Start a server here, then run opencode
in your own project with that file layered over your settings; opencode
merges configs:

```bash
make splash-start MODEL=qwen3.8-27b           # in this repository

export OPENCODE_CONFIG=/path/to/llm-local-servers/opencode/splash/opencode.json
opencode models splash                        # the model ids it offers
opencode                                      # in your project
opencode run -m splash/mlx-community/Qwen3.8-27B-4bit "Summarise the auth flow."
```

- `MODEL` names a config in this repository; the opencode model id is its
  served name. Only the model the server was started with answers.
- To give one project a provider permanently, copy the file to that
  project's root as `opencode.json`.
- Entries with reasoning-effort variants take `opencode run --variant
  <effort>`; no variant leaves the model's default.
- The remote providers need their tunnel running (`make vllm-remote-tunnel`,
  `make ollama-remote-tunnel` or `make strata-remote-tunnel`).
- Do not point `OPENCODE_CONFIG_DIR` at these directories: opencode writes
  its plugin files into that directory.

| Provider | Base URL | Config | Reasoning field |
| -- | -- | -- | -- |
| `vllm` | `http://127.0.0.1:8000/v1` | [vllm/opencode.json](opencode/vllm/opencode.json) | `reasoning` |
| `vllm-remote` | `http://127.0.0.1:8001/v1`, `make vllm-remote-tunnel` | [vllm-remote/opencode.json](opencode/vllm-remote/opencode.json) | `reasoning` |
| `vllm-metal` | `http://127.0.0.1:8021/v1` | [vllm-metal/opencode.json](opencode/vllm-metal/opencode.json) | `reasoning` |
| `splash` | `http://127.0.0.1:8022/v1` | [splash/opencode.json](opencode/splash/opencode.json) | `reasoning` |
| `lmstudio` | `http://127.0.0.1:1234/v1` | [lmstudio/opencode.json](opencode/lmstudio/opencode.json) | `reasoning_content` |
| `ollama` | `http://127.0.0.1:11434/v1` | [ollama/opencode.json](opencode/ollama/opencode.json) | not declared |
| `ollama-mlx` | `http://127.0.0.1:11434/v1` | [ollama-mlx/opencode.json](opencode/ollama-mlx/opencode.json) | not declared |
| `ollama-remote` | `http://127.0.0.1:11436/v1`, `make ollama-remote-tunnel` | [ollama-remote/opencode.json](opencode/ollama-remote/opencode.json) | not declared |
| `ds4` | `http://127.0.0.1:8023/v1` | [ds4/opencode.json](opencode/ds4/opencode.json) | `reasoning_content` |
| `kapitsa` | `http://127.0.0.1:8024/v1` | [kapitsa/opencode.json](opencode/kapitsa/opencode.json) | `reasoning_content` |
| `strata` | `http://127.0.0.1:8025/v1` | [strata/opencode.json](opencode/strata/opencode.json) | `reasoning_content` |
| `strata-remote` | `http://127.0.0.1:8026/v1`, `make strata-remote-tunnel` | [strata-remote/opencode.json](opencode/strata-remote/opencode.json) | `reasoning_content` |

### How the files are generated

`make opencode-config` generates them from the model configs, and
`make test` fails when they are stale, so never edit them by hand.

- Every config of a runtime is a model of each of its providers, except
  that Ollama splits by artifact format: safetensors tags run on the MLX
  runner, which the fleet serves on Apple Silicon only, so they are
  `ollama-mlx` models and stay off `ollama` and `ollama-remote`, which list
  the GGUF configs. [CAPABILITIES.md](CAPABILITIES.md) lists which configs
  run on which host.
- The id is `VLLM_SERVED_NAME`, the `OLLAMA_MODEL` tag, the
  `SPLASH_MODEL_REPO` repository, `DS4_SERVED_NAME`,
  `KAPITSA_SERVED_NAME`, `STRATA_SERVED_NAME`, or for LM Studio the config
  name.
  Configs that share a served id become one model, with the smaller
  context.
- The display name is derived from the config name.
- `limit.context` is the config's launch context, and `limit.output` is
  a quarter of it.
- `reasoning` is declared only where the model reasons with no request
  control, since opencode sends no thinking toggle. `tool_call` follows
  the config's tool expectation.
- Ollama entries declare no reasoning, because the capability check
  verifies Ollama reasoning only on its native API.
- `<PREFIX>_REASONING_EFFORTS` in a config, such as `VLLM_REASONING_EFFORTS`,
  becomes `reasoningEffort` variants on an entry that declares reasoning.

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
derived. Capability pass/fail is in [CAPABILITIES.md](CAPABILITIES.md).

The mission workload: a growing tool-loop conversation resent every turn,
report or verdict at depth, 16 tool steps at 262,144 configured context
(fewer at shorter contexts), at the declared sampling. Ranked rows pass
Capability Check v3 compatibility and publish their
optimal operating point: the fastest measured stream count whose sessions
all completed, where one stream qualifies as much as N. `@Nx` names the
measured concurrency; an `@Nx` rate with an incomplete session is shown
for reference only. Rows are ranked by the optimal rate within a host
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

| Rank | Runtime and profile | Tier | Sessions/h 1x | Sessions/h @Nx | Optimal | Report decode 1x |
| --: | -- | -- | --: | --: | -- | --: |
| 1 | vLLM `qwen3.6-35b-a3b-awq` | MoE | 38.49 | 58.67 @8x | 8x | 111.4 |
| 2 | vLLM `gemma4-26b-a4b-awq` | MoE | 37.20 | 45.99 @8x | 8x | 63.6 |
| 3 | Strata `qwen3.8-flash-next-nvfp4` (125B-A6B, NVFP4) | MoE | 27.66 | -- | 1x | 110.2 |
| 4 | vLLM `qwen3.8-27b` (W4A16) | dense | 11.83 | 21.48 @4x | 4x | 49.8 |
| 5 | vLLM `qwen3.8-27b-512k` | dense | 14.49 | 19.55 @4x | 4x | 36.7 |
| 6 | Ollama `nemotron-3.5-bolt-74b-a9b-iq2` (74B-A9B) | hybrid MoE | 15.53 | -- | 1x | 119.6 |
| 7 | vLLM `qwen3.8-27b-dflash2` | dense | 8.40 | 13.04 @2x | 2x | 22.8 |
| 8 | Ollama `flint-40b-a2b-nvfp4` (40B-A2.5B) | MoE | 9.94 | 12.14 @2x, incomplete | 1x | 40.7 |
| 9 | Strata `deepseek-v4.1-flash-coder-iq2xxs` (1,048,576 context) | MoE | 9.77 | -- | 1x | 50.3 |

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

| Rank | Runtime and profile | Tier | Context | Sessions/h 1x | Sessions/h @Nx | Optimal | Report decode 1x |
| --: | -- | -- | --: | --: | --: | -- | --: |
| 1 | Ollama `nemotron-3.5-lightning-30b-mlx` (30B-A3B) | hybrid MoE | 262,144 | 31.07 | -- | 1x | 123.3 |
| 2 | Splash `ornith1.5-35b-a3b` (35B-A3B, text-only) | MoE | 262,144 | 28.01 | 30.72 @2x | 2x | 167.4 |
| 3 | Splash `qwen3.8-flash-next-iq3s` (125B-A6B, GSQ-RCO IQ3_S) | MoE | 262,144 | 27.17 | 28.73 @2x | 2x | 118.3 |
| 4 | Kapitsa `clover-35b-a3b` (block diffusion, 35B-A3B) | MoE | 262,144 | 27.58 | 27.01 @2x | 1x | 84.4 |
| 5 | Splash `qwen3.6-35b-a3b` | MoE | 262,144 | 20.90 | 20.18 @4x, incomplete | 1x | 211.5 |
| 6 | Ollama `muse-glimmer-30b-mlx` (32B, 3:1 sliding-window attention) | dense | 131,072 | 20.12 | -- | 1x | 44.0 |
| 7 | LM Studio `qwen3.6-35b-a3b-splash` | MoE | 262,144 | 18.70 | -- | 1x | 177.0 |
| 8 | Ollama `nemotron-3.5-super-mlx` (120B-A12B) | hybrid MoE | 524,288 | 12.79 | -- | 1x | 55.3 |
| 9 | Ollama `nemotron-3.5-bolt-74b-a9b-q3kxl` (74B-A9B) | hybrid MoE | 262,144 | 9.09 | -- | 1x | 32.2 |
| 10 | Splash `qwen3.8-27b` | dense | 262,144 | 8.57 | 8.49 @4x | 1x | 63.0 |
| 11 | Splash `bonsai2-27b-pq2` (ternary) | dense | 262,144 | 8.10 | 8.48 @2x | 2x | 58.3 |
| 12 | LM Studio `qwen3.8-27b-splash` | dense | 262,144 | 8.12 | -- | 1x | 53.5 |
| 13 | vLLM-Metal `granite4.2-30b-4bit` | hybrid MoE | 131,072 | 2.14 | 3.18 @2x | 2x | 10.5 |
| 14 | Ollama `nanbeige4.3-33b-q4km` | dense | 262,144 | 1.47 | -- | 1x | 6.0 |

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

| Rank | Runtime and profile | Tier | Context | Sessions/h 1x | Sessions/h @Nx | Optimal | Report decode 1x |
| --: | -- | -- | --: | --: | --: | -- | --: |
| 1 | Ollama `qwen3.6-35b-a3b-reap48` (expert-pruned Qwen3.6-35B-A3B, all on GPU) | MoE | 262,144 | 6.74 | -- | 1x | 19.3 |
| 2 | Ollama `saluki-27b` (2-bit Qwen3.8-27B, all on GPU) | dense | 163,840 | 4.56 | -- | 1x | 11.4 |

Unranked: Ollama `lfm2.5-24b-a2b` (7.49/h at 131,072, all on GPU) fails
Capability Check v3 compatibility and its 1x run is incomplete; it is the
RTX's interactive profile.
