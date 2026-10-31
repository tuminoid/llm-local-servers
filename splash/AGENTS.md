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
| `runtime.py` | Lifecycle, model installation and verification, identity and HTTP authentication |
| `bench.py` | AuditBench transport, live capacity and provenance |
| `capability.py` | Shared API gate and Splash thinking-control mapping |
| `models/*.conf` | Immutable model facts and capability expectations |
| `Makefile` | Guard against built-in script-copy rules |
| `BENCHMARKS.md` | Retained measurement evidence |

## Invariants and retest conditions

- Use the standalone archive and checksum pinned in the root Makefile.
  Installation never replaces an existing version tree or global runtime.
  Install records the engine binary and metallib digests from the
  checksum-verified archive (1.5.0's `release.json` no longer states them),
  and every verification checks them. The server loads the model
  directory's own tokenizer (1.4.0 dropped `--tokenizer`).
  Model pulls select immutable HF revisions for the target and its
  DFlash2 draft. Upstream `prepare` has no draft revision option and
  installs a draft repository's default branch, so the draft is passed as
  its pinned snapshot directory, and pinned against cache pruning; the
  target goes through `--revision`.
- Reuse the release installer's assembly verification with full content
  hashes, and check its recorded target source and draft snapshot against
  the config. Splash packages no longer load (1.3.1). A matching served
  name alone cannot establish model identity.
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
- A conf declares its memory need, `SPLASH_MEMORY_GIB` (weights, draft and
  four full-context KV streams; 64 when omitted), as a model fact. The
  launcher grants it clamped to host RAM minus `HOST_RESERVE_GIB`, and
  upstream further clamps to the device's working-set limit; never put a
  host value in a conf. A model larger than its grant streams experts from
  the SSD, which costs throughput, so size the need from a measured run.
  Keep raw KV capacity, conservative benchmark capacity, four native active
  slots and measured streams distinct.
- DFlash 2, Q8 KV, state/prefix caching, the dense target's Neural Engine
  FFN split and idle weight release use release defaults. Their memory
  competes inside one dynamic budget; KV capacity is not committed GPU
  memory. Larger queues do not lift the four-lane ceiling.
- Keep the 7,200-second request timeout. Release 1.0's 1,800-second
  default aborted healthy four-way Qwen3.8 near-context prefills with
  HTTP 504; since 1.2.0 there is no default, so this is the only bound.
  Lower it only after the same four-way near-context phase fits.
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
