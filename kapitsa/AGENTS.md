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
| `runtime.py` | Lifecycle, model conversion and verification, identity |
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
- Models are converted by the source tree's converter from the pinned
  Hugging Face revision. `llm-local-servers.json` records
  the source, revision, converter and commit; `conversion.json` hashes
  every file. The conversion is deterministic: two separate conversions
  of the pinned revision produced identical files.
- Kapitsa serves only Clover. Its Qwen3.6-35B-A3B and Qwen3.8-27B catalog
  profiles (DFlash2 drafters) passed Capability Check v2 but lost to Splash
  on sessions/h (16.28 against 20.29, 6.65 against 8.01) and were dropped
  on 2026-10-29; reconsider with a release that moves those numbers.
- Kapitsa clamps `--context` to `max_position_embeddings`. A positions
  override is a model fact (the base's native RoPE window) and is served
  through a view: symlinks to the pack and its own `config.json`. A
  generation-config override (`KAPITSA_GENERATION`) goes the same way into
  the view's `generation_config.json`, and only for keys the pack has. The
  view is derived, so start rewrites it. Never edit the pack.
- Clover's end-of-reply ramp counts reasoning tokens and, at the
  checkpoint's strength, ends deep audit replies at about 16K with their
  thinking open, so the conf turns it off. Without it, the `</think>` ramp
  at the checkpoint's strength lets thinking loop to the client's output
  limit; doubled at the checkpoint's 4,096 start it cuts thinking to 8K and
  the model loops on tool calls instead. The conf doubles it and starts it
  at 16,384. Retest with a checkpoint revision that changes either ramp.
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
