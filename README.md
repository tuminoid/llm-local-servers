# llm-local-servers

Measured, Makefile-driven local LLM serving. Nine managed runtimes -- vLLM
(CUDA), Ollama, vLLM-Metal, Splash (Apple Silicon), LM Studio, ds4, Kapitsa,
Strata and FreeToken (CUDA) -- with one portable config per model,
host-adaptive launchers, isolated remote-host operation, and benchmark and
capability results per hardware ([Results by hardware](#results-by-hardware)).
The workload everything is tuned for is deep-context security-audit calls;
[AGENTS.md](AGENTS.md) states the mission and the invariants.

Each hardware keeps the best provider per model: one runtime, chosen by
Capability Check v3 and then the AuditBench session rate. LM Studio is kept
beside it as the entry-level option, since it installs cleanly on every
platform.

Serving performance is measured with AuditBench v3, and engine and model
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
   [kapitsa/README.md](kapitsa/README.md),
   [strata/README.md](strata/README.md), and
   [freetoken/README.md](freetoken/README.md).

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
| `make <runtime>-bench MODEL=<name>` | Run AuditBench v3 |
| `make <runtime>-capability MODEL=<name>` | Run Capability Check v3 |

where `<runtime>` is `vllm`, `ollama`, `vllm-metal`, `splash`, `lmstudio`,
`ds4`, `kapitsa`, `strata` or `freetoken` (plus `ollama-install`, `vllm-metal-install`,
`vllm-metal-pull`, `splash-install`, `splash-pull`, `lmstudio-install`,
`lmstudio-pull`, `ds4-install`, `ds4-pull`, `kapitsa-install`,
`kapitsa-pull`, `strata-install`, `strata-pull`, `freetoken-install`, and
`freetoken-pull` for runtime and model
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

## Results by hardware

Each page ranks the measured profiles by completed audit sessions per hour
(AuditBench v3, at the optimal stream count, gated by Capability Check v3),
lists the interactive profiles, and gives every profile's capability
verdict. Pick the page closest to your machine:

- Apple Silicon Mac: [Apple M5 Max, 128 GB](docs/hardware/apple-m5-max-128gb.md)
- NVIDIA datacenter GPU:
  [NVIDIA A100 SXM4 80GB](docs/hardware/nvidia-a100-sxm4-80gb.md)
- NVIDIA laptop GPU:
  [NVIDIA RTX PRO 3000 Blackwell laptop GPU, 12 GB](docs/hardware/nvidia-rtx-pro-3000-blackwell-laptop-12gb.md)

With less memory than the page's hardware, a profile whose weights and KV
cache do not fit runs slower or not at all; with more, the ranking still
holds and longer contexts may fit. Rates compare only within one page, and a
MoE or hybrid row is not comparable with a dense one.
