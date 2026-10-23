# ollama/

Script-managed Ollama server. User-facing operation and memory rationale live
in [README.md](README.md); shared server conventions live in
[../AGENTS.md](../AGENTS.md).

## File inventory

| File | Role |
| -- | -- |
| `install.sh` | Verified user-local Ollama runtime install |
| `lib.sh` | Runtime paths, binary resolution, pid, API, and GPU helpers |
| `start.sh` | Foreground launcher and environment policy |
| `run.sh` | Detached launcher and API readiness wait |
| `pull.sh` | Model pull through the running server |
| `preflight.sh` | Remote managed-server and idle-GPU guard |
| `status.sh` | API allocation, CPU/GPU split, RAM, VRAM, and process report |
| `bench.py` | Ollama adapter, live artifact identity and effective-slot guards for shared AuditBench v2 |
| `capability.py` | Native Ollama adapter for shared Capability Check v2 |
| `stop.sh` | Recorded-process-group teardown and GPU release check |
| `models/*.conf` | Portable model facts |
| `Makefile` | Guard with no runnable targets |

## Invariants

- Never add systemd operations. The launcher owns one detached process group
  and one pidfile, and refuses to compete with an active Ollama service.
- Run every operation through a root Makefile target.
- Keep runtime binaries, models, pidfiles, logs, and benchmark output outside
  the repository.
- Keep the server on loopback. Ollama has no authentication on this endpoint.
- Remote Ollama is isolated under `tmp/ollama/`: `runtime/`, `model-cache/`,
  and `state/`. The fixed remote environment must name `OLLAMA_BIN` explicitly
  so it cannot fall back to a host installation.
- Keep remote API port 11435 and local tunnel port 11436 distinct from local
  Ollama's 11434 and the vLLM tunnel's 8001.
- Never assign `HOME` or an XDG variable to relocate Ollama. Upstream hardcodes
  `~/.ollama/id_ed25519`; remote startup requires the existing private/public
  key files to be regular and readable, and fails rather than generating them.
  The only exception is a human-authorized first start with
  `OLLAMA_REMOTE_ALLOW_KEY_CREATE=1`; omit it immediately afterward.
- Remote guards are causal, never a typed confirmation: start fails when the
  managed pidfile is live, the port answers, or any NVIDIA compute process is
  active; pull, benchmark, and capability require the pidfile-owned managed
  server; bootstrap refuses while it is running; stop signals only the
  pidfile-owned process group. Do not weaken these on a shared host.
- Remote deploy excludes `runtime/`, `model-cache/`, and `state/`. Stop,
  status, logs, and tunnel must never deploy as a side effect.
- `pull.sh` must require the pidfile-owned server before contacting the API;
  an unmanaged process must never receive a model pull.
- Do not force `num_gpu`. llama.cpp automatic fit decides which layers and
  caches reside on the 12 GiB GPU after accounting for the full context slot.
- An RTX profile runs entirely on the GPU, ahead of context length: a
  model whose weights spill to the CPU gets a smaller artifact (a lower-bit
  or expert-pruned GGUF) or leaves the host.
- Keep every Qwen profile at `OLLAMA_NUM_PARALLEL=1`. Ollama 0.32.14 forced
  both `qwen35` and `qwen35moe` architectures to one request slot, and the
  benchmark's effective-runner check rejected requested 2x and 4x
  profiles; no later release has been tested for more. Do not claim
  multi-slot Qwen support without repeating full-context correctness tests.
- Ollama 0.40.7 runs the `nemotron_h_moe` runner (Nemotron 3.5 Bolt) on
  one slot: a start with `OLLAMA_NUM_PARALLEL=4` served one, and the
  effective-runner check refused the 4x bench.
- Keep the benchmark job count equal to `OLLAMA_NUM_PARALLEL`.
- A model card that requires its returned reasoning in the history declares
  `OLLAMA_PRESERVE_REASONING=1`. `bench.py` and `capability.py` both forward
  it; the capability adapter builds its own `CapabilityConfig`, so the
  harness's `CAPABILITY_PRESERVE_REASONING` alone never reaches it.
