# Strata runtime instructions

Root [AGENTS.md](../AGENTS.md) applies. Usage and knobs are in
[README.md](README.md), results on the hardware pages (`docs/hardware/`),
investigations in [BENCHMARKS.md](BENCHMARKS.md).

## Files

| File | Responsibility |
| -- | -- |
| `lib.sh` | Shared paths and the stdlib lifecycle's interpreter |
| `install.sh`, `pull.sh` | Root Make entry points for the pinned build and pull |
| `run.sh`, `start.sh` | Detached launcher and foreground exec of the server |
| `stop.sh`, `status.sh` | Inspection and verified teardown |
| `runtime.py` | Build, pull and verification, placement, lifecycle, identity |
| `bench.py` | AuditBench transport, capacity, residency and provenance |
| `capability.py` | Shared API gate with the template's thinking switch |
| `models/*.conf` | Immutable model facts and capability expectations |
| `Makefile` | Guard against built-in script-copy rules |
| `BENCHMARKS.md` | Retained measurement evidence |

## Invariants and retest conditions

- The pin is the tag's commit. The source tree must sit at it with no
  tracked changes; the engine is checked against the install receipt's
  SHA-256 and GPU architectures, and a host whose GPUs differ rebuilds.
  The MTP checkpoint revision is the source tree's own pin, read from
  it, never restated here.
- The engine is built from source with Strata setup's NVIDIA options, never
  taken from a release package: those carry no sm_80 code. Install builds
  both engines from `engine/`, the Inkling one in `build-inkling2` with
  `STRATA_BUILD_INKLING`, with `GGML_CCACHE=OFF` (a ccache on `PATH` breaks
  nvcc) and one retry of a failed build (CUDA 13's ptxas fails a parse now
  and then), and the receipt holds both checksums. Validate a pin bump on
  the A100 and on a second GPU generation, and check the architectures in
  the receipt.
- The run config states each family's drafter (`drafting`): left at
  auto, the server chooses by the served name, which is no model fact.
  Inkling's server-side thinking budget is 0 (none): left unset, the
  server caps thinking at 2,048 tokens per request by effort level.
- The Inkling drafter is the original checkpoint's `mtp.safetensors`,
  which only an engine whose `--info` reports `dspark_f32_widen=1` reads
  correctly; an engine without it rejects every draft.
- The server spawns the engine in a process group of its own and restarts
  it after a crash, at most three times in ten minutes. The pidfile records
  both, with their start times, and
  the engine is looked up again under the server when the recorded one is
  gone. Stop signals the server, which stops the engine; a surviving engine
  is signalled directly, and stop fails until the engine is gone from the
  GPU's compute processes. A stop that finds nothing running keeps the logs.
- No `STRATA_*` variable from the caller reaches the server or the engine:
  the engine reads its tuning switches from the environment, and a managed
  run is tuned only by the config's `STRATA_ENGINE_ARGS`. Strata itself
  keeps short-lived process records under `$XDG_STATE_HOME/strata`, beside
  the managed state locally and in the host's own state directory remotely.
- Start refuses while any GPU compute process is active: the expert cache
  sizes itself to the free VRAM, so a co-tenant changes what is measured.
- Each slot holds one full-context session; the KV pool is slots times the
  context. The engine reads one admission's prompt at a time, with the
  other slots decoding between its chunks; on deep agent sessions two
  streams measured slower than one on every pack tried, with batch MTP
  drafts and a raised decode share too. The Flash-Next config serves one
  slot. The Inkling engine batches its four slots, and on the A100 two
  streams measured no faster than one (0.2.21). Retest when a release
  changes admission or batch decoding.
- `bench.py` refuses a server whose engine did not report every routed
  expert in VRAM: experts computed on the CPU are not a GPU serving result.
  The capability gate runs on every profile, a CPU-lane one included.
- The PLE table cannot be locked when `RLIMIT_MEMLOCK` is below its size.
  It then serves faulted-in and reclaimable, and the engine says so in its
  log. Heavy disk writes on the host can evict it mid-run, so keep pulls
  and other large writes off the host while measuring.
- Strata ends a response at EOS rather than at `max_tokens` (a 128-token
  reference call returned 33 to 43 tokens on every pack tried), so the
  harness's llama-bench reference line is unavailable. It is a diagnostic
  only.
- Validate with `make lint`, `make test`, and the full managed lifecycle on
  every configured model. Stop and verify release even on failure.
