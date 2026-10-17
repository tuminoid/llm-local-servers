# llm-local-servers

Measured, Makefile-driven local LLM serving. Six managed runtimes --
vLLM (CUDA), Ollama, vLLM-Metal, Splash (Apple Silicon), LM Studio and
ds4 -- with one portable config per model, host-adaptive launchers, isolated remote-host
operation, and the retained benchmark and capability results for every
host in the fleet. The workload everything is tuned for is deep-context
security-audit calls; [AGENTS.md](AGENTS.md) states the mission and the
invariants.

Each host keeps the best provider per model: one runtime, chosen by
Capability Check v2 and then the AuditBench session rate. LM Studio is kept
beside it as the entry-level option, since it installs cleanly on every
platform.

Serving performance is measured with AuditBench (v1 rows until each host
is re-measured at v2), and API compatibility and audit fitness are gated
with Capability Check v2 (v1 rows until each model is re-checked). Both
live in the sibling [llm-audit-bench](https://github.com/tuminoid/llm-audit-bench)
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
   [splash/README.md](splash/README.md),
   [lmstudio/README.md](lmstudio/README.md), and
   [ds4/README.md](ds4/README.md).

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
| `make <runtime>-bench MODEL=<name>` | Run AuditBench v2 |
| `make <runtime>-capability MODEL=<name>` | Run Capability Check v2 |

where `<runtime>` is `vllm`, `ollama`, `vllm-metal`, `splash`, `lmstudio`,
or `ds4` (plus `ollama-install`, `vllm-metal-install`, `vllm-metal-pull`,
`splash-install`, `splash-pull`, `lmstudio-install`, `lmstudio-pull`,
`ds4-install`, and `ds4-pull` for runtime and model installation).
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
- The remote providers need their tunnel running (`make vllm-remote-tunnel`
  or `make ollama-remote-tunnel`).
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
| `ollama-remote` | `http://127.0.0.1:11436/v1`, `make ollama-remote-tunnel` | [ollama-remote/opencode.json](opencode/ollama-remote/opencode.json) | not declared |
| `ds4` | `http://127.0.0.1:8023/v1` | [ds4/opencode.json](opencode/ds4/opencode.json) | `reasoning_content` |

### How the files are generated

`make opencode-config` generates them from the model configs, and
`make test` fails when they are stale, so never edit them by hand.

- Every config of a runtime is a model of each of its providers.
  [CAPABILITIES.md](CAPABILITIES.md) lists which configs run on which
  host.
- The id is `VLLM_SERVED_NAME`, the `OLLAMA_MODEL` tag, the
  `SPLASH_MODEL_REPO` repository, `DS4_SERVED_NAME`, or for LM Studio the
  config name.
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
[vllm-metal/BENCHMARKS.md](vllm-metal/BENCHMARKS.md), and
[splash/BENCHMARKS.md](splash/BENCHMARKS.md), which hold the
evidence, ranges, caveats, replay results, and history; nothing here is
derived. Capability pass/fail is in [CAPABILITIES.md](CAPABILITIES.md).
Prefill and decode are aggregate tok/s, audit columns are calls/hour,
`@Nx` names the measured concurrency, and `GPU KV / allocation` is the
raw vLLM pool or Ollama's measured allocation.

ds4 is not in these tables. Its models (Qwen3.8 Flash Next, DeepSeek V4
and V4.1 Flash, GLM 5.3 Flash) are too large for any fleet host to run
audit campaigns on, so it serves them for interactive use on the M5 Max;
its capability and speed tables are in [ds4/BENCHMARKS.md](ds4/BENCHMARKS.md).

### Audit throughput per host

The mission workload: a growing tool-loop conversation resent every
turn, report or verdict at depth, with 262,144 configured context and 16
tool steps. One row per runtime and model, ranked within a host only; a
MoE or hybrid row and a dense row are not comparable.

A100-SXM4-80GB, AuditBench v2 `session` profile (sessions per hour at
the declared sampling; 16 tool steps from 32k evidence, report at about
165k; 1 stream and the largest of 2/4/8 the pool admits). Ranked rows pass
Capability Check v2 and are publishable:

| Rank | Runtime and profile | Tier | Sessions/h 1x | Sessions/h @Nx | Report decode 1x |
| --: | -- | -- | --: | --: | --: |
| 1 | vLLM `qwen3.6-35b-a3b-awq` | MoE | 38.49 | 58.67 @8x | 111.4 |
| 2 | vLLM `gemma4-26b-a4b-awq` | MoE | 37.20 | 45.99 @8x | 63.6 |
| 3 | Ollama `ornith1.5-35b-a3b` GGUF | MoE | 27.77 | -- | 58.3 |
| 4 | vLLM `qwen3.8-27b-512k` | dense | 14.49 | 19.55 @4x | 36.7 |
| 5 | vLLM `qwen3.8-27b` (W4A16) | dense | 11.83 | 21.48 @4x | 49.8 |
| 6 | vLLM `qwen3.8-27b-dflash2` | dense | 8.40 | 13.04 @2x | 22.8 |
| 7 | Ollama `qwen3.8-flash-next-gguf-iq4xs` (125B-A6B) | MoE | 7.98 | 8.68 @2x | 25.8 |

Unranked: vLLM `mimo-v2.6-9b-awq` (58.97 / 93.99 @8x) is unpublishable
(incomplete sessions) and fails Capability Check v2. DFlash 2 loses to
plain qwen3.8 at sampling; see [vllm/BENCHMARKS.md](vllm/BENCHMARKS.md).

Apple M5 Max, AuditBench v2 `session` profile (same method as the A100;
16 tool steps at 262,144 configured context, 9 at 131,072). Ranked rows
pass Capability Check v2 and are publishable:

| Rank | Runtime and profile | Tier | Context | Sessions/h 1x | Sessions/h @Nx | Report decode 1x |
| --: | -- | -- | --: | --: | --: | --: |
| 1 | Ollama `nemotron-3.5-super-mlx` (120B-A12B) | hybrid MoE | 524,288 | 9.62 | -- | 41.0 |
| 2 | LM Studio `qwen3.8-27b-splash` | dense | 262,144 | 8.12 | -- | 53.5 |
| 3 | Splash `qwen3.8-27b` | dense | 262,144 | 6.73 | 7.47 @4x | 50.5 |
| 4 | vLLM-Metal `granite4.2-30b-4bit` | hybrid MoE | 131,072 | 2.14 | 3.18 @2x | 10.5 |
| 5 | vLLM-Metal `gemma4-31b-4bit` | dense | 262,144 | 1.80 | 1.89 @2x | 2.8 |

Unranked: Splash `qwen3.6-35b-a3b` (17.95/h) and vLLM-Metal
`ornith1.5-35b-a3b-4bit` (9.15 / 10.52 @4x) pass the gate but their runs
are unpublishable (incomplete sessions). The vLLM-Metal MiMo profile, LM
Studio `qwen3.6-35b-a3b-splash` and both MLX-engine profiles, and the
Ollama Glimmer and Lightning MLX profiles fail Capability Check v2; the
Ollama ones on `json_schema`, the Ollama MLX engine's schema gap, and
Lightning also on audit fitness. Their rates (Lightning 21.12/h at 262k)
cannot promote them. Details are in each runtime's BENCHMARKS.md.

RTX PRO 3000, Ollama 0.40.3, AuditBench v2 `session` profile (16 tool
steps at 262,144 configured context, 13 at 163,840):

| Rank | Runtime and profile | Tier | Context | Sessions/h 1x | Sessions/h @Nx | Report decode 1x |
| --: | -- | -- | --: | --: | --: | --: |
| 1 | Ollama `qwen3.6-35b-a3b-reap48` (expert-pruned Qwen3.6-35B-A3B, all on GPU) | MoE | 262,144 | 7.37 | -- | 22.6 |
| 2 | Ollama `saluki-27b` (2-bit Qwen3.8-27B, all on GPU) | dense | 163,840 | 3.26 | -- | 7.8 |

Unranked: Ollama `lfm2.5-24b-a2b` (8.21/h at 131,072, all on GPU) fails
Capability Check v2 audit fitness and is the RTX's interactive profile. See
[ollama/BENCHMARKS.md](ollama/BENCHMARKS.md).

### A100-SXM4-80GB

Remote host: sm_80, 81,920 MiB VRAM; vLLM 0.31.0 with Transformers 5.15.1,
isolated Ollama 0.40.3. The AuditBench v2 table with
context, slots, KV pool, completion, the pp512/tg128 reference and the
retained JSON names is in
[vllm/BENCHMARKS.md](vllm/BENCHMARKS.md) and
[ollama/BENCHMARKS.md](ollama/BENCHMARKS.md); its sessions/hour are in the
overview above.

### Apple M5 Max (128 GB unified memory)

Local host: MacBook Pro `Mac17,6`, 40 GPU cores, macOS 27.0. vLLM-Metal
0.31.0, Splash 1.3.1, LM Studio 0.4.25+1, Ollama 0.32.14 (MLX) and 0.40.5
(Super VL). The
AuditBench v2 tables with context, slots, KV pool,
completion, the pp512/tg128 reference and the retained JSON names are in
[vllm-metal/BENCHMARKS.md](vllm-metal/BENCHMARKS.md),
[splash/BENCHMARKS.md](splash/BENCHMARKS.md),
[lmstudio/BENCHMARKS.md](lmstudio/BENCHMARKS.md) and
[ollama/BENCHMARKS.md](ollama/BENCHMARKS.md); sessions/hour are in the
overview above.

### RTX PRO 3000 Blackwell laptop GPU

Local host: sm_120, 12,227 MiB VRAM, 62 GiB RAM; Ollama 0.40.3. Its
profiles, `qwen3.6-35b-a3b-reap48`, `saluki-27b` and the interactive
`lfm2.5-24b-a2b`, are in the overview above and in
[ollama/BENCHMARKS.md](ollama/BENCHMARKS.md).

### ds4 on the Apple M5 Max (interactive use)

ds4 serves large MoE models for interactive agentic sessions, one slot,
never ranked for audits. Speed is from the 262,144 runs, one stream, in
tok/s. At 524,288 a 50-step session to about 445k tokens took Qwen 14 min
(report 57.0 tok/s) and V4 Flash 2.2 h, its checkpoints evicted at depth.
Details are in [ds4/BENCHMARKS.md](ds4/BENCHMARKS.md).

| Model | Context | Audit fitness | Tool calls | Turn decode, mid session | Report decode, ~160k deep | Session prefill | Interactive use |
| -- | --: | -- | -- | --: | --: | --: | -- |
| `qwen3.8-flash-next-q4` | 524,288 (YaRN) | pass, 12/12 | pass | 69.3 | 60.9 | 1,277 | yes, the pick |
| `deepseek-v4-flash-q2` | 524,288 | 11/12 at 262,144, 10/12 at 524,288 | pass | 33.4 | 27.2 | 420 | yes, slower |
| `glm5.3-flash-q2` | 262,144 | pass, 11/12 | fail: string-typed arguments | 54.2 | 26.9 | 364 | no |
| `deepseek-v4.1-flash-q2` | 262,144 | fail, 7/12 | pass | 21.8 | 13.4 | 544 | no: slow, SSD streaming |
