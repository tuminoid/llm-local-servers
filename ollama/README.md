# Ollama server

Script-managed Ollama server for local models. It does not manage a systemd
service.

Serving benchmarks follow
[AuditBench v2](https://github.com/tuminoid/llm-audit-bench).
Ollama operating points still require
`OLLAMA_BENCH_JOBS` to match the effective runner slot count.

## macOS MLX baseline

The same scripts run the local Apple Silicon baseline (M5 Max, 128 GB
unified memory, macOS 26). `make ollama-install` selects the official
universal `ollama-darwin.tgz` for the pinned version, verifies its own
reviewed digest (`OLLAMA_ARCHIVE_SHA256_DARWIN`), and recreates the Linux
`bin/` plus `lib/ollama/` layout under the managed runtime root -- the binary
searches `<exe dir>/../lib/ollama` for its bundled MLX and llama.cpp
runtimes, so a bare binary would silently lose them. Do not substitute a
Homebrew build: an M5 report showed the Homebrew-linked MLX build missing
NAX kernels that the official archive uses.

Runner selection is an artifact fact, not a host or env setting: a registry
tag whose manifest is `model_format: safetensors` (for example
`nemotron-3.5-lightning:30b-a3b-mlx`) is dispatched to the MLX runner, while
GGUF tags keep using llama.cpp. The MLX profiles are named for the artifact
with an `-mlx` suffix. On the M5, Qwen3.6 and Qwen3.8 are served by Splash,
not Ollama.

The fleet default runtime is 0.40.3. Profiles that need another release
declare it per profile with `OLLAMA_RUNTIME_VERSION`: the M5's MLX profiles
and `qwen3-coder-30b` stay on 0.32.14 (the MLX runner's memory runaway and
coder's duplicated tool calls on 0.40.x); remote lifecycle calls for such a
profile also pass its `OLLAMA_VERSION` at the make level.

`qwen3.8-flash-next-gguf-iq4xs` (Qwen3.8-Flash-Next 125B-A6B, locally
imported UD-IQ4_XS GGUF sized for the A100's 80 GB, locked to 2 x 262,144
with q8_0 KV) needs a qwen4exp-capable llama.cpp, Ollama 0.33.3 or newer.
On the M5 the model is served by ds4. The model is imported
with `ollama create`, never pulled (`make ollama-pull` refuses it); the
import recipe and the mandatory `use_mmap false` are documented in the
conf, and the measured operating point in [BENCHMARKS.md](BENCHMARKS.md).
Install a per-profile runtime with the reviewed digests recorded beside it in
the root Makefile.

The 0.32.14 MLX runner serializes requests through a single slot and keeps
its KV cache at model precision. `OLLAMA_NUM_PARALLEL`,
`OLLAMA_KV_CACHE_TYPE`, and `OLLAMA_FLASH_ATTENTION` are ignored on that
path, which is why the MLX profiles carry `OLLAMA_KV_CACHE_TYPE=mlx-native`:
the launcher accepts it as documentation and forwards no cache-type
environment. Concurrent requests queue; they must not be reported as
parallel execution, and the benchmark's effective-runner check enforces one
job.

Status on this host reports the runner (`mlx` with engine version and
device, or `llama.cpp` with slots), the `/api/ps` allocation and context,
process RSS, and each group member's `footprint` phys footprint, which is
the process-owned unified-memory total including Metal allocations. With
`OLLAMA_DEBUG=1` the loaded `mlx_metal_v4` variant line is the Metal 4
evidence on M5. Teardown proof on unified memory is the verified-empty
process group; there is no separate VRAM counter to poll, so `stop.sh`
reports the group release instead of a GPU baseline.

macOS ships no `setsid`; the detached launcher falls back to bash job
control, which gives the server its own process group -- the same handle the
pidfile teardown signals.

## Remote A100 deployment

The isolated deployment was exercised on the shared A100 test host. The
server was stopped after benchmarking, GPU use returned
to 0 MiB, and no tunnel was opened. Do not run any remote Ollama write or GPU
target while vLLM or another compute workload is active.

### Isolation contract

The remote path follows the vLLM deployment pattern but does not share any
writable runtime path or port:

| Resource | Remote Ollama value |
| -- | -- |
| Deployed scripts | `tmp/ollama/` |
| Pinned binary | `tmp/ollama/runtime/v<OLLAMA_VERSION>/bin/ollama` (default 0.40.3) |
| Model cache | `tmp/ollama/model-cache/` |
| Pidfile, log, GPU baseline | `tmp/ollama/state/` |
| Remote API | `127.0.0.1:11435` |
| Local tunnel endpoint | `127.0.0.1:11436` |

The remote commands set `OLLAMA_BIN` explicitly, so a missing isolated runtime
fails instead of falling back to an Ollama binary on `PATH`. Deployment uses
`rsync --delete` only for deployed files and excludes `runtime/`,
`model-cache/`, and `state/`. Bootstrap does not write `/usr/local`, configure
systemd, or use the local managed runtime path under `~/.local/share`.

Ollama has one upstream path that cannot be relocated:
`~/.ollama/id_ed25519`. Remote startup therefore requires an existing regular,
readable private/public keypair and refuses to start if either file is absent
or a symlink. This prevents automatic key generation from writing into the
host's Ollama installation. The wrapper never assigns `HOME` or an XDG
variable.

If the account has no keypair, a human may explicitly authorize Ollama's
normal first-start generation once:

```bash
make ollama-remote-start MODEL=<config> \
  HOST=<ssh-host> OLLAMA_REMOTE_ALLOW_KEY_CREATE=1
```

Omit `OLLAMA_REMOTE_ALLOW_KEY_CREATE` after that first start; its default is
zero and the existing-key guard is restored. The first A100 startup used this
explicit authorization; all later starts used the existing-key guard.

The remote guards are causal, keyed on the live state each operation would
damage. `preflight.sh idle` rejects a start when the isolated pidfile is
live, anything answers on the isolated endpoint, any NVIDIA compute process
is active, the GPU cannot be queried, or the keypair is missing; `start.sh`
separately rejects an active systemd Ollama service. Pull, benchmark, and
capability require the isolated live pidfile and endpoint before making an
API request. Bootstrap refuses while the managed server is running: stop it
first.

The tunnel uses local port 11436, not local Ollama's 11434 or the vLLM
tunnel's 8001. It uses `ExitOnForwardFailure=yes`, so a bind conflict exits
instead of leaving a misleading SSH process.

### A100 comparison profiles

The official profiles below were pulled, loaded, and benchmarked on A100.
Detailed throughput, residency, and full-context proofs are in
[BENCHMARKS.md](BENCHMARKS.md):

| A100 vLLM profile | Ollama config | Official Ollama model | Context | Retained slots |
| -- | -- | -- | --: | --: |
| `qwen3-coder-30b` | `qwen3-coder-30b` | `qwen3-coder:30b` | 262,144 | 4 |
| `glm4.7-flash-awq` | `glm4.7-flash` | `glm-4.7-flash` | 202,752 | 8 |
| `qwen3.6-35b-a3b-awq` | `qwen3.6-35b-a3b` | `qwen3.6:35b-a3b` | 262,144 | 1 |
| `qwen3.8-27b` native | `qwen3.8-27b-native` | `qwen3.8:27b` | 262,144 | 1 |
| `gemma4-26b-a4b-awq` | `gemma4-26b` | `gemma4:26b` | 262,144 | 8 |

### Remote workflow

Read-only status does not deploy:

```bash
make ollama-remote-status HOST=<ssh-host>
```

Only after the host is confirmed idle, the isolated lifecycle is:

```bash
make ollama-remote-bootstrap HOST=<ssh-host>
make ollama-remote-start MODEL=qwen3-coder-30b \
  OLLAMA_NUM_PARALLEL=4 HOST=<ssh-host>
make ollama-remote-pull MODEL=qwen3-coder-30b HOST=<ssh-host>
make ollama-remote-bench MODEL=qwen3-coder-30b \
  OLLAMA_NUM_PARALLEL=4 OLLAMA_BENCH_JOBS=4 HOST=<ssh-host>
make ollama-remote-stop HOST=<ssh-host>
```

`ollama-remote-bootstrap`, `-start`, `-pull`, `-bench`, and `-capability`
implicitly deploy the current scripts. Stop, status, logs, and tunnel never
deploy as a side effect.

## Artifact identity

Every model config pins a reviewed Ollama registry manifest digest and its
expected format and native context. Before AuditBench starts, the adapter
checks `/api/tags` and `/api/show`, then confirms `/api/ps` loaded that same
digest. A moved alias, changed quantization, unexpected architecture, or stale
local pull fails explicitly instead of producing a result under the old model
name. Review and update the config expectation, then pull and rerun when an
artifact change is intentional.

## Gemma 4 E2B and Qwen3.5 4B

These profiles match the model and 131,072-token request limit of the
corresponding local vLLM profiles:

```bash
make ollama-start MODEL=gemma4-e2b
make ollama-pull MODEL=gemma4-e2b
make ollama-bench MODEL=gemma4-e2b
make ollama-stop

make ollama-start MODEL=qwen3.5-4b
make ollama-pull MODEL=qwen3.5-4b
make ollama-bench MODEL=qwen3.5-4b
make ollama-stop
```

The 128k limit is native for Gemma E2B. Qwen3.5 4B supports 262,144 tokens,
but this comparison profile deliberately uses 128k to match vLLM.

Gemma E2B supports real Ollama concurrency. Jobs 1, 2, and 4 each completed a
near-full-context request per slot while keeping all 36 reported layers on
GPU. Qwen3.5 4B completed one 123,030-token prompt with all 34 layers on GPU,
but explicit 2x and 4x probes were forced back to one effective slot by the
`qwen35` architecture guard. Measured allocations and throughput are in
[BENCHMARKS.md](BENCHMARKS.md).

## Nemotron 3.5 Lightning 30B-A3B

The `nemotron-3.5-lightning-30b` profile uses the official explicit
`nemotron-3.5-lightning:30b-a3b-q4_K_M` GGUF artifact. It is separate from the
Apple-only `nemotron-3.5-lightning-30b-mlx` safetensors profile:

```bash
make ollama-start MODEL=nemotron-3.5-lightning-30b
make ollama-pull MODEL=nemotron-3.5-lightning-30b
make ollama-status
make ollama-capability MODEL=nemotron-3.5-lightning-30b
make ollama-stop
```

The 23.68 GiB Q4_K_M weights cannot reside fully on the 12 GiB RTX. The
profile leaves placement to llama.cpp automatic fit, uses one request slot,
and caps the artifact's native 1,048,576-token context at 262,144 to match the
proven MLX operating point. At that limit the managed 0.32.14 runner allocated
432 MiB of q4 KV, down from 816 MiB with q8, plus 142.85 MiB of recurrent
state. The one-layer MTP draft keeps a separate 256 MiB f16 cache.

The local load-only run on 2026-08-25 verified the pinned digest, GGUF
identity, `nemotron_h_moe` architecture, 1M native context, llama.cpp
dispatch, one effective slot, and the 262,144-token q4 allocation. The host's
NVIDIA device was unavailable to NVML during that run, so Ollama loaded
25.17 GiB entirely in CPU RAM. That is not a GPU residency or performance
result. Keep this as a direct server experiment, absent from OpenCode and the
retained capability/benchmark inventories, until the same lifecycle passes
with CUDA available.

## Nemotron Nano 9B v2 availability

Ollama has no official NVIDIA Nemotron Nano 9B v2 artifact. Its official
Nemotron 3 Nano library contains 4B and 30B variants instead.

Two community uploads were found, but neither is an official like-for-like
artifact for the existing 6.23 GiB vLLM AWQ profile:

- `oamazonasgabriel/nemotron-nano-9b-v2`: 18 GB, 1M context, one tag.
- `mirage335/NVIDIA-Nemotron-Nano-9B-v2-virtuoso`: 9.1 GB, 1M context, one
  tag.

They are not wired or benchmarked here.

## Gemma 4 12B

The `gemma4-12b` profile runs the official `gemma4:12b` Q4_K_M artifact with
q8 KV and its native 262,144-token context:

```bash
make ollama-install
make ollama-start MODEL=gemma4-12b
make ollama-pull MODEL=gemma4-12b
make ollama-status
make ollama-bench MODEL=gemma4-12b
make ollama-stop
```

The manifest requires Ollama 0.30.5 or newer. One 262,144-token slot remains
fully GPU-resident on this host. Gemma 4 supports real parallel requests, but
additional 262k slots force CPU offload. The canonical RTX inventory therefore
retains jobs=1 rather than treating redundant offloaded slot counts as serving
profiles. The measured residency and AuditBench throughput are in
[BENCHMARKS.md](BENCHMARKS.md).

## Qwen3.5 9B and Qwen3.6 35B-A3B

Both profiles expose their native 262,144-token context with q8 KV:

```bash
make ollama-start MODEL=qwen3.5-9b
make ollama-pull MODEL=qwen3.5-9b
make ollama-bench MODEL=qwen3.5-9b
make ollama-stop

make ollama-start MODEL=qwen3.6-35b-a3b
make ollama-pull MODEL=qwen3.6-35b-a3b
make ollama-bench MODEL=qwen3.6-35b-a3b
make ollama-stop
```

The official Qwen3.5 9B manifest requires Ollama 0.17.1 or newer. The Qwen3.6
manifest declares no minimum; its profile requires the managed 0.32.14 runtime
against which it was validated.

Qwen3.5 9B stays fully GPU-resident at 10.21 GiB with its native 262k request
limit. Qwen3.6 allocates 14.53 GiB to CPU and 10.21 GiB to GPU; it has
similar raw decode but substantially slower prefill and end-to-end audit
throughput. Canonical 32k audit throughput is 70.34 calls/hour for Qwen3.5 9B
and 25.09 for Qwen3.6. Full results are in [BENCHMARKS.md](BENCHMARKS.md).

Neither model supports parallel requests under official Ollama 0.32.14.
Qwen3.5 uses the internal `qwen35` architecture and Qwen3.6 uses
`qwen35moe`; both are covered by the scheduler guard that forces `-np 1`.
Requested 2-slot and 4-slot profiles were tested for each model and remained
one effective slot. Their maximum verified operating point is therefore one
262,144-token request.

Qwen3.5 9B is the sole local Ollama model registered in OpenCode, as
`ollama-local/qwen3.5:9b`. Qwen3.6 remains available as a direct server
experiment.

## Qwen3.8-27B

The default config runs one `qwen3.8:27b` Q4_K_M model allocation with one
131,072-token request slot:

```bash
make ollama-install
make ollama-start MODEL=qwen3.8-27b
make ollama-pull MODEL=qwen3.8-27b
make ollama-status
make ollama-bench MODEL=qwen3.8-27b
make ollama-stop
```

For a quick allocation check without the throughput workloads:

```bash
make ollama-bench MODEL=qwen3.8-27b OLLAMA_BENCH_LOAD_ONLY=1
```

The fleet's default Ollama release is 0.40.3. The model manifest requires
at least 0.32.12, so the older system binary is not used. `ollama-install`
verifies the official release checksum and extracts it under
`${XDG_DATA_HOME:-~/.local/share}/ollama/runtime/`; it does not need root.
Model blobs stay in Ollama's normal per-user model store.

The launcher binds `127.0.0.1:11434`, enables Flash Attention, uses the
profile's KV type, keeps one model loaded, and gives llama.cpp a 1024 MiB
GPU-fit margin, 256 MiB on a CUDA GPU that drives no display.

### Parallelism limitation

The target was two concurrent 262,144-token slots. Official Ollama 0.32.14
cannot provide them for this model. Qwen3.8's public name differs from its
internal architecture family: its manifest declares `model_family: qwen35`.
Ollama's scheduler blocklists that architecture family from parallel requests
and forces `-np 1` even when `OLLAMA_NUM_PARALLEL=2`:

```text
model architecture does not currently support parallel requests
architecture=qwen35
```

Upstream issue `ollama/ollama#4165` tracks the limitation. Unmerged PR
`ollama/ollama#17144` removes the guard after the original llama.cpp recurrent
state crash was fixed, but this server stays on an official binary for now.
The managed default and all recorded benchmarks therefore use jobs=1. Context
defaults to 131,072 because the measured GPU offload and throughput are
materially better there; the model's native 262,144 remains an explicit
override.

## Why the split is unavoidable on this host

Qwen3.8-27B has 64 language layers, but only 16 use full attention. At the
131,072-token default, measured q8 target KV is 4.25 GiB and MTP draft KV is
512 MiB. The Q4_K_M language weights and vision projector add about 16.5 GiB
before runtime buffers.

The host has 12,227 MiB of VRAM and 62 GiB of RAM. Even jobs=1 cannot be wholly
GPU-resident; Ollama's automatic fit places 12.49 GiB in system RAM and
7.64 GiB on GPU at the retained 128k point. Canonical AuditBench measures only
2.93 decode tok/s and 2.70 cold-32k calls/hour there, so this is a
model-capability profile rather than a throughput choice. `make ollama-status`
reports Ollama's exact CPU/GPU byte split, effective job count, and runner RSS.
Measured throughput and residency are in [BENCHMARKS.md](BENCHMARKS.md).

The native context remains an explicit capability override, not a retained RTX
benchmark point:

```bash
OLLAMA_CONTEXT_LENGTH=262144 make ollama-start MODEL=qwen3.8-27b
```

q8 KV is deliberate: Ollama documents it as roughly half the f16 memory with
little quality loss. `q4_0` would halve KV again, but its quality loss is more
visible at long context and on grouped-query-attention models. It remains an
explicit experiment rather than the default:

```bash
OLLAMA_KV_CACHE_TYPE=q4_0 make ollama-start MODEL=qwen3.8-27b
```

## Using it from opencode

The generated providers `ollama` (`127.0.0.1:11434`) and `ollama-remote`
(`127.0.0.1:11436`, where `make ollama-remote-tunnel` lands) list every config
here, keyed by the `OLLAMA_MODEL` tag. The entries declare no reasoning,
because the capability check verifies Ollama reasoning only on its native
API, not on `/v1`. See [Using the servers from opencode](../README.md#using-the-servers-from-opencode).

```bash
OPENCODE_CONFIG=/path/to/llm-local-servers/opencode/ollama/opencode.json opencode
```

## Runtime state

Pidfile, log, and the pre-start GPU baseline live under
`${XDG_STATE_HOME:-~/.local/state}/ollama/`. The detached launcher uses a new
process group. Stop signals only that recorded group, then verifies that GPU
memory returned to within 512 MiB of the baseline.
