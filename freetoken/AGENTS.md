# FreeToken runtime instructions

Root [AGENTS.md](../AGENTS.md) applies. Usage and knobs are in
[README.md](README.md), results on the hardware pages (`docs/hardware/`),
investigations in [BENCHMARKS.md](BENCHMARKS.md).

## Files

| File | Responsibility |
| -- | -- |
| `lib.sh` | Shared paths and the stdlib lifecycle's interpreter |
| `install.sh`, `pull.sh` | Root Make entry points for the pinned install and pull |
| `run.sh`, `start.sh` | Detached launcher and foreground exec of `ft serve` |
| `stop.sh`, `status.sh` | Inspection and verified teardown |
| `runtime.py` | Install, pull and verification, lifecycle, identity, engine facts |
| `bench.py` | AuditBench transport, capacity and provenance |
| `capability.py` | Shared API gate with the template's thinking switch |
| `models/*.conf` | Immutable model facts and capability expectations |
| `Makefile` | Guard against built-in script-copy rules |
| `BENCHMARKS.md` | Retained measurement evidence |

## Invariants and retest conditions

- The install is the release's two wheels, each checked against its pinned
  SHA-256 before use, plus a pinned ninja, in a venv per version. The
  receipt records the `ft` entry point's digest; start refuses a venv that
  differs. Never install from PyPI by name: the release assets are the pin.
- Serve with `ft serve` only. `ft launch` installs and configures
  third-party agent CLIs, outside a server runtime's scope.
- `/v1/models` answers while the model still loads, and completions return
  503 "model is still loading" meanwhile, so readiness is a completed
  one-token request, never the model list.
- FreeToken runs its engine in subprocesses of the server, in the server's
  process group. Stop signals the group and fails until every member has
  exited and left the GPU's compute processes.
- No `FREETOKEN_*` variable from the caller reaches the server; the venv's
  `bin` and the CUDA toolkit lead `PATH`, and the hub is offline.
- Start refuses while any GPU compute process is active: the KV pool and
  expert cache size themselves to the free VRAM, so a co-tenant changes
  what is measured. An `offload` config also needs its GGUF size plus
  16 GiB of `MemAvailable`; pinned experts must never push the host to swap.
  Offload reserves the context times admission as KV, since its default
  8,192-token reserve leaves the expert cache the rest of the card.
- The KV pool is the one FreeToken logs it allocated, shared by the running
  requests; the benchmark's admission is the launch's
  `--max-running-requests`. The resolved MoE strategy is read from the log
  and must equal the config's.
- Validate with `make lint`, `make test`, and the full managed lifecycle on
  every configured model. Stop and verify release even on failure.
