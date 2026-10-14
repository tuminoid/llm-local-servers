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

The fleet default runtime is the root Makefile's `OLLAMA_VERSION`. Profiles
that need another release declare it per profile with
`OLLAMA_RUNTIME_VERSION`: the M5's MLX profiles stay on the release their
runner was validated on (the MLX memory runaway is unproven on 0.40.x);
remote lifecycle calls for such a profile also pass its `OLLAMA_VERSION` at
the make level.

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
| Pinned binary | `tmp/ollama/runtime/v<OLLAMA_VERSION>/bin/ollama` |
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

### A100 profiles

The A100 runs on Ollama only the two models no vLLM profile serves there;
throughput, residency and full-context proofs are in
[BENCHMARKS.md](BENCHMARKS.md):

| Ollama config | Ollama model | Context | Slots |
| -- | -- | --: | --: |
| `ornith1.5-35b-a3b` | `ornith-1.5:35b` | 262,144 | 1 |
| `qwen3.8-flash-next-gguf-iq4xs` | `qwen3.8-flash-next:ud-iq4xs` (local import) | 262,144 | 2 |

### Remote workflow

Read-only status does not deploy:

```bash
make ollama-remote-status HOST=<ssh-host>
```

Only after the host is confirmed idle, the isolated lifecycle is:

```bash
make ollama-remote-bootstrap HOST=<ssh-host>
make ollama-remote-start MODEL=ornith1.5-35b-a3b HOST=<ssh-host>
make ollama-remote-pull MODEL=ornith1.5-35b-a3b HOST=<ssh-host>
make ollama-remote-bench MODEL=ornith1.5-35b-a3b HOST=<ssh-host>
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

## Install and launcher

`make ollama-install` verifies the official release checksum and extracts it
under `${XDG_DATA_HOME:-~/.local/share}/ollama/runtime/`; it does not need
root. Model blobs stay in Ollama's normal per-user model store.

The launcher binds `127.0.0.1:11434`, enables Flash Attention, uses the
profile's KV type, keeps one model loaded, and gives llama.cpp a 1024 MiB
GPU-fit margin, 256 MiB on a CUDA GPU that drives no display. For a quick
allocation check without the throughput workloads:

```bash
make ollama-bench MODEL=saluki-27b OLLAMA_BENCH_LOAD_ONLY=1
```

### Parallelism limitation

Qwen3.8 (Saluki) declares the internal `qwen35` architecture, and Qwen3.6
and Ornith `qwen35moe`. Ollama's scheduler blocklists both families
from parallel requests and forces `-np 1` even when `OLLAMA_NUM_PARALLEL=2`:

```text
model architecture does not currently support parallel requests
architecture=qwen35
```

Upstream issue `ollama/ollama#4165` tracks the limitation. Unmerged PR
`ollama/ollama#17144` removes the guard after the original llama.cpp recurrent
state crash was fixed, but this server stays on an official binary for now.
These profiles and all their recorded benchmarks therefore use one slot.

## Underdog Saluki 27B

The `saluki-27b` profile is the RTX's fully GPU-resident Qwen3.8-27B: a
2-bit mixed-precision GGUF (`Underdog-Saluki-27B-1.0-IQ2-mix.gguf`, 7.9 GB,
`ConwayResearch/Underdog-Saluki-27B-1.0` at the revision and sha256 in the
conf). It is a local import, so `make ollama-pull` refuses it. Download the
file into a staging directory of real files, check its sha256 against the
conf, and put beside it a Modelfile of:

```text
FROM ./Underdog-Saluki-27B-1.0-IQ2-mix.gguf
RENDERER qwen3.8
PARSER qwen3.5
```

then import it through the managed server and run the lifecycle:

```bash
make ollama-start MODEL=saluki-27b
OLLAMA_HOST=127.0.0.1:11434 ~/.local/share/ollama/runtime/v"${OLLAMA_VERSION:?set to the root Makefile OLLAMA_VERSION}"/bin/ollama create saluki:27b-iq2mix -f Modelfile
make ollama-capability MODEL=saluki-27b
make ollama-bench MODEL=saluki-27b
make ollama-stop
```

The import's manifest digest is pinned in the conf; a different digest
means a different file or Modelfile. The operating point is 163,840 tokens
with q4_0 KV, where weights, KV and compute buffer keep all 65 layers on
the 12 GiB card under the launcher's no-display fit margin. Larger
contexts move layers to the CPU; measurements are in
[BENCHMARKS.md](BENCHMARKS.md).

## Qwen3.6 35B-A3B REAP-48

The `qwen3.6-35b-a3b-reap48` profile is the RTX's fully GPU-resident
Qwen3.6-35B-A3B: `Qwen3.6-35B-A3B-REAP-48-v2.gguf` (9.4 GB, 48% of the
routed experts pruned), from `crucible-labs/Qwen3.6-35B-A3B-REAP-48-v2-GGUF`
at the revision and sha256 in the conf. It is imported like Saluki, as
`qwen3.6:35b-a3b-reap48` with the Modelfile in its conf, and runs at
262,144 with q4_0 KV, weights and KV all on the GPU; measurements are in
[BENCHMARKS.md](BENCHMARKS.md).

## LFM2.5 24B-A2B

The `lfm2.5-24b-a2b` profile is LiquidAI's LFM2.5-24B-A2B (24B total, 2.45B
active) as unsloth's `LFM2.5-24B-A2B-UD-IQ3_XXS.gguf` (9.0 GB), at the
revision and sha256 in the conf, imported like Saluki as
`lfm2.5:24b-a2b-iq3xxs` with the Modelfile in its conf (`RENDERER lfm2`,
`PARSER lfm2-thinking`). It runs at its native 131,072 with f16 KV, all on
the GPU. It fails Capability Check v2 audit fitness, so it serves
interactive use and has no secaudit preset; measurements are in
[BENCHMARKS.md](BENCHMARKS.md).

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
