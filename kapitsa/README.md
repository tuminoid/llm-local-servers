# Kapitsa on Apple Silicon

Managed [Kapitsa](https://github.com/nace-ai/kapitsa), a native Metal engine
for Qwen3.5-family hybrid models with prefix reuse and speculative decoding.
It serves DiffuSpace's Clover-35B-A3B block-diffusion MoE in Clover's own
self-speculative mode; Splash serves the plain Qwen models faster.
Measured operating points are in [BENCHMARKS.md](BENCHMARKS.md).

## Install and run

Requires `uv`, `git`, Apple Silicon, macOS 14 or newer, and the Xcode
Command Line Tools' `c++` for the model converter. Run every command from
the repository root:

```bash
make kapitsa-install
make kapitsa-pull MODEL=clover-35b-a3b
make kapitsa-start MODEL=clover-35b-a3b
make kapitsa-status
make kapitsa-capability MODEL=clover-35b-a3b
make kapitsa-bench MODEL=clover-35b-a3b
make kapitsa-stop
```

There is no default model. Stop before pulling or installing a runtime.
`make kapitsa-logs` follows the current log. A guard Makefile rejects
commands from this directory.

Install verifies the release archive pinned in the root Makefile
(`KAPITSA_VERSION`, `KAPITSA_ARCHIVE_SHA256`), extracts it into
`~/.local/share/kapitsa/runtime/<KAPITSA_VERSION>`, and fetches the
release's source commit (`KAPITSA_SOURCE_COMMIT`) into
`~/.local/share/kapitsa/source/` for its model converters.

Pull downloads the pinned Hugging Face revision (a host `hf`, else a
pinned `huggingface_hub` through uv) into `~/.local/share/kapitsa/work/`,
runs the release's converter (`KAPITSA_CONVERTER`) on it into the engine's
own store, `~/.local/share/kapitsa/home/models/`, and deletes the download
once the pack verifies; a failed pull keeps it to resume. Clover's BF16
checkpoint is 69 GB, its pack 19.5 GB. Startup never downloads: before
launch and measurement every file is checked against the conversion record
with full content hashes.

## Serving settings

| Setting | Default | Purpose |
| -- | -- | -- |
| `KAPITSA_PORT` | `8024` | Separate from the other Apple Silicon runtimes |
| `KAPITSA_DISK_CACHE` | `0` | SSD prefix cache size; off so a run never reads an earlier run's prompts |
| `KAPITSA_START_TIMEOUT` | `600` | Readiness deadline in seconds |
| `KAPITSA_DATA_DIR` | XDG data root + `/kapitsa` | Versioned runtime, source and the engine's home |
| `KAPITSA_STATE_DIR` | XDG state root + `/kapitsa` | Managed pidfile and current log |

The server listens on loopback only and stays out of Bonjour (`--private`);
reach it from another machine through an ssh tunnel. Slots and the
memory plan are Kapitsa's own for the host. Model facts live in
`models/<name>.conf`: the immutable source revision, converter, context,
decode switches, capability expectations and the checkpoint's sampling.
