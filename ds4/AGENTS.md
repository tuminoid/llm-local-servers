# ds4 runtime instructions

Root [AGENTS.md](../AGENTS.md) applies, with one declared exception: this
runtime is for interactive, large-model ("big brain") agentic use only.
The fleet has no hardware large enough to run audit campaigns on these
models, so they are never tuned for, ranked by, or promoted on audit
throughput, and AuditBench results here are diagnostics. Capability Check
v2 still runs and its failures are recorded.

Usage and knobs are in [README.md](README.md), measurements and verdicts
in [BENCHMARKS.md](BENCHMARKS.md).

## Invariants and retest conditions

- The pin is the source commit `DS4_COMMIT`; ds4 has no releases. The
  launcher refuses a build tree at another commit or with local changes.
  ds4's own Makefile needs GNU Make's built-in rules, so `install.sh`
  clears the `MAKEFLAGS` this repository's Makefile exports.
- Model identity is the HF cache blob name, which is the LFS sha256 of the
  pinned revision's file. Never use `download_model.sh`: it follows `main`
  and relinks `ds4flash.gguf`. The launcher always passes `-m`.
- `/v1/models` lists compatibility aliases after the loaded model (V4
  Flash also answers as `deepseek-v4-pro`). The first card must equal
  `DS4_SERVED_NAME`; alias ids can switch thinking off, so clients name
  the first.
- Declare every sampling key, `min_p=0` included: ds4 applies its own
  `min_p` 0.05 when a request omits it. Tool-call syntax decodes greedily
  regardless; argument values keep the request temperature.
- Speculation runs only at `--mtp-exact-sampling`; ds4's default accepts
  greedy drafts at any temperature. Enable it per model on measurement:
  built-in MTP helped Qwen and hurt GLM. V4 Flash's DSpark drafter stalled
  inside tool calls and is not wired. Retest after an MTP or DSpark change
  in ds4.
- Disk KV checkpoints stay on by default. ds4 does not rewind its live
  state to a common prefix, and a resent history that drops reasoning
  diverges from it, so without checkpoints each agent step can re-prefill
  the whole conversation. Retest: per-step `cached_tokens`, and
  `live kv cache miss` lines in the log.
- Checkpoints deliberately outlive a run, under the XDG cache rather than
  the run-scoped state directory: interactive sessions resume across
  restarts. Each model config gets its own directory and budget; the
  files hold prompt text. The server runs from the build tree, so the
  launcher rejects relative checkpoint and trace paths.
- A checkpoint records no RoPE scaling, and ds4 loads one saved at a
  smaller context (`ds4_kvstore.c` skips only larger ones). A change to a
  config's YaRN factor therefore needs its checkpoint directory cleared;
  the same text under different positions would load silently.
- The checkpoint budget is per config: one is saved every 20,480 tokens of
  a session, so the budget must hold a full-context chain of the model's
  checkpoint size, or deep checkpoints are evicted before their first hit.
- One slot by default. Concurrent sessions interleave prefill in 128-token
  chunks with decode and lost on every measured model.
- Metal kernels load relative to the build tree; `start.sh` changes into
  it before exec.
- ds4 has no `response_format`, so `json_schema` fails on every model.
  GLM tool arguments come back as strings. Retest both on a pin move.
- Validate with `make lint`, `make test` and the managed lifecycle for
  the changed config.