- Keep Flash Attention enabled when using quantized KV. q8 is the quality-safe
  default; q4 is an explicit experiment.
- Each conf declares its model's minimum Ollama release as
  `OLLAMA_MIN_VERSION`. Profiles run on the root Makefile's default unless
  their conf declares `OLLAMA_RUNTIME_VERSION`. Update a runtime's version
  and all reviewed per-platform GitHub asset digests
  (`OLLAMA_ARCHIVE_SHA256`, `_LINUX_ARM64`, `_DARWIN`, from the release's
  `sha256sum.txt`) together.
- The remote deploy (`ollama-remote-*` targets) rsyncs the repo's ollama/
  directory over `tmp/ollama/` with `--delete`, preserving only `runtime/`,
  `model-cache/`, and `state/`. Never stage import files or anything else
  inside `tmp/ollama/` -- a staged 87 GiB GGUF download was silently deleted
  by the next deploy. Stage local-import sources in the remote home
  directory instead.
- `qwen3.8-flash-next-gguf-iq4xs` is the A100 Flash-Next profile
  (UD-IQ4_XS, 73 GB VRAM at 2 x 262,144 with q8_0 KV, locked to that
  shape -- llama.cpp has no fungible KV pool, so slots divide the
  context partition statically).
- A remote profile whose conf declares `OLLAMA_RUNTIME_VERSION` (none
  today) needs the same `OLLAMA_VERSION` at the make level on remote
  lifecycle calls: the remote fixed environment
  resolves `OLLAMA_BIN` before the conf is read; a forgotten override fails
  loudly at the version guard.
- 0.40.x keeps a second model index, `manifests-v2/` (one symlink per tag
  to its manifest, stored as a blob), beside `manifests/`, and prefers it.
  0.40.1 rewrote older GGUF tags on first load (a `llamacpp/` runner
  manifest plus new config and params), breaking digest pins in a shared
  store; 0.40.3 kept every pin across its loads. A store 0.40.1 touched can
  hold v2 links to blobs since removed: 0.40.3 then logs "bad manifest" and
  drops the tag from `/api/tags`, so the adapter finds no entry. Move such a
  dangling link aside (it is evidence, not data) and the tag lists again at
  its legacy manifest. Back up `manifests/` and `manifests-v2/` before a new
  0.40.x release touches a store. 0.40 also refuses a relative
  `OLLAMA_MODELS`; start.sh makes it absolute.
- `qwen3.8-flash-next-gguf-iq4xs` needs llama.cpp >= b10760 (qwen4exp),
  hence `OLLAMA_MIN_VERSION=0.33.3`. The artifact is a
  LOCAL `ollama create` import, not a registry pull -- pull.sh refuses
  profiles with `OLLAMA_LOCAL_IMPORT=1` -- and its import recipe (real-file
  staging dir, mandatory `use_mmap false`, orphaned shard-upload blob
  cleanup) lives in the conf comments. Serving
  default is two full 262,144 slots with q8_0 KV; qwen4exp has no one-slot
  architecture guard and two-slot decode batching is real, but cold deep
  prefills serialize across slots.
- The macOS install extracts the flat universal `ollama-darwin.tgz` into
  `lib/ollama/` and moves the CLI to `bin/ollama`, recreating the Linux
  layout. The binary resolves its bundled MLX and llama.cpp runtimes from
  `<exe dir>/../lib/ollama` (upstream `ml/path.go`); installing the bare
  binary silently loses the MLX runtime. Never use a Homebrew build for the
  measured baseline: an M5 report showed it missing NAX kernels.
- Runner dispatch is decided by the artifact: a `model_format: safetensors`
  manifest takes the MLX runner, GGUF takes llama.cpp. There is no env
  switch. MLX profiles are named for the artifact (`-mlx` suffix) and never
  replace the GGUF profiles.
- The MLX runner serializes requests through one slot and ignores
  `OLLAMA_NUM_PARALLEL`, `OLLAMA_KV_CACHE_TYPE`, and
  `OLLAMA_FLASH_ATTENTION`. MLX profiles set
  `OLLAMA_KV_CACHE_TYPE=mlx-native`, which start.sh accepts as documentation
  and does not export. Do not report queued MLX requests as concurrency; the
  benchmark's effective-runner check treats MLX as one slot.
