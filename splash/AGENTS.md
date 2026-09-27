# Splash runtime instructions

Root [AGENTS.md](../AGENTS.md) applies. This runtime serves deep-context
agent loops with the upstream native Metal engine; it does not translate
or reimplement benchmark workloads.

## Files

| File | Responsibility |
| -- | -- |
| `lib.sh` | Shared paths and uv invocation |
| `install.sh`, `pull.sh` | Root Make entry points for pinned installation |
| `run.sh`, `start.sh` | Detached launcher and foreground exec |
| `stop.sh`, `status.sh` | Inspection and verified teardown |
| `runtime.py` | Lifecycle, package verification, identity and HTTP authentication |
| `bench.py` | AuditBench transport, live capacity and provenance |
| `capability.py` | Shared API gate and Splash thinking-control mapping |
| `models/*.conf` | Immutable model facts and capability expectations |
| `Makefile` | Guard against built-in script-copy rules |
| `BENCHMARKS.md` | Retained measurement evidence |

## Invariants and retest conditions

- Use the standalone archive and checksum pinned in the root Makefile.
  Installation never replaces an existing version tree or global runtime.
  Model pulls select an immutable HF revision; upstream `prepare` follows
  `main` and is therefore unsuitable for this repository's pull target.
- Reuse upstream manifest validation and full artifact hashing. Native
  `/status` identity hashes describe layout, not content. A matching
  served name or layout alone cannot establish model identity.
- Use `uv run --no-project` with the bundled interpreter for adapters.
  Resolve the foreground interpreter with uv and exec it, preserving
  the pidfile's session leader across Python and native-engine startup.
- State and logs stay outside the repository. A lifecycle lock prevents
  concurrent mutation. Existing managed state blocks start/install/pull;
  stop validates PID start time and process-group ownership before
  signaling. Wait for transient zombies to disappear before declaring
  the group empty. macOS can return EPERM during native-worker exit;
  this means the group still exists, so keep waiting. Confirm port
  release too. Keep failure evidence.
  The foreground child waits on its parent's stdin gate until its
  ownership record is saved; direct `start.sh` use must fail.
- Bind loopback by default. Non-loopback requires an API key; pass it
  through the environment, never argv or measurement metadata. Adapter
  authorization headers apply only to the owned HTTP origin.
- The 64 GiB cap is launcher policy. Upstream clamps it to the device's
  working-set limit; do not duplicate that host adaptation in model
  configs. Keep raw sparse virtual KV, conservative benchmark capacity,
  four native active slots and measured streams distinct.
- DFlash 2, Q8 KV and state/prefix caching use release defaults. Their
  memory competes inside one dynamic budget; a virtual pool is not
  committed GPU memory. Larger queues do not lift the four-lane ceiling.
- Keep the 7,200-second request timeout. Release 1.0's 1,800-second
  default aborts healthy four-way Qwen3.8 near-context prefills with
  HTTP 504. Retest after an upstream timeout/scheduling change, using
  the same four-way near-context phase before lowering it.
- Splash expects top-level `reasoning_effort`. Do not use the shared
  vLLM control mapping, which nests it in `chat_template_kwargs`.
- Keep trial full-run provenance intact: retained v1 full runs are
  history, replaced only by canonical v2 session runs. Update the root
  README and CAPABILITIES alongside changes to retained serving results.
- Validate with `make lint`, `make test`, and the full managed lifecycle
  for both configured models. Stop and verify release even on failure.
- `start.sh` refuses a runtime directory whose `release.json` version differs
  from `SPLASH_VERSION`. The directory is named by the pin; the guard covers a
  mis-populated one.
