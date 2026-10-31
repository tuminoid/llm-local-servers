# Splash on Apple Silicon

Managed [Splash](https://github.com/incoai/splash), serving MLX and
GGUF targets with pinned DFlash 2 drafts, Q8 KV and prefix/state
caching. These defaults serve repeated deep agent requests; the measured
262K operating points are in [BENCHMARKS.md](BENCHMARKS.md).

## Install and run

Requires `uv`, Apple Silicon M3 or newer and macOS 26.4 or newer. Upstream
requires at least 36 GB unified memory and recommends 48 GB or more;
our four-stream 262K measurements used an M5 Max with 128 GB. Smaller
machines need their own capacity proof.

Run every command from the repository root:

```bash
make splash-install
make splash-pull MODEL=qwen3.6-35b-a3b
make splash-start MODEL=qwen3.6-35b-a3b
make splash-status
make splash-capability MODEL=qwen3.6-35b-a3b
make splash-bench MODEL=qwen3.6-35b-a3b
make splash-stop
make splash-status
```

The other profiles are in `models/`. There is no default model. Stop before
pulling another model or installing a runtime. `make splash-logs` follows
the current log. A guard Makefile rejects commands from this directory.

The installer verifies the release archive pinned in the root Makefile
(`SPLASH_VERSION`, `SPLASH_ARCHIVE_SHA256`) and extracts the standalone
runtime into `~/.local/share/splash/runtime/<SPLASH_VERSION>`. It owns no
Homebrew installation. `uv run` executes the repository's adapters using
the release's bundled interpreter and dependency set; installation,
status and teardown use uv-selected Python 3.12. The detached child uses
`uv python find` then `exec` so its PID remains the session leader.

Pull fetches the exact Hugging Face revisions of the target and its
draft named in the model config, then runs the release installer, which
assembles them under `~/.local/share/splash/models/`. Startup never
downloads or follows `main`. Before launch and measurement the assembly
is verified with full content hashes, and its recorded target and draft
sources are checked against the config.

## Serving settings

| Setting | Default | Purpose |
| -- | -- | -- |
| `SPLASH_HOST` | `127.0.0.1` | Bind address; a non-loopback address requires `SPLASH_API_KEY` |
| `SPLASH_PORT` | `8022` | Separate from Ollama and vLLM-Metal |
| `SPLASH_MAX_MEMORY` | the conf's `SPLASH_MEMORY_GIB`, clamped to host RAM minus 24 GiB | Native engine memory ceiling, including weights, KV and cached states |
| `SPLASH_REQUEST_TIMEOUT` | `7200` | Allows the dense model's four-way deep prefills to complete |
| `SPLASH_START_TIMEOUT` | `600` | Readiness deadline in seconds |
| `SPLASH_DATA_DIR` | XDG data root + `/splash` | Versioned runtime and model links |
| `SPLASH_STATE_DIR` | XDG state root + `/splash` | Managed pidfile and current log |

Host settings can be exported or prefixed to `make`. Model facts live in
`models/<name>.conf`: immutable target and draft revisions,
262,144-token context, memory need, and capability expectations. `SPLASH_MODEL_CONF`
can select an alternate config file. Environment values override config
defaults. Carry `SPLASH_API_KEY` into status, benchmark and capability
commands when authentication is enabled; the key is never put in argv
or retained metadata.

Splash itself clamps the requested memory ceiling to Metal's recommended
working set minus its safety margin. It also guards allocations against
host memory pressure. A configured 262K context is a per-request limit,
not a claim that every machine can admit four such requests.

The native maximum decode width is four. Larger client queues can wait,
but they cannot create more active lanes in this release. The adapter
reads the live memory plan and conservatively bounds the KV extent pool
by dynamic memory after reserving active lane state. Retained
cache states share that memory and may evict. AuditBench admits only
stream counts that fit both scheduler width and this capacity bound.

## Agent API and measurement

The OpenAI-compatible endpoint is `http://127.0.0.1:8022/v1`. Thinking is
enabled by default; top-level `reasoning_effort: "none"` disables it.
The capability adapter preserves this wire format rather than sending
vLLM's nested `chat_template_kwargs` option. See the measured reasoning,
tool-call, streaming, JSON and schema results in
[CAPABILITIES.md](../CAPABILITIES.md).

The generated provider `splash` lists every config, keyed by
`SPLASH_MODEL_REPO`. See [Using the servers from opencode](../README.md#using-the-servers-from-opencode).

```bash
OPENCODE_CONFIG=/path/to/llm-local-servers/opencode/splash/opencode.json opencode
```

Benchmark and capability fixtures come only from `llm-audit-bench`.
`make splash-bench` defaults to the canonical session profile and preserves
the model's default thinking behavior.
An explicit `AUDIT_BENCH_REASONING_EFFORT=none` control is recorded in
the result and changes the operating point.
Both shared profiles are available through `AUDIT_BENCH_PROFILE`.
With the existing laptop power gate:

```bash
AUDIT_BENCH_GATE_CMD=vllm-metal/battery-gate.sh \
  make splash-bench MODEL=qwen3.6-35b-a3b
```

Retained v1 `full` results keep their provenance as history.
Default JSON retention is `~/.local/state/auditbench/` and
`~/.local/state/capability-check/`. Normal teardown confirms the process
group is empty and the port is released, then removes the pidfile and
log. Failed starts/stops retain diagnostic logs.
