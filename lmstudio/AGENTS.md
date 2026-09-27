# LM Studio runtime instructions

Root [AGENTS.md](../AGENTS.md) applies. Usage and rationale are in
[README.md](README.md).

## Files

| File | Responsibility |
| -- | -- |
| `runtime.py` | Lifecycle, pin checks, pulls and live identity; the Makefile calls its verbs |
| `bench.py` | AuditBench transport, admission and provenance |
| `capability.py` | Capability Check v2 with LM Studio's top-level thinking control |
| `models/*.conf` | One artifact each: format, repo, revision, context, expectations |
| `Makefile` | Guard against built-in script-copy rules |

## Argued deviations

- **No pidfile or process group.** The LM Studio service owns the engine
  processes. Ownership is `server.json`: the identifier this runtime loaded
  and whether it started the server. Start coexists with the operator's
  loads and server. Stop acts on that record alone: it verifies the
  identifier is gone from `lms ps`, and the port closed if it owned the
  server.
- **No start/run split and no lib.sh.** Nothing is detached, and all paths
  live in `runtime.py`, so shell wrappers would only forward arguments.
- **Install verifies, it does not install.** The app installs and updates its
  engines. `lmstudio-install` reports the app and selected engines against
  the pins; selecting an engine is the operator's `lms runtime select`.
- **Pins gate measurements, not serving.** The operator owns LM Studio and
  it updates itself, so start serves whatever engine is selected and names
  any drift. Bench and capability refuse drift: their rows are only
  comparable at the measured release.

## Invariants

- Pull only into `llm-local-servers/<config>`. `lms load` takes a model key,
  not a path, and keys turn into `publisher/name@quant` as soon as two copies
  of a model exist; resolve the key from the path at every start and verify
  the loaded path. The operator's own downloads must never satisfy identity.
- Every served file carries Hugging Face metadata naming the pinned revision.
  Copy by APFS clone, never by symlink: LM Studio skips symlinked folders.
- Engine facts belong in `FORMATS`: the preference key, the format `lms`
  reports, the pin variable, and fixed lanes. Model facts stay in configs.
- Refuse a remote LM Link preferred device; a load would run on that host.
- The OpenAI endpoint lists every downloaded model; select the served id.
  `tool_choice` accepts strings only, and reasoning arrives in
  `reasoning_content`, which Capability Check accepts as its alias.

## Retest conditions

- The MLX configs' `LMSTUDIO_BENCH_TOLERATE_OFF_BY_ONE`: clear it once
  `max_tokens=1` returns `completion_tokens=1` on the MLX engine.
- Linux and Windows need GGUF configs, a llama.cpp pin and host checks in
  `host_supports`; `fcntl` has no Windows equivalent in the lifecycle lock.
