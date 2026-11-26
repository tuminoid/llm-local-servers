# FreeToken

[FreeToken](https://github.com/FlashML-org/FreeToken) is an MoE serving
engine with semantic-anchor prefix caching for agent sessions and elastic
GPU/host expert placement. It serves llama.cpp GGUF files on llama.cpp's own
CUDA kernels and speaks the OpenAI chat API with tool calls and
`reasoning_content`. Linux x86_64 with an NVIDIA GPU and a CUDA 13 toolkit
only: its kernels compile on first use.

## Usage

```bash
make freetoken-install
make freetoken-pull MODEL=ornith1.5-35b-a3b
make freetoken-start MODEL=ornith1.5-35b-a3b
make freetoken-capability MODEL=ornith1.5-35b-a3b
make freetoken-bench MODEL=ornith1.5-35b-a3b
make freetoken-stop
```

On a remote GPU host the same verbs are `freetoken-remote-*` with
`HOST=<ssh-host>`; `freetoken-remote-bootstrap` installs, and
`freetoken-remote-tunnel` forwards the loopback API to this machine.

Install fetches the release's engine wheel and prebuilt kernel-cache wheel,
each checked against the root Makefile's SHA-256, into a venv of their own
with ninja (FlashInfer JIT-builds its attention modules at engine start and
shells out to it). Pull fetches the config's GGUF file(s) at the pinned
revision and records their SHA-256; start verifies them again.

## Serving settings

| Setting | Default | Purpose |
| -- | -- | -- |
| `FREETOKEN_PORT` | `8027` | Loopback port; the remote tunnel uses 8028 locally |
| `FREETOKEN_CUDA_HOME` | the `nvcc` on `PATH`, else `/usr/local/cuda` | CUDA 13 toolkit for the kernels compiled at start |
| `FREETOKEN_START_TIMEOUT` | `1800` | Readiness deadline in seconds |
| `FREETOKEN_DATA_DIR` | XDG data root + `/freetoken` | Wheels, venv, models |
| `FREETOKEN_STATE_DIR` | XDG state root + `/freetoken` | Managed pidfile and current log |

Model facts live in `models/<name>.conf`: repository, immutable revision,
GGUF file(s), served context, admission (`--max-running-requests`), the MoE
strategy (`fused`: every expert in VRAM; `offload`: experts in pinned host
RAM behind a GPU expert cache), the allowed engine flags, capability
expectations and the checkpoint's sampling.
