# vLLM-Metal server

Script-managed [vLLM-Metal](https://github.com/vllm-project/vllm-metal)
server: the official community vLLM hardware plugin for Apple Silicon,
serving MLX-format models through vLLM's engine, scheduler, and
OpenAI-compatible API on Metal.

## Why this runtime

The Ollama MLX baseline (phase 1) measured two structural gaps on this
host: the MLX runner serializes every request through one slot, and
nothing bounds KV growth against physical memory -- a native-context
prefill exhausted 128 GB of unified memory and hard-reset the machine.
vLLM-Metal addresses both by construction: continuous batching with a
paged KV cache, and an up-front KV budget planned from
`--gpu-memory-utilization` at startup, so an unfittable context refuses to
start instead of taking the host down mid-prefill.

The M5 NAX prefill kernel (merged upstream 2026-08-19) engages
automatically on M5 GPUs for fp16/bf16 MHA/GQA/MQA prefill;
`VLLM_METAL_DISABLE_NAX=1` forces the tiled fallback for A/B comparison.
Hybrid GDN layers do not use it, so Qwen3.8-class models gain little --
that checkpoint is here as the same-model comparison against the Ollama
MLX baseline, not as the NAX showcase.

## Usage

```bash
make vllm-metal-install                        # pinned venv (one time)
make vllm-metal-pull  MODEL=qwen3.8-27b-4bit   # pinned model revision
make vllm-metal-start MODEL=qwen3.8-27b-4bit
make vllm-metal-status
make vllm-metal-bench MODEL=qwen3.8-27b-4bit
make vllm-metal-stop
```

The benchmark follows the shared
[AuditBench v1](https://github.com/tuminoid/llm-audit-bench)
protocol. It measures common 32k
audit calls, context-relative calls, decode scaling, and near-ceiling capacity.

The server binds `127.0.0.1:8021` (the port reserved for this runtime in
phase 0) with no authentication; do not expose it.

## Pinning

Everything is pinned in the root Makefile and verified by `install.sh`:

| Component | Pin |
| -- | -- |
| vllm-metal | `VLLM_METAL_VERSION`, wheel sha256 from the GitHub release |
| vllm | `VLLM_METAL_VLLM_VERSION`, the prebuilt macOS arm64 wheel, sha256 verified |
| mlx | 0.32.0 exact, declared by the plugin wheel (ABI-locked) |
| mlx-lm | git SHA declared by the plugin wheel |
| model weights | HF revision in `models/<name>.conf`, fetched by `pull.sh` |

Since 0.28.0 upstream numbers the plugin after its vLLM core version and
ships NAX prefill in stable releases (it was dev-only before, which is why
earlier pins were exact `v0.3.0.dev*` builds). The venv lives at
`~/.local/share/vllm-metal/venv` and is recreated from scratch on any pin
change; upstream's `curl | bash` installer is deliberately not used.

Model weights are downloaded with the authenticated `hf` CLI into
`~/.local/share/vllm-metal/models/<config-name>/` at the pinned revision.
The HF cache is treated as read-only and never served from.

## Memory policy

On unified memory the utilization fraction is the engine's whole footprint
budget, resolved against Metal's recommended working-set limit (~106 GB on
a 128 GB host). The default on hosts with 96 GB or more is 0.91 -- the
measured four-full-context operating point for qwen3.8 on the M5 Max:
a 1,061,760-token paged pool (4.05x a native 262,144 sequence), a 98 GB
footprint planned at startup, and ~28 GB left over, with memory pressure
nominal under load. The default admission cap is 5 sequences, the measured
decode sweet spot on that pool: 76-79 tok/s aggregate at ~15-16 tok/s per
stream, where 6 streams consistently measured *below* 5 and 8 trades
per-stream speed for a 84.7 peak. Five jobs stay preemption-free while
they average under ~212k tokens. Hosts below 96 GB default to 0.50 and
2 sequences.

The fraction buys KV capacity only: prefill and decode rates measured
identical at 0.60, 0.80, and 0.91. Lower it per run
(`VLLM_GPU_UTIL=0.6 make vllm-metal-start ...`) when running beside other
memory-heavy work; the engine plans the whole footprint up front and
refuses to start when a full-length sequence does not fit, so a wrong
value fails loudly at startup -- the phase-1 incident's mid-prefill host
reset is structurally impossible here.

Unlike the CUDA launcher there is no compute-capability or VRAM probing:
every Apple Silicon host takes the same code path, differing only in the
memory budget derived from `sysctl hw.memsize`.

## Prefix caching

`VLLM_PREFIX_CACHING` controls automatic prefix caching per run: `1`
opts in, `0` forces off, empty keeps the engine default (on for dense
models; for hybrid GDN models the resolved default depends on the core
version -- off at 0.27.1, where align-mode caching was opt-in and
experimental). Every model conf
pins its decided value explicitly so a core bump cannot silently change
the resolved mode: dense models pin `1` (their measured default),
qwen3.6 pins `1` (align-mode APC adopted 2026-08-26 for audit
workloads, see below), and the other hybrids pin `0`. The environment
override below still wins.

```bash
VLLM_PREFIX_CACHING=1 make vllm-metal-start MODEL=qwen3.6-35b-a3b-4bit
```

For hybrid GDN models the opt-in is not free. Align mode addresses
recurrent state by scheduler block, so every pool block carries a GDN
state slab besides its KV pages and the per-token pool cost roughly
doubles; the conf declares the effective figure as
`VLLM_KV_BYTES_PER_TOKEN_APC` and the launcher's utilization inversion
uses it, so the full-native-sequence budget stays honest. For
qwen3.6-35b-a3b-4bit that is 45,236,224 bytes per 1,056-token block
(21,626,880 KV + 21,463,040 state + 2,146,304 growth overlap, matching
the planner's breakdown line), 42,838 B/token: the computed utilization
rises from 0.46 to 0.71 and the pool lands at 1,325,112 tokens, keeping
five full 262,144-token sequences (5.05x admission).

Correctness was gated on 2026-08-24 with divergent conversations sharing
a 15k-token prefix at temperature 0: cold compute and cache-hit compute
are byte-identical in both directions (prefix cached by A then reused by
divergent B, and the reverse), across server restarts, and across 32k and
262k max-len configs. The measured win on that prefix is time to first
token 4.09 s cold against 0.11 s hot (36x); agentic clients that resend
the whole conversation each step (opencode/secaudit) get most of their
prefill back.

The opt-in is currently BLOCKED for serving and benchmarking: the
2026-08-24 decode smoke (plugin 0.3.0.dev20260819180958, vLLM 0.27.1)
found align-mode decode degrading deterministically with requests served
per process. A fresh APC server decodes 93.6/149.0/214.7 tok/s at 1/2/4
streams -- already ~21% under the cache-off control -- and decays to
65/88/149 within one three-sample family, to 26/45/82 after ~35
requests, roughly halving every ~20 requests. The curve reproduces
exactly on restart, does not recover without one, and is not thermal (a
cooled rerun on the same process continued from the degraded level).
The cache-off control is flat at 117/200/310 across the same cadence.
Root cause found upstream after this pin: PR #634 (merged 2026-08-21,
first in v0.3.0.dev20260821152549) replaced full recurrent-state-pool
copies on every update with an in-place Metal kernel. Correctness is
unaffected -- the gate above stands.

2026-08-26 retest at plugin v0.3.0.dev20260826100011 (same vLLM 0.27.1
and MLX 0.32.0): the decay is FIXED. APC-on decode held 101/171/257
then 99/167/255 tok/s (1/2/4) across two back-to-back smoke runs (~28
requests on one process) where the old pin had halved by ~20 requests.
The same-build cache-off control measured 119.6/202.0/316.1, matching
the historical control, so a flat align-mode cost of ~15-19% decode
remains -- the fix removed the decay, not the mode's price.

The pin was bumped to that build the same day and the gates re-ran on
the pinned venv: the divergent-conversation correctness gate re-passed
(byte-identical cold vs hit in both directions across a restart, TTFT
4.26 s cold vs 0.22 s hit on a ~10k shared prefix), the same-instant
pair probe passed 0/12, and capability-v1 passed on all three serving
profiles. qwen3.6 now serves with APC ON by default (its conf pins
VLLM_PREFIX_CACHING=1): for audit workloads that resend the whole
conversation each step, the warm-prefix TTFT win dominates the flat
decode cost. The cache-off canonical rates stay authoritative for
cache-off only; the APC operating point's own canonical run has since
been recorded in BENCHMARKS.md.

One standing caveat besides the block. Enabling align mode changes the
hybrid compute path itself: temp-0 outputs diverge from the cache-off
server starting at the first generated token (both variants are
internally deterministic and answered the factual probe correctly).
Because of it the cache-off and APC operating points each carry their
own canonical AuditBench run in BENCHMARKS.md; never quote one
condition's rates for the other.

2026-09-03 re-gate at plugin 0.28.0 (the first stable release; upstream
renumbered the plugin after its vLLM core version and deleted the dev
channel; paired core vLLM 0.28.0, MLX 0.32.0 unchanged): decode smoke
flat with no per-request decay -- qwen3.8 APC 28.7/51.9/81.5 tok/s and
qwen3.6 APC 97.7/164.9/252.8 tok/s at 1/2/4 streams, both within ~2% of
the dev-pin figures. The divergent-conversation correctness gate
re-passed (byte-identical cold vs hit in both directions across a
restart, TTFT 4.2 s cold vs 0.26 s hit), the same-instant pair probe
passed 0/12, and capability-v1 passed on all three serving profiles.
Cold 32k prefill spot-checks (the NAX path) also measured within ~3%
of the canonical rows on all three profiles: qwen3.8 567-602 tok/s
(canonical 569.9), qwen3.6 2,814-2,979 (2,823.8), gemma4 342-366
(363.5); qwen3.8 additionally matched its 64k row at 445-461 (457.6).
The dev-pin canonical tables in BENCHMARKS.md therefore carry over
unchanged.

## Runtime state

Pidfile and log live in `~/.local/state/vllm-metal/` and are scoped to one
run: start truncates the log, a clean stop removes it, and a failed
startup or teardown preserves it as evidence. Teardown is verified by the
emptied process group -- on unified memory the process group owns the Metal
allocations, so an empty group is the release proof.
