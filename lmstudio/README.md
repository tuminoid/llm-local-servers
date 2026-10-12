# LM Studio server

[LM Studio](https://lmstudio.ai) serves models through its desktop service and
its engines: Splash and MLX on Apple Silicon, llama.cpp everywhere. This
runtime drives that service with pinned versions and pinned checkpoints, so
its rows compare directly against the native runtimes serving the same
weights.

## Engines per platform

One config per artifact; the artifact decides the engine.

| Host | Engine | Configs |
| -- | -- | -- |
| Apple Silicon M3 or newer, macOS 26.4+ | Splash (Splash 1.0.2) | `qwen3.6-35b-a3b-splash`, `qwen3.8-27b-splash` |
| Other Apple Silicon | MLX (mlx-llm) | `qwen3.6-35b-a3b-mlx`, `qwen3.8-27b-mlx` |
| Linux, Windows | llama.cpp (GGUF) | none yet |

The Splash configs load the Splash packages [splash/](../splash/README.md)
served before 1.3.1, and the MLX configs the mlx-community checkpoints it now
serves, at the same revisions. On an M3+ host use the Splash engine: its
configs pass Capability Check v1 and decode 2.2-2.4x faster at one stream,
while the MLX configs ignore schema enforcement. LM Studio runs Splash one
request at a time, so the MLX engine only catches up at four streams; it
remains the path for older Apple Silicon. Measurements are in
[BENCHMARKS.md](BENCHMARKS.md).

## Usage

```bash
make lmstudio-install                          # verify the pinned app and engines
make lmstudio-pull MODEL=qwen3.8-27b-splash    # pinned, hash-verified download
make lmstudio-start MODEL=qwen3.8-27b-splash
make lmstudio-status
make lmstudio-capability MODEL=qwen3.8-27b-splash
make lmstudio-bench MODEL=qwen3.8-27b-splash
make lmstudio-stop
```

The generated provider `lmstudio` lists every config here, keyed by the
config name that start loads as the identifier. Reasoning arrives in
`reasoning_content`. See [Using the servers from opencode](../README.md#using-the-servers-from-opencode).

```bash
OPENCODE_CONFIG=/path/to/llm-local-servers/opencode/lmstudio/opencode.json opencode
```

## Pins and identity

The app auto-updates and installs its engines itself, so the root Makefile pins
versions instead of archives: `LMSTUDIO_VERSION` for the app and one engine
version per format. They name the release the results here were measured on.
Bench and capability refuse any other; install and start report the drift and
serve whatever LM Studio selects. Re-gate before moving a pin.

A pull downloads the pinned Hugging Face revision into LM Studio's models
folder under `llm-local-servers/<config>`. `hf download` hashes every file
against that revision, and start refuses a file whose metadata names any
other. When the Hugging Face cache already holds the pinned snapshot, the pull
starts from an APFS clone of it, which costs no space; LM Studio does not
follow symlinks.

## Server policy

Start coexists with the operator's LM Studio: their loaded models stay loaded,
and a server already running on the port is reused as configured. Otherwise
start starts one on `127.0.0.1:1234` and confirms LM Studio recorded loopback
without CORS. It loads the pulled copy at the configured context under the
key LM Studio currently lists for its path and checks the live load against
the record. Stop unloads that identifier, and stops the server only when
start started it; without a record it touches nothing. Bench and capability
need the model alone in LM Studio. Just-in-time loading stays on, since
LM Studio 0.4.25 exposes no switch for it: a request naming another
downloaded model loads it, and stop leaves such loads.

Admission: LM Studio ignores `--parallel` for the Splash engine and serves its
requests one at a time, so Splash configs admit one stream; the MLX engine
loads with `--parallel 4` (`LMSTUDIO_PARALLEL`).
LM Studio exposes no KV pool, so the benchmark records configured context
times active slots as allocation, not as a measured pool.

## The MLX engine's token accounting

mlx-llm 1.11.0 reports `completion_tokens` one low whenever the length cap cuts
a response. The MLX configs therefore run AuditBench with
`AUDIT_BENCH_TOLERATE_OFF_BY_ONE=1`: exact at that offset, and
`canonical: false` by protocol. The Splash engine reports exact counts.
