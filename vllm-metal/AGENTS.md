# vllm-metal/

Script-managed vLLM-Metal server (Apple Silicon). User-facing usage and the
memory rationale live in [README.md](README.md); shared server conventions
live in [../AGENTS.md](../AGENTS.md).
Serving measurements follow
[AuditBench v2](https://github.com/tuminoid/llm-audit-bench).

## File inventory

| File | Role |
| -- | -- |
| `lib.sh` | Paths, venv-only binary resolution, pid, memory helpers |
| `install.sh` | Pinned venv from checksum-verified release wheels |
| `pull.sh` | Pinned-revision model download via the host's hf CLI, else the venv's |
| `start.sh` | Foreground launcher and host memory policy |
| `run.sh` | Detached launcher and readiness wait |
| `status.sh` | Process, KV sizing, NAX evidence, footprint, live API probe |
| `bench.py` | vLLM-Metal adapter for shared AuditBench v2, including exact config and resolved host-profile provenance |
| `capability.py` | OpenAI-compatible adapter for shared Capability Check v2 |
| `battery-gate.sh` | AuditBench sample gate: charge floor plus 140 W adapter contract |
| `stop.sh` | Process-group teardown and release verification |
| `models/*.conf` | Portable model facts: repo, revision, context, parsers, KV cost |
| `Makefile` | Guard with no runnable targets |

## Invariants

- Run every operation through a root Makefile target.
- The venv, model weights, pidfile, and log all live outside the repository.
- `vllm_metal_bin` accepts only the `VLLM_METAL_BIN` override or the managed
  venv. Never fall back to a PATH `vllm`: that is the CUDA install or the uv
  tool wrapper, and it would serve without the Metal plugin.
- All pins live in the root Makefile: the exact plugin release tag, its
  wheel sha256, and the sha256 of the prebuilt macOS arm64 wheel for the
  matching vLLM core version. `install.sh` refuses unverified wheels
  and recreates the venv from scratch on any pin change. Do not use
  upstream's `curl | bash` installer; it writes an unpinned user-global
  venv.
- The plugin wheel ABI-locks an exact mlx release (its prebuilt
  `_paged_ops.so` links MLX private headers). A pin bump means bumping the
  plugin wheel, never overriding mlx independently.
- Model weights are served from `pull.sh`'s explicit per-config directory
  at a pinned HF revision. `start.sh` refuses to start when the directory
  is missing rather than letting vLLM download implicitly; the HF cache is
  read-only. Before AuditBench, `bench.py` also checks the Hugging Face
  metadata for config, tokenizer, chat template, index, and every weight shard;
  all served files must name the configured revision.
- Keep the server on loopback port 8021 (phase 0 reservation). 8000 is the
  CUDA vLLM server and 8001 its tunnel.
- The memory budget default at >= 96 GiB is 0.91 with 5 admitted
  sequences: the measured four-full-context pool for the retired qwen3.8
  8-bit checkpoint on the 128 GB M5 Max (1,061,760 tokens, 98 GB
  footprint, ~28 GB left, pressure nominal; BENCHMARKS.md at `a7e8f3f`),
  and the measured decode sweet spot on it (5 streams beat both
  4 and 6; 6 measured consistently below 5 -- a batch-shape effect, so do
  not "round up" the cap without re-measuring).
  Below 96 GiB the default is 0.50 with 2 sequences. The fraction resolves
  against Metal's ~106 GB working-set limit and buys KV capacity only --
  rates measured identical at 0.60, 0.80, and 0.91. vLLM plans the paged
  KV pool from it up front and refuses an unfittable `--max-model-len` at
  startup; that loud refusal is the property this runtime was chosen for.
  Override down per run when co-tenanting with memory-heavy work.
- `max-num-seqs` is admission only, never memory-aware: the fifth job
  waits even when the resident four are tiny. Memory is governed by the
  fixed pool plus recompute preemption, so over-admitting long jobs costs
  a re-prefill, not a failure; per-request context is never reserved, only
  consumed as used, capped by `--max-model-len` per request.
- Model configs are portable model facts only (repo, revision, served
  name, native context, parsers, paged-KV bytes per token from the
  architecture). Utilization, sequence count, batch size, bind address,
  and port are host policy in `start.sh`. When a config declares
  `VLLM_KV_BYTES_PER_TOKEN`, the launcher computes the utilization that
  fits `max-num-seqs` full-native-context requests (weights measured from
  the pulled directory, Metal limit queried from MLX, flat 5 GB engine
  overhead), rounded up to the next 0.01 and clamped to the host cap; an
  explicit `VLLM_GPU_UTIL` still wins.
- Prefix caching is a pinned per-model operating point: every conf sets
  `VLLM_PREFIX_CACHING` explicitly, because vLLM main resolves supported
  hybrids to align-mode APC ON and an unset knob would flip silently on
  a core bump. Dense models pin `1` (their measured default). Hybrid
  confs that passed the align gate pin `1`: align-mode APC was adopted on
  the qwen3.6 profile (dropped on 2026-10-12; see README.md) after the
  plugin pin moved to dev20260826100011, whose PR #634 fixed the decode decay that
  blocked it (gates re-passed on every pinned venv since, most recently
  0.28.0: byte-identical cold-vs-hit correctness, 0/12 same-instant
  bails, capability-v1). The environment still wins over the conf;
  `1` opts in, `0` forces off, empty (a conf without a pin) keeps the
  engine default. A hybrid conf that opts in must also declare
  `VLLM_KV_BYTES_PER_TOKEN_APC` (align mode makes every pool block carry
  GDN state; 1-3% more per token on plugin 0.30.0) or the utilization
  inversion under-budgets the pool. Align mode changes hybrid temp-0
  outputs from the first token, so cache-off canonical benchmark rates
  do not transfer to an APC profile -- each condition carries its own
  canonical run in BENCHMARKS.md; gate and math are in README.md.
  Rerun a session smoke (`make vllm-metal-bench MODEL=<conf>
  AUDIT_BENCH_STREAMS=1 AUDIT_BENCH_SAMPLES=1`, noncanonical) on every
  plugin bump.
- Parsers are explicit per model, as on the CUDA side: vLLM auto-detects
  neither. Qwen3.5-family checkpoints use `qwen3` reasoning and
  `qwen3_xml` tool parsers; the response field is `message.reasoning`.
- A model whose template re-renders past reasoning declares
  `VLLM_PRESERVE_REASONING=1`. `bench.py` and `capability.py` both forward
  it; the capability adapter builds its own `CapabilityConfig`, so the
  harness's `CAPABILITY_PRESERVE_REASONING` alone never reaches it.
- Stop by the recorded process group, never a command-line pattern. macOS
  has no `setsid`; `run.sh` falls back to bash job control for the
  detached process group, and the emptied group is the unified-memory
  release proof.
- The log is scoped to one run: truncated at start, removed on a clean
  stop, preserved when startup or teardown failed.
- NVFP4 safetensors did not load with an mlx-lm no newer than plugin
  0.28.0's (0.31.3): unsloth/Qwen3.8-27B-NVFP4 failed engine init with 937
  unmapped parameters (mlx-lm had no NVFP4 block-scale weight mapping),
  and the verdict transfers to nvidia/Qwen3.6-35B-A3B-NVFP4 -- same
  format. mlx-lm has moved since without a retest here; do not re-add an
  NVFP4 profile until one passes. The Ollama registry is the only NVFP4
  path on this host. Expect and accept loud load failures; never paper
  over one with a dequantizing fallback.
- Serving is text only: `start.sh` always passes `--language-model-only`,
  so a multimodal checkpoint's image processor is never built and its
  processor files (broken or absent in several MLX conversions) are never
  read. Image and video requests are rejected.
- `start.sh` refuses a venv whose installed vllm-metal or vllm version
  differs from the Makefile pins, which `vllm-metal-start` passes. Start
  never installs; a pin bump is complete only after `make
  vllm-metal-install` has rebuilt the venv.

## Verification

```bash
make lint
make vllm-metal-install
make vllm-metal-pull  MODEL=ornith1.5-35b-a3b-4bit
make vllm-metal-start MODEL=ornith1.5-35b-a3b-4bit
make vllm-metal-status      # host line, KV sizing, NAX evidence
make vllm-metal-capability MODEL=ornith1.5-35b-a3b-4bit
make vllm-metal-bench MODEL=ornith1.5-35b-a3b-4bit
make vllm-metal-stop        # must report the process group empty
```

Also send one real streaming request and one structured tool call, and
confirm `message.reasoning` is populated with no `</think>` in content.
AuditBench's session runs provide the batching evidence at 1x and the
serving concurrency. Its near-context phase runs 1x and the highest canonical
stream count that fits active admission and the pool, and is the context and
aggregate-capacity proof; every request must land between 90% and 100% of
`VLLM_MAX_LEN`. Publish only a canonical result.
