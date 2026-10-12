# llm-local-servers

Self-hosted inference servers: managed runtimes, portable per-model operating
points, and the retained measurements for every host in the fleet. Each
runtime directory is one server, driven entirely by Makefile targets from the
repository root.

## Mission

This repository exists for exactly one workload shape: **maximum
throughput on deep-context agentic tool loops** -- automated
vulnerability discovery across a codebase, and deep agentic coding
sessions. A call of that shape is a deep-context request -- tens to
hundreds of thousands of evidence tokens -- with tool calls landing
mid-context and complex reasoning over the whole window. The fleet is
tuned, benchmarked, and judged on completed sessions per hour at real
depths, nothing else.

**Every decision in this tree must serve this mission.** Model
selection, quantization choice, context sizing, cache policy, scheduler
tuning, benchmark design, pin bumps, which trade-offs are acceptable --
all of it is decided by asking one question: does this raise real audit
throughput? A change that cannot answer that question does not belong
here, and a justification that appeals to any other goal is not a
justification. When two options conflict, the one that serves audit
throughput wins, even when the other looks better on a general-purpose
metric.

What this means in practice:

- Sessions/hour on the AuditBench agent session, at one stream and at the
  serving concurrency, is the primary metric. A model or setting that wins
  a short-prompt decode sweep but loses sessions/hour loses, period.
- Deep context is the product, not an edge case. Survivable context
  depth is proven per model and per artifact digest; a config that
  parses 262k but cannot serve repeated deep prefills is broken, not
  "mostly fine".
- Tool calls and reasoning must work mid-context, in streaming requests,
  at depth, and the model must finish audit work at its own sampling
  without running away, skipping its thinking, or ignoring the task --
  that is what capability-v2 gates and why a throughput number can never
  override a capability failure.
- Repeated-prefix reuse matters because audit clients resend the whole
  growing conversation every step. Trading a flat decode percentage for
  a large warm-prefix prefill win is the correct trade for this
  workload (see the qwen3.6 vLLM-Metal APC decision).
- Linear context filling, small-context benchmarks, and synthetic
  decode-only leaderboards are diagnostics at best. Do not tune for
  them, do not select models by them, and do not present them as
  serving results.

## Inventory

| Directory | Runtime | Targets |
| -- | -- | -- |
| `ollama/` | Ollama native and OpenAI-compatible server | Local lifecycle plus isolated `ollama-remote-*` targets |
| `vllm/` | vLLM OpenAI-compatible server | Local lifecycle, benchmark and capability targets, plus `vllm-remote-*` |
| `vllm-metal/` | vLLM-Metal plugin server on Apple Silicon | `vllm-metal-{install,pull,start,stop,status,logs,bench,capability}` |
| `splash/` | Splash native Metal server on Apple Silicon M3+ | `splash-{install,pull,start,stop,status,logs,bench,capability}` |
| `lmstudio/` | LM Studio service with its Splash and MLX engines | `lmstudio-{install,pull,start,stop,status,logs,bench,capability}` |
| `ds4/` | ds4 (DwarfStar) native Metal server for large MoE models; interactive use only, see its AGENTS.md | `ds4-{install,pull,start,stop,status,logs,bench,capability}` |

[README.md](README.md) is the front page and the cross-runtime, host-oriented
executive summary of measured results. The per-runtime `BENCHMARKS.md` files
remain the sources of measurement detail.
[CAPABILITIES.md](CAPABILITIES.md) holds the capability campaign runbook,
host inventory, and the retained cross-host result matrix.
[docs/INTRODUCTION.md](docs/INTRODUCTION.md) is the newcomer-facing primer on
local serving concepts.

## The shared harness

