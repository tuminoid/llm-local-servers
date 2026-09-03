# lmstudio/

Script-managed LM Studio server. User-facing usage and rationale live in
[README.md](README.md); shared server conventions live in
[../AGENTS.md](../AGENTS.md). Serving measurements follow
[AuditBench v1](https://github.com/tuminoid/llm-audit-bench).

## File inventory

| File | Role |
| -- | -- |
| `lib.sh` | Paths, lms binary resolution, API base, server-status/GPU/memory helpers |
| `install.sh` | Verify the lms CLI, service reachability, version floor, runtimes |
| `pull.sh` | Download the pinned artifact via `lms get` with the --mlx/--gguf filter |
| `start.sh` | Synchronous launcher: ensure server up, load model, host policy |
| `run.sh` | Invoke start.sh and confirm the OpenAI endpoint answers |
| `status.sh` | Server, loaded identity, context, memory/GPU, live API probe |
| `bench.py` | LM Studio adapter for shared AuditBench v1, identity and resolved-profile provenance |
| `capability.py` | OpenAI-compatible adapter for shared Capability Check v1 |
| `stop.sh` | `lms unload --all` + `lms server stop` and release verification |
| `models/*.conf` | Portable model facts: repo/quant spec, model key, format, context, capability expectations |
| `Makefile` | Guard with no runnable targets |

## Invariants

- Run every operation through a root Makefile target.
- The model weights, baseline reading, and log all live outside the
  repository under `${XDG_STATE_HOME:-~/.local/state}/lmstudio/`.
- `lmstudio_bin` accepts only the `LMSTUDIO_BIN` override or a PATH `lms`.
  There is no managed install location: `lms` ships inside the desktop app.
- Keep the server on loopback port 1234 (LM Studio's default). It is
  distinct from Ollama 11434, CUDA vLLM 8000/8001, and vLLM-Metal 8021.
  The endpoint has no authentication by default, so never bind non-loopback
  and never pass `--cors`.
- Model configs are portable model facts only: `lms get` spec, model key,
  served name, format, context, expected quant/architecture, and capability
  expectations. GPU offload and bind/port are host policy in `start.sh`.
- The MLX config is Darwin/arm64 only. `pull.sh` and `start.sh` refuse it
  on any other host rather than silently loading a GGUF fallback, the same
  platform gate `vllm-metal/` enforces.
- One conf per artifact, format encoded in the config. Never switch format
  on an env var: the artifact decides the runner (llama.cpp for GGUF, MLX
  on Apple Silicon), exactly as ollama/ and vllm-metal/ split the two.
- Load must run on this host. LM Studio's LM Link routes model resolution
  across networked devices, so when a remote peer is the preferred device
  `lms load` runs the model on that peer's GPU. `start.sh` reads
  `lms link status --json` and refuses a remote-routed load by default,
  the same "serve locally, remote is a deliberate act" stance as the
  loopback-bind invariant. `LMSTUDIO_ALLOW_REMOTE_DEVICE=1` opts in.

## Accepted deviations (and why)

These are the three places LM Studio cannot meet a tree convention the way
the pinned-runtime servers do. Each was a deliberate choice, not an
oversight; a future change must not "fix" them by pretending LM Studio is
a pinned CLI runtime.

- No pinned, checksum-verified install. Ollama and vLLM-Metal fetch an
  exact release and verify a published SHA256. LM Studio ships `lms` and
  its llama.cpp/MLX runtimes inside an auto-updating desktop application;
  there is no per-platform release tarball with a digest to fetch, and the
  app must have run once before `lms` works at all. `install.sh` therefore
  verifies `lms` is present, the service is reachable (`lms ls`), and, when
  the CLI reports a semver, that it meets `LMSTUDIO_MIN_VERSION`. Some
  `lms` builds print only a commit hash instead of a semver; an unparseable
  version is not fatal, because the real capability gate is the `/api/v1`
  REST probe performed at start and bench time.
- Identity by model key/path/format/quant, not a served content digest.
  Ollama pins a registry manifest SHA256 and detects drift. LM Studio
  identifies a model by its Hugging Face repo path plus quant and exposes
  no served content digest, so `bench.py` and `capability.py` verify the
  loaded artifact's format, quantization, and architecture against the
  config via `lms ps`. Note LM Studio reports the llama.cpp architecture id
  (for example `qwen35`), not the Hugging Face class name, and reports
  quantization as a `{"name","bits"}` object; the configs and adapters
  match those actual strings, case-insensitively.
- No pidfile or process-group teardown. The other runtimes fork and own
  the server process and stop it by pidfile-scoped signal. LM Studio's
  model is owned by the long-running desktop service (`lms daemon`), which
  is already detached, so `start.sh` runs a synchronous sequence
  (`lms server start`, then `lms load`, which blocks until resident) with
  no process to hold, and `stop.sh` tears down through `lms unload --all`
  and `lms server stop`. Teardown is still verified, not assumed: VRAM must
  return to the pre-start baseline on hosts with `nvidia-smi`, and an empty
  `lms ps` after unload is the release proof on Apple Silicon, where there
  is no separate VRAM counter. `stop.sh` does not stop the desktop app or
  its daemon.

## Guarding a shared service

Because the service is shared with whatever the operator loads in the GUI,
`start.sh` refuses to start when the service already has any model loaded,
rather than silently loading a second one, and refuses when the running
server is on a different port than configured. Read-only `status.sh` and
teardown `stop.sh` never load a model or mutate the service beyond the
requested unload/stop.

## Gotchas a future change could reintroduce

- `lmstudio_version` must tolerate no match: its `grep` finds nothing on
  commit-hash builds, and under `set -e` an ungarded pipeline failure kills
  the caller silently. Keep the `|| true`.
- Do not embed escaped double quotes inside the `python3 -c '...'`
  single-quoted heredocs: the shell passes `\"` through literally and
  Python's tokenizer rejects it. Compute strings into a variable instead.
- `lms load --gpu max` offloads every layer; on a small-VRAM host that
  fails at CUDA-buffer allocation. That is a host-fit issue, not a bug; the
  operator lowers `LMSTUDIO_GPU`. The scripts must let LM Studio's guardrail
  refuse the load loudly rather than pre-computing a fit.
- The bench adapter must not synthesise a KV pool size from context length.
  LM Studio exposes no fungible pool metric, so, like the Ollama adapter,
  capacity is one active slot at the configured per-request context.
- `/v1/models` lists every downloaded model, not just the loaded one, so
  the harness's `openai_model_card` (which asserts a lone entry) cannot be
  used. `bench.py` carries `_served_model_card`, which selects the served
  id out of the list; the harness stays untouched. LM Studio's card also
  omits `max_model_len`, so the loaded context is verified against
  `lms ps`, not the card.
- LM Link can route a load to a networked peer. When testing locally,
  confirm the preferred device is this host (`lms link status`); the
  guard in `start.sh` refuses a remote-routed load, but a change that
  bypasses it would silently benchmark someone else's GPU. Restore any
  `set-preferred-device` change you make for a local test.
- AuditBench requires at least 131,072 configured context tokens
  (`build_plan` rejects less). A small-VRAM host cannot hold that for a
  27B, and only barely for a 9B with heavy CPU offload, so canonical rows
  come from a host that fits the native context, not from trimming the
  window below the harness floor.
