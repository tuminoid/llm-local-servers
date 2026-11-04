# Strata on Linux NVIDIA

Managed [Strata](https://github.com/Niko1221/Strata), a C++/CUDA engine for
Qwen3.8-Flash-Next built on parts of llama.cpp's ggml, with its own decode,
prompt and MoE kernels, MTP speculative decoding and an OpenAI-compatible
Python server. It keeps the routed experts in a VRAM expert cache and
computes the ones that do not fit on the CPU; on a card that holds every
expert, it serves entirely from the GPU. Measured operating points are in
[BENCHMARKS.md](BENCHMARKS.md).

## Install and run

Requires Linux, an NVIDIA GPU of compute capability 7.5 or newer and its
driver, the CUDA toolkit (`nvcc`; `STRATA_CUDA_HOME` names its root when it
is not on `PATH` or in `/usr/local/cuda`), `python3` with `venv`, `git` and
a C++ compiler. Pull uses a host `hf`, else the pinned client that install
puts in the venv. Run every command from the repository root:

```bash
make strata-install
make strata-pull MODEL=qwen3.8-flash-next-nvfp4
make strata-start MODEL=qwen3.8-flash-next-nvfp4
make strata-status
make strata-capability MODEL=qwen3.8-flash-next-nvfp4
make strata-bench MODEL=qwen3.8-flash-next-nvfp4
make strata-stop
```

The same verbs run on the remote GPU host as `strata-remote-*` with
`HOST=<ssh-host>`; `strata-remote-bootstrap` is the remote install and
`strata-remote-tunnel` forwards `localhost:8026` to the remote server.
There is no default model. Stop before pulling or installing.
`make strata-logs` follows the server log. A guard Makefile rejects commands
from this directory.

Install fetches the pinned source commit (`STRATA_COMMIT`, the
`STRATA_VERSION` tag's commit) into `~/.local/share/strata/source/`, and the
llama.cpp commit that tree's `setup.py` pins beside it. It installs the
tree's pinned Python requirements into its own `.venv`, and builds the
engine with the options Strata's own setup uses, for the compute
capabilities of this host's GPUs. The release packages carry no sm_80 code,
so an A100 needs this build.

Pull downloads the pack's pinned Hugging Face revision into
`~/.local/share/strata/models/<owner>--<repo>/<revision>/`. It builds the
MTP draft layer once, with Strata's own tools from the original checkpoint's
MTP tensors at the source tree's pinned revision. Every file's SHA-256 goes
into the folder's `llm-local-servers.json`. Startup never downloads: every
file is checked against that record before launch and before measurement.

## Serving settings

| Setting | Default | Purpose |
| -- | -- | -- |
| `STRATA_PORT` | `8025` | Separate from the other runtimes and tunnels |
| `STRATA_START_TIMEOUT` | `1800` | Readiness deadline in seconds |
| `STRATA_CUDA_HOME` | the `nvcc` on `PATH`, else `/usr/local/cuda` | Toolkit the engine is built against |
| `STRATA_DATA_DIR` | XDG data root + `/strata` | Source, build, venv, models and draft layer |
| `STRATA_STATE_DIR` | XDG state root + `/strata` | Pidfile, run config, server and engine logs |

The server listens on `127.0.0.1` and runs `--offline`: no image URLs or
MCP subprocesses. Reach it from another machine through an ssh tunnel.

The launcher derives the memory placement from the host. The n-gram (PLE)
table is held in RAM when the available memory covers it beside the pinned
expert copy, plus 16 GiB, and is otherwise read from the disk. Above 65,536
tokens of context the KV cache streams from pinned RAM with a 32,768-token
window in VRAM. Model facts live in `models/<name>.conf`: the pack's
immutable revision and file names, context, slots, engine flags, capability
expectations and the checkpoint's sampling.