AuditBench v2 (the serving benchmark) and Capability Check v2 (the model gate)
are defined and implemented in the sibling
[llm-audit-bench](https://github.com/tuminoid/llm-audit-bench) repository:
`docs/PROTOCOL.md`, `docs/CAPABILITY.md`, and the two stdlib-only modules
under `src/`. This repository consumes them and never carries copies:

- The Makefile resolves the checkout via `AUDIT_BENCH_DIR` (default
  `../llm-audit-bench`) and fails fast when it is missing. Local bench,
  capability, and test targets import the modules with
  `PYTHONPATH=$(AUDIT_BENCH_DIR)/src`.
- The internal remote-deploy step (a prerequisite of every remote verb that
  executes repo scripts) rsyncs `audit_bench.py` and `capability_check.py`
  from that checkout next to the adapters on remote hosts, where they import
  as adjacent files with no PYTHONPATH.
- Workload logic -- prompt generation, target sizes, sample counts, stream
  counts, validation, metrics, and the JSON schema -- lives only in the
  harness. Runtime adapters here own transport, model loading, capacity
  discovery, and identity evidence, nothing more.
- Every run retains its complete JSON on disk before printing, under
  `${XDG_STATE_HOME:-~/.local/state}/auditbench/` for benchmarks and
  `.../capability-check/` for checks, on whichever host executed it. The
  bench and capability targets print a human summary; the JSON is the
  result. Find it with `uv run audit-bench --list` or
  `uv run capability-check --list` (in the llm-audit-bench checkout)
  and re-read one with `--show FILE`. `AUDIT_BENCH_OUTPUT_DIR` and
  `CAPABILITY_OUTPUT_DIR` relocate retention and are forwarded to remote
  runs. Never transcribe measured numbers from the printed summary.
- Protocol changes happen in llm-audit-bench under its amendment rules. A
  change that would alter a canonical workload invalidates cross-host
  comparability; never fork the workload locally to avoid that
  conversation.

## Scope

This repository holds servers that host models locally: their launchers,
per-model operating points, and the measured results. It does not hold the
benchmark or capability harnesses (llm-audit-bench), and it does not hold
clients, cloud models, or agent definitions. The one client artifact is the
generated opencode provider configs for its own servers, under `opencode/`.

A server belongs here when it owns a long-running process and GPU or CPU
resources. A wrapper that merely calls a hosted API does not.

Personal, host-specific values -- above all the remote GPU host's ssh alias
-- are supplied by the environment (`.envrc`, gitignored; see
`.envrc.example`), never committed in the Makefile or scripts.

Committed content must contain no PII. Identify measured hosts by hardware
labels such as Apple M5 Max or A100-SXM4-80GB. Keep personal hostnames,
login names, SSH aliases, private addresses and personal absolute paths
in untracked local configuration or retained evidence, not repository files.

## Conventions

All servers in this tree follow these. They exist because each one was
learned from a failure, so treat a deviation as a bug unless it is argued
in the server's own AGENTS.md.

### Makefile-driven

Never invoke the scripts directly in documentation or examples. Every
operation gets a `make <server>-<verb>` target, run from the repository
root.

The corollary is that a server directory needs a guard `Makefile` defining no
targets. With no makefile present, `make stop` in one of these directories does
not fail -- it matches GNU Make's built-in `%: %.sh` rule and runs
`cat stop.sh > stop; chmod a+x stop`, leaving an executable, untracked, stale
copy of the script while stopping nothing. The guard sets
`MAKEFLAGS += --no-builtin-rules` and uses `.DEFAULT` to fail with the root
target list instead. Each runtime directory carries its own standalone copy
rather than sharing an include: `vllm/` and `ollama/` are rsynced to remote
hosts, where an include path outside the directory would not exist.

### Config per model, not per invocation

Model settings live in `<server>/models/<name>.conf`, one file per model,
selected by a `make` variable. Every value uses `${VAR:-default}` so the
environment wins over the file without the file needing to know.

Capability Check expectations are model facts too: reasoning present or
absent, tools required or absent, and the documented thinking controls. Keep
them beside the parser and model identity rather than inferring them in the
shared checker. So is the checkpoint's sampling: each config declares
`<PREFIX>_SAMPLING` from its `generation_config.json` at the pinned revision
(else the model card or registry params), and the adapters pass it to
AuditBench and audit fitness.

Host-specific settings (bind address, port, accelerator backend) belong in
the launcher, not the model config. A model config should be portable
between machines; the launcher adapts to the machine.

### State pins and lists once

A runtime version, archive digest, model revision or model list is set in
code -- the root Makefile, a launcher, or a model config -- and prose points
there instead of restating it. A version in prose is measurement
provenance (what a retained result ran on) or dated history, never a claim
about the current pin, which would go stale at the next bump.

### Host-adaptive defaults

A launcher must degrade rather than fail when an optional host capability
is missing. Probe for the capability and pick a working fallback.

Concretely: the vLLM launcher derives its attention backend, KV cache dtype,
memory policy and even the location of its own executable from the GPU's
compute capability and VRAM, so one copy of the scripts serves a 12 GB laptop
card and an 80 GB A100 with no per-host branch. Hardcoding the fast path makes
the scripts fail at engine init on any machine that cannot take it.

The corollary is that a model config must stay portable -- model facts only,
no utilization or backend values. A host setting in a model config is a bug,
because it will be wrong on the next machine.

The second corollary is a verification duty: a change to host adaptation
cannot be validated on one machine, since a single host only exercises one
branch of the derivation. Run the lifecycle on a second GPU generation, and
check the resolved profile the launcher logs rather than just that the server
started.

### Runtime state outside the repo

Pidfiles, logs, and caches go to `${XDG_STATE_HOME:-~/.local/state}/<server>/`.
Nothing generated may land in git, and no `.gitignore` entry should be
needed to achieve that.

State is also scoped to a run, not accumulated: start truncates the log, stop
removes it and the pidfile, so a stopped server leaves an empty state dir. Keep
the log only where it is still evidence -- a teardown that failed to release the
resource, or a stop that found nothing running. This is cheaper than rotation
and covers the case rotation misses, a single run that logs without bound.

### Lifecycle by pidfile

The launcher records its pid; stop reads it. Do not stop servers by
matching command-line patterns. `pkill -f <pattern>` matches any process
whose command line contains the pattern, including the shell that invokes
the `pkill`, so it kills the caller. This is not hypothetical -- it
happened three times while building the vLLM scripts.

Detach with `setsid`, not `nohup` alone. `nohup` only ignores SIGHUP; a
Ctrl-C in the invoking shell sends SIGINT to the whole foreground process
group and takes a backgrounded server down with it.

### Verify teardown, do not assume it

Stop must confirm the resource was actually released -- for GPU servers,
that VRAM dropped -- and exit non-zero if not. An orphaned worker holding
memory breaks the next start with a confusing error far from the cause.

### Bind to loopback

Default to `127.0.0.1`. Inference servers commonly default to `0.0.0.0`
with no authentication, which exposes an unauthenticated endpoint to the
whole network. Exposing one is a deliberate act: it needs an explicit
override and an authentication flag.

### Isolate shared remote hosts

A remote runtime must not reuse the host's normal binary, cache, state,
pidfile, or API port. Give deployed scripts one owned tree and exclude its
runtime data from later `rsync --delete` operations. Explicitly name the
managed executable so a missing bootstrap fails instead of falling back to
`PATH`.

Guard mutations causally, on the live state they would damage, never with a
ceremonial confirmation variable. Start must fail while the managed pidfile is
live, the port is claimed, or another GPU compute process is active;
operations through the server must require the pidfile-owned managed process;
replacing the installed runtime must require the server stopped; stop signals
only the pidfile-owned process group. Read-only inspection and
teardown do not deploy: silently syncing scripts before status or stop mutates
the host at the moment the operator is trying to inspect or recover it.

Local tunnel ports are runtime-specific and cannot reuse a local server port
or another runtime's tunnel. Bind them to loopback and fail if forwarding
cannot be established.

### Use one benchmark protocol

All new and replacement measurements use
[AuditBench v2](https://github.com/tuminoid/llm-audit-bench). Published
AuditBench v1 rows are history: never compare them with v2 rows, and replace
them as each host is re-measured.
Runtime adapters may implement transport,
model loading, and residency checks, but prompt generation, target sizes,
sample count, stream counts, validation, metrics, and JSON schema belong only
in the shared harness.

A publishable result has `canonical: true`. Exploratory overrides are for
finding the memory and concurrency operating point; rerun the canonical
protocol after freezing it. Never combine a retired-harness rate with an AuditBench
result or derive a missing scalar from another workload.

Canonicality describes the workload only. The JSON `publishable` field also
requires a clean repository commit, hashes of the exact harness, adapter and
model config, checked model identity, and the live resolved runtime profile.
Do not remove that distinction: exploratory or dirty runs remain useful
evidence without becoming publication artifacts.

The overview tables in `README.md` are derived from `vllm/BENCHMARKS.md`,
`ollama/BENCHMARKS.md`, `vllm-metal/BENCHMARKS.md`, and
`splash/BENCHMARKS.md`. Update the matching
host overview whenever a benchmark source changes a model, context, memory
allocation, KV pool, active slots, or canonical metric.

Use hardware host labels and exact measured tokenizer counts. Personal
hostnames belong only in retained evidence outside the repository.
Keep these separate:

- configured per-request context;
- raw vLLM KV pool or Ollama allocation;
- active scheduler or runner slots;
- measured streams; and
- preemption and CPU offload.

Ollama has no fungible pool metric, so never derive one from context length.
AuditBench never submits a stream count that exceeds active admission or the
KV capacity of that workload.

### Gate agent API capabilities separately

Run Capability Check v2 before promoting a model for agent workloads. It must
prove the configured reasoning semantics, structured tool call, tool-result
continuation, and direct JSON output, and pass audit fitness at the
declared sampling. Keep these pass/fail fixtures out of AuditBench: serving speed
cannot compensate for malformed agent responses or unfinished work.

Any run intended to update the serving inventory must follow
[CAPABILITIES.md](CAPABILITIES.md) and update its host row in the same
change. Do not improvise a campaign by running every
config on a host, and do not promote older manual evidence to an automated
pass.

Capability expectations live in model configs and name documented controls.
Never infer them from a parser name or registry capability list.

### Keep the best provider per model

A host serves each model from one runtime: the best measured one, judged by
Capability Check v2 first and the AuditBench session rate second. When a
second runtime on the same host serves the same model, drop the losing
profile with its benchmark rows, capability rows and generated provider
entries; launcher rationale that rests on its measurements stays, marked as
from a dropped profile. LM Studio is the exception: its profiles stay beside
the best provider as the entry-level option, because it installs cleanly on
every platform.

### Client configs are generated

`opencode/*/opencode.json` is generated from the model configs by
`make opencode-config`, and `make test` fails when it is stale. Never edit it
by hand: change the config, or `opencode/generate.py` for a provider's base
URL or a runtime rule. A provider is an access path and carries no host
names; its port is the launcher's default, which the test checks.

### Diagnose upstream bugs, do not report them

When a runtime, plugin, or model defect is root-caused, record the full
diagnosis in the affected model config or benchmark document with a retest
condition, and stop there. Do not file upstream issues, draft them, or
offer to file them: upstream reporting happens only when the operator
explicitly asks for it.

## Adding a server

1. Create `<name>/` at the repository root with `start.sh`, `run.sh`,
   `stop.sh`, `status.sh`, `models/`, and a standalone guard `Makefile` as
   described above.
2. Put shared paths and helpers in `lib.sh`. It is sourced, never
   executed, and defines the state dir, pidfile, and log paths.
3. Add `make <name>-{start,stop,status,logs,bench}` targets plus a
   `<NAME>_MODEL_CONF` variable, and list them in `make help`.
4. Write `<name>/README.md` for usage and host-tuning rationale, and
   `<name>/AGENTS.md` for the file inventory, invariants, and the
   gotchas that a future change could reintroduce.
5. Update the inventory table above and the overview in README.md.
6. `make lint`, then exercise the full cycle: start, status, bench, a
   real request, stop. Confirm the resource is released at the end.

## Verification expectations

A change to a server is not done until the full lifecycle has been run,
not just linted. Scripts in this tree orchestrate long-running processes
that hold hardware; static checks cannot show that start actually serves
or that stop actually frees the GPU.

Record measured numbers when a change is meant to affect performance.
Claims about throughput need a before and after from the same benchmark
on the same host, with the warmup discarded. Update the matching
`README.md` host table when the benchmark summary changes.
