# Kapitsa runtime instructions

Root [AGENTS.md](../AGENTS.md) applies. Usage and knobs are in
[README.md](README.md), measurements and verdicts in
[BENCHMARKS.md](BENCHMARKS.md).

## Files

| File | Responsibility |
| -- | -- |
| `lib.sh` | Shared paths and uv invocation |
| `install.sh`, `pull.sh` | Root Make entry points for pinned installation |
| `run.sh`, `start.sh` | Detached launcher and foreground exec |
| `stop.sh`, `status.sh` | Inspection and verified teardown |
| `runtime.py` | Lifecycle, model pull, conversion and verification, identity |
| `bench.py` | AuditBench transport, live capacity and provenance |
| `capability.py` | Shared API gate with the template's thinking switch |
| `models/*.conf` | Immutable model facts and capability expectations |
| `Makefile` | Guard against built-in script-copy rules |
| `BENCHMARKS.md` | Retained measurement evidence |

## Invariants and retest conditions

- The pin is the release archive and its sha256, plus the release's source
  commit (the tag's merge commit) for the model converters the archive
  leaves out. The installed binary must report the pinned version, and the
  source tree must sit at the commit with no local changes.
- Kapitsa self-updates by default. Every engine invocation carries
  `KAPITSA_NO_AUTO_UPDATE=1`, and its home (`KAPITSA_HOME`) is the managed
  data tree, so its store, converter work folder and saved state never
  touch `~/.cache/kapitsa`.
- `serve` defaults to `0.0.0.0` with no authentication and advertises
  itself over Bonjour. The launcher always passes `--private` (loopback,
  no Bonjour) and has no host knob: remote use is an ssh tunnel.
- Catalog models are pulled by the pinned binary, which fixes their
  revisions; the config restates the repository, revision and companions,
  and verification compares them with the store's manifest, then hashes
  every file the manifest gives a sha256. A config change without a
  release bump that moves the catalog is a mismatch, not an update.
- Converted models (Clover) are converted by the source tree's converter
  from the pinned Hugging Face revision. `llm-local-servers.json` records
  the source, revision, converter and commit; `conversion.json` hashes
  every file. The conversion is deterministic: two separate conversions
  of the pinned revision produced identical files.
- Kapitsa clamps `--context` to `max_position_embeddings`. A positions
  override is a model fact (the base's native RoPE window) and is served
  through a view: symlinks to the pack and its own `config.json`. Never
  edit the pack.
- Ambient `NI_*` variables are dropped; a model's decode switches come only
  from `KAPITSA_ENGINE_ENV`. Clover decodes self-speculatively
  (`NI_CLOVER_DECODE=spec`) with threshold acceptance: exact acceptance
  and the 35B's DFlash2 drafter both fail audit fitness. Retest when a
  release changes Clover's decode modes.
- The KV pool is the KV room the engine plans at load, read from its
  launch log; `/v1/models` lists the whole catalog and the served model
  is the single `active` entry, with its slots and context.
- The SSD prefix cache is off by default so no run reads an earlier run's
  prompts. Turn it on for interactive use only.
- Validate with `make lint`, `make test`, and the full managed lifecycle
  on every configured model. Stop and verify release even on failure.
