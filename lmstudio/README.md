# LM Studio server

Script-managed [LM Studio](https://lmstudio.ai) server: the desktop
application's `lms` CLI and its bundled llama.cpp (GGUF) and MLX
(Apple Silicon) inference runtimes, serving models through LM Studio's
OpenAI-compatible API and native `/api/v1` REST API.

## Why this runtime

LM Studio is the convenience and comparison peer in this fleet. Its
inference engines are the same llama.cpp and MLX that `ollama/` and
`vllm-metal/` already wrap, so it is not expected to beat their measured
audit throughput on shared hardware; it earns its place as a second,
independently packaged path to the same engines, with first-class control
over the MLX-versus-GGUF choice and a single CLI for lifecycle and model
identity. Any promotion into the serving inventory must be justified by a
measured AuditBench result, not by convenience alone.

Format is a first-class choice here. LM Studio keeps MLX and GGUF variants
as distinct model keys and the `--mlx`/`--gguf` filter on `lms get`
selects which is fetched, so each artifact gets its own config
(`qwen3.6-27b-gguf`, `qwen3.6-27b-mlx`) exactly as the Ollama and
vLLM-Metal servers split the two. GGUF runs on every host; the MLX config
is Apple-Silicon-only and is refused loudly elsewhere, the same platform
gate `vllm-metal/` lives under.

## Usage

```bash
make lmstudio-install                       # verify lms CLI, service, runtimes
make lmstudio-pull   MODEL=qwen3.6-27b-gguf # download the pinned artifact
make lmstudio-start  MODEL=qwen3.6-27b-gguf # start the server and load it
make lmstudio-status
make lmstudio-bench  MODEL=qwen3.6-27b-gguf
make lmstudio-stop
```

On Apple Silicon, swap in the MLX config:

```bash
make lmstudio-pull   MODEL=qwen3.6-27b-mlx
make lmstudio-start  MODEL=qwen3.6-27b-mlx
```

The benchmark follows the shared
[AuditBench v1](https://github.com/tuminoid/llm-audit-bench) protocol,
driving the OpenAI-compatible endpoint. Capability Check v1 gates the
agent API surface (reasoning, tools, structured output) separately.

The benchmark also sends the model-documented decode-compliance controls:
`LMSTUDIO_BENCH_REASONING_EFFORT` and `LMSTUDIO_BENCH_SYSTEM_PROMPT` from
the model config, environment wins, and the `AUDIT_BENCH_*` harness names
work too. Both are passed to the request and chat adapters, so the model
receives what the run's settings record. The Qwen configs default
`reasoning_effort` to `none`: these models reason by default, and a budget
burned in `reasoning_content` leaves the token-accounting probe nothing
visible to confirm. Override per run with the environment, or set the
config default to empty to send nothing.

The current LM Studio server decodes one token short of every length-
capped request (the characterized, documented off-by-one), so
`lmstudio-bench` defaults `AUDIT_BENCH_TOLERATE_OFF_BY_ONE` on. The run
probes the backend first and applies the -1 gate only on the exact
confirmed signature, and an applied run self-marks `canonical: false` /
`publishable: false` with the probe evidence; once a fixed server build
reports full counts, the probe stops confirming and runs return to
canonical with no config change. Set
`AUDIT_BENCH_TOLERATE_OFF_BY_ONE=0` to force strict validation.

## Host adaptation

The launcher passes `--gpu` offload to LM Studio and lets its own
guardrails plan the load: an unfittable context or offload refuses to
load rather than taking the host down, the loud-refusal property this
tree wants. `--gpu` defaults to `max` (offload all layers); override with
`LMSTUDIO_GPU` (`0`-`1`, `off`, or `max`) on hosts that cannot hold the
whole model on the accelerator. Per-request context is `LMSTUDIO_CONTEXT_LENGTH`
in the config; override it down for a small-VRAM host.

## Local device guard (LM Link)

LM Studio's LM Link lets one device use models loaded on another across the
network, and a networked peer can be set as the preferred device for model
resolution. When that happens, an unqualified `lms load` runs the model on
the peer's GPU, not this host, which silently defeats a local benchmark.
`start.sh` therefore reads `lms link status` and refuses a remote-routed
load by default, matching the tree's serve-locally, remote-is-deliberate
stance. Point the preferred device back at this machine
(`lms link set-preferred-device <this-device-id>`, or `lms link disable`),
or set `LMSTUDIO_ALLOW_REMOTE_DEVICE=1` to load on the remote device on
purpose.

## Accepted deviations

LM Studio is GUI-first, so three of the tree's conventions are met
differently. All three are load-bearing enough to state here and are
detailed in [AGENTS.md](AGENTS.md):

- No pinned, checksum-verified install. LM Studio ships `lms` and its
  runtimes inside an auto-updating desktop app with no per-platform
  release tarball to digest, so `install.sh` verifies presence,
  reachability, and a version floor rather than fetching a pinned
  artifact. The desktop app itself is installed out of band.
- Identity by model key, path, format, and quant, not a served content
  digest. LM Studio exposes no SHA256 the way Ollama's registry does, so
  `bench.py` verifies the loaded artifact against those fields via
  `lms ps`.
- No pidfile or process-group teardown. The model is owned by the
  long-running LM Studio service, so `start.sh` loads synchronously and
  `stop.sh` tears down through `lms unload --all` and `lms server stop`,
  verifying VRAM returned to the pre-start baseline (or an empty
  `lms ps` on Apple Silicon).

## Scope

Local only. LM Studio's desktop-app dependency does not fit the
isolated-shared-host pattern the `ollama-remote-*` and `vllm-remote-*`
targets rely on, so there is deliberately no `lmstudio-remote-*` family.