- MLX context maxima are measured per model and digest and never copied
  between models. A Qwen3.8 NVFP4 profile (since dropped) at native 262,144
  exhausted the M5 Max's 128 GB unified memory ~192k tokens into a 246k
  prefill and hard-reset the machine: the MLX runner wires only the model
  and nothing bounds KV growth before the OS dies. Raising any MLX context
  is a supervised experiment with a memory watchdog, never a config
  default.
- On hosts without `nvidia-smi`, teardown proof is the verified-empty
  process group: unified memory is owned by the group, and there is no
  separate VRAM counter. status.sh reports `footprint` phys footprints per
  group member there. macOS has no `setsid`; run.sh falls back to bash job
  control for the detached process group.
- The A100 serves on Ollama only what vLLM cannot there (the profiles are
  in README.md). The Ollama copies of Qwen3.6, Qwen3.8 27B and
  Gemma 4 26B lost to their vLLM profiles, and Qwen3 Coder and GLM-4.7-Flash
  failed the gate on both runtimes; all five were dropped on 2026-10-12.
- New and replacement measurements follow
  [AuditBench v2](https://github.com/tuminoid/llm-audit-bench).
  Publish only canonical results and update [../README.md](../README.md)
  in the same change. Never combine a retired-harness rate with AuditBench
  or project results between hosts.
- The overview's `GPU KV pool` column is `-` for Ollama because Ollama does not
  expose the fungible pool size used by vLLM. Report the measured 1x CPU/GPU
  allocation in its own column instead; never turn context length into a
  claimed pool size.
- Keep effective runner slots, measured streams, and residency explicit.
  AuditBench caps every phase at the effective slots and allocated context.
- Every model config pins the reviewed registry manifest digest plus expected
  format and native context. `bench.py` resolves `/api/tags` and `/api/show`,
  validates those facts, then confirms `/api/ps` loaded the same digest before
  AuditBench starts. A tag update is an artifact update: review the new
  metadata, change the expectation, and rerun rather than silently accepting
  the alias movement. Architecture and quantization expectations are required
  where the runtime exposes stable values; sparse MLX metadata may omit one.
- AuditBench also retains hashes of the exact harness, adapter, and model
  config plus the current launcher `config:` lines, effective runner, slot
  count, KV policy, allocation, and loaded digest. Keep those fields tied to
  the live managed process rather than reconstructing them from documentation.
- llama.cpp can print raw tokenizer bytes that are not valid UTF-8. Python
  consumers of the managed server log must decode with replacement so identity
  and runner checks do not fail before inference.
- Stop by the recorded process group, never by a command-line pattern.
- `start.sh` refuses a binary whose version differs from the effective
  `OLLAMA_VERSION` (the fleet default or the conf's `OLLAMA_RUNTIME_VERSION`),
  on top of the per-model minimum. The managed path encodes the version; the
  guard exists for an explicit `OLLAMA_BIN` naming another runtime.

## Verification

Run the complete lifecycle:

```bash
make lint
make ollama-install
make ollama-start MODEL=saluki-27b
make ollama-status
make ollama-capability MODEL=saluki-27b
make ollama-bench MODEL=saluki-27b
make ollama-stop
```

`OLLAMA_BENCH_JOBS` must match the effective `OLLAMA_NUM_PARALLEL`; the adapter
rejects a mislabeled operating point before AuditBench starts. Canonical
near-context capacity submits canonical stream counts up to that effective
limit at 15/16 of configured context. Gemma concurrency claims require those
requests to complete in every active slot, not only a successful load-only
probe. Qwen and MLX profiles remain one-slot results.

While a shared remote GPU is occupied, validation is static only: use
`make shellcheck`, `make markdownlint`, and `make -n` for the remote recipes.
Do not invoke SSH, rsync, a remote Make target, bootstrap, start, pull, bench,
stop, logs, or tunnel merely to validate wiring.
