# Ollama benchmark results

Measured throughput, memory, context, and concurrency baselines for the
script-managed Ollama deployments on the hosts below.

Use each host's operating-point table for its measured hardware. The later
sections preserve the measurements and memory explanations behind those
recommendations.

The RTX PRO 3000 and A100 rows use canonical
[AuditBench v1](https://github.com/tuminoid/llm-audit-bench).
The Apple operating-point tables use the retired
runtime-specific harness; the Apple AuditBench v1 sections (Nemotron,
the qwen3.6 NVFP4 pair, and the conversation profile) are canonical and
dated per section. Retired A100 measurements remain clearly separated
later in this file and must not be combined with canonical rates.

## RTX PRO 3000 Blackwell laptop GPU operating points

Host: RTX PRO 3000 Blackwell laptop GPU with 12,227 MiB VRAM, Intel Core Ultra
9 285H, 62 GiB RAM, and no swap. All rows use Ollama 0.32.14, Flash Attention,
and q8 KV. Canonical AuditBench v1 ran with the
full profile and three measured samples. Only retained operating points are
shown: redundant Gemma slot counts, Nemotron, and native-context Qwen3.8 are
not part of this inventory.

Capacity is one proof sample. Input rate is aggregate prompt tok/s. Ollama
exposes an allocated context per effective slot, not a fungible KV pool.

| Profile | Context/request | Slots | Aggregate context | Allocation CPU / GPU | Near-context capacity proof |
| -- | --: | --: | --: | --: | -- |
| Qwen3.5 4B | 131,072 | 1 | 131,072 | 0.00 / 6.04 GiB | 1 x 122,861 in 84.87s at 1,447.7 tok/s |
| Gemma 4 E2B | 131,072 | 4 | 524,288 | 0.00 / 2.66 GiB | 1 x 122,903 in 56.73s at 2,166.4 tok/s; 4 x in 217.03s at 2,265.2 tok/s |
| Qwen3.5 9B | 262,144 | 1 | 262,144 | 0.00 / 10.21 GiB | 1 x 245,752 in 311.57s at 788.7 tok/s |
| Gemma 4 12B | 262,144 | 1 | 262,144 | 0.00 / 7.96 GiB | 1 x 245,777 in 462.12s at 531.9 tok/s |
| Qwen3.6 35B-A3B | 262,144 | 1 | 262,144 | 14.53 / 10.21 GiB | 1 x 245,752 in 927.94s at 264.8 tok/s |
| Qwen3.8 27B | 131,072 | 1 | 131,072 | 12.49 / 7.64 GiB | 1 x 122,861 in 745.62s at 164.8 tok/s |

Performance cells are median tok/s followed by `[min-max]`. Prefill output is
one token; decode output is exactly 1,024 tokens per stream.

| Profile | 32k prefill | 64k prefill | 128k prefill | Decode 1x | Decode 2x | Decode 4x |
| -- | --: | --: | --: | --: | --: | --: |
| Qwen3.5 4B | 2,057.6 [1,799.6-2,245.8] | 1,970.4 [1,884.9-2,017.9] | - | 67.43 [61.69-68.75] | - | - |
| Gemma 4 E2B | 3,582.5 [3,522.8-3,587.2] | 2,971.1 [2,903.0-2,971.3] | - | 110.35 [96.62-112.55] | 184.07 [158.29-188.40] | 247.40 [240.31-252.47] |
| Qwen3.5 9B | 1,654.8 [1,631.6-1,766.6] | 1,518.9 [1,486.5-1,525.8] | 1,139.2 [1,134.3-1,142.6] | 37.83 [31.73-38.58] | - | - |
| Gemma 4 12B | 1,242.8 [1,227.5-1,246.7] | 1,042.9 [1,024.8-1,044.7] | 767.4 [762.0-769.8] | 32.36 [31.07-32.73] | - | - |
| Qwen3.6 35B-A3B | 303.4 [295.5-303.7] | 299.1 [297.9-302.4] | 288.4 [286.5-288.4] | 30.99 [28.35-31.15] | - | - |
| Qwen3.8 27B | 188.3 [182.9-198.1] | 178.3 [176.9-179.7] | - | 2.93 [2.69-3.42] | - | - |

Qwen prompt counts were 32,780, 65,547, and 131,071 where included; Gemma
counts were 32,779, 65,535, and 131,058. Decode control prompts were 66 tokens
for Qwen and 76 for Gemma.

Audit cells are median calls/hour followed by `[min-max] / median output
tok/s`. The 32k and half-context phases generate 1,024 tokens; deep generates
256.

| Profile | Audit 32k 1x | Audit 32k 2x | Audit 32k 4x | Audit half 1x | Audit deep 1x | Audit deep max |
| -- | --: | --: | --: | --: | --: | --: |
| Qwen3.5 4B | 100.55 [100.25-105.47] / 28.60 | - | - | 59.19 [56.97-60.11] / 16.84 | 41.92 [41.56-42.19] / 2.98 | 1x |
| Gemma 4 E2B | 171.85 [165.90-182.62] / 48.88 | 179.66 [157.69-187.89] / 51.10 | 184.88 [181.99-197.10] / 52.59 | 99.42 [96.27-99.88] / 28.28 | 67.33 [65.52-68.46] / 4.79 | 4x: 64.57 [64.53-65.11] / 4.59 |
| Qwen3.5 9B | 70.34 [69.14-73.91] / 20.01 | - | - | 22.10 [22.09-22.24] / 6.29 | 12.26 [12.23-12.36] / 0.872 | 1x |
| Gemma 4 12B | 59.82 [59.53-60.60] / 17.01 | - | - | 16.67 [16.28-16.75] / 4.74 | 8.31 [8.31-8.43] / 0.591 | 1x |
| Qwen3.6 35B-A3B | 25.09 [25.07-25.14] / 7.14 | - | - | 7.00 [6.96-7.11] / 1.99 | 4.00 [4.00-4.00] / 0.284 | 1x |
| Qwen3.8 27B | 2.70 [2.31-2.86] / 0.769 | - | - | 1.83 [1.69-1.87] / 0.521 | 2.15 [1.96-2.30] / 0.153 | 1x |

The serving-performance recommendation is:

- Gemma 4 E2B is the throughput leader and the only retained concurrent
  Ollama point. Four streams reach 247.40 decode tok/s and 184.88 cold-32k
  calls/hour, while one stream is better for deep audits.
- Qwen3.5 4B is the fastest retained one-slot 128k profile and the direct
  comparison with local vLLM.
- Qwen3.5 9B is the fastest fully GPU-resident 262k profile. It beats Gemma
  12B at every AuditBench audit phase.
- Gemma 4 12B remains the retained larger-model Gemma point at one slot.
  Higher slot counts force CPU offload and are not useful baselines here.
- Qwen3.6 is a model-capability choice. The runner reports 41 of 42 layers on
  GPU, but byte allocation is 14.53 GiB CPU plus 10.21 GiB GPU and its audit
  throughput is far below the fully resident 9B model.
- Qwen3.8 at 128k is host-memory bound: decode falls to 2.93 tok/s and the
  32k audit reaches only 2.70 calls/hour. The 262k profile is not retained.

All Qwen profiles are forced to one slot by Ollama's `qwen35` or `qwen35moe`
architecture guard. These recommendations describe serving performance and
capacity only; they do not establish answer quality.

### Audit conversation and replay (clean fixture)

Canonical clean-fixture runs on the GPU-resident RTX profiles,
conversation and replay. The earlier overnight conversation runs at
`bf27151` predate fixture finalization and are superseded: the qwen3.5
variant collapses (number-sequence runaways, a 333 s think-then-quit)
were the planted decode-control, since fixed; those JSONs remain
retained only as fixture-bug evidence. Ollama exposes no prefix-caching
switch and its OpenAI-compatible endpoint reports no `cached_tokens`,
so every row runs the runtime's implicit llama.cpp slot prefix reuse --
visible only in per-turn walls, never as a measured fraction.

| Profile | Steps | Compliant | Wall | Conv/h | Replay wall | Replays/h |
| -- | --: | -- | --: | --: | --: | --: |
| Qwen3.5 4B | 9 | 1 of 2 | 159.0 s | 22.6 | 907.4 s | 3.97 |
| Qwen3.5 9B | 16 | 3 of 3 | 367.1 s | 9.8 | 1,659.0 s | 2.17 |
| Qwen3.6 35B-A3B | 16 | 1 of 2 | 818.8 s | 4.4 | not run | - |
| Gemma 4 12B | 16 | 0 of 2 | - | - | 1,430.2 s | 2.52 |
| Gemma 4 E2B (4 slots) | 9 | 0 of 2 | - | - | 172.7 s | 20.85 |

Conversation walls and rates come from compliant samples only; replay
includes the forced 16,384-token verdict decode, which dominates the
wall at these decode rates (verdict tok/s at depth: 4B 20.4, 9B 11.7,
12B 15.4; the E2B ignored the never-conclude control and self-stopped
its verdict near 4k tokens, recorded via `verdict_completion_tokens`).
Per profile:

- Qwen3.5 9B is the only RTX profile compliant on every sample: full
  16-step chains to 164,503 tokens with 16/16 recall, resending
  1,679,839 prompt tokens per conversation with flat per-turn walls.
- Qwen3.5 4B remains variant-split on the clean corpus: one sample ran
  9/9 with full recall, the other read one file and issued a premature
  one-finding verdict -- a graceful miss, not the old runaway. The
  same checkpoint under local vLLM is 2/2 compliant cache-off and
  runaway-broken under align APC (see ../vllm/BENCHMARKS.md), so cache
  mode and serving stack both move this knife edge.
- Gemma 4 12B follows the chain and then declares "The audit is
  complete" early (13/16 and 8/16 files), dropping findings it did
  read. Gemma 4 E2B reads a filename embedded in the evidence text
  instead of `file_001`, in both stacks. Both behaviors survive the
  corpus fix: genuine model limits, cleanly attributed.
- Qwen3.6 35B-A3B ran on the finalized fixture after an
  identity refusal was resolved: this host held an artifact
  (`07d35212...`) pulled before the digest pin was recorded
  (`096fdbd0...`). A re-pull fetched exactly the pinned digest (the
  tag had not moved since the pin) and pruned the old layers, so the
  canonical RTX rows above for this profile -- measured on the older
  artifact -- describe a digest no longer present locally. On the
  pinned artifact the compliant variant ran
  the full 16-step chain with 16/16 recall at ~40 s per tool turn
  despite the 14.53 GiB CPU offload; the other variant produced a
  graceful near-miss (15/16, verdict one file early). Its replay and
  Qwen3.8 27B (2.93 tok/s decode) await a separately approved
  CPU-offload batch.

Run JSONs: `~/tmp/auditbench-conv-rtx/`.

## Apple M5 Max MLX operating points

Host: MacBook Pro `Mac17,6`, Apple M5 Max, 40 GPU cores, 128 GB unified
memory, macOS 26.6.2 (25G83), on external power. All rows use the managed
official Ollama 0.32.14 (`ollama-darwin.tgz`), whose MLX runner loaded the
`mlx_metal_v4` backend (MLX 0.32.0-213-gadf21de, device gpu) -- the Metal 4
path on M5. Both models are safetensors NVFP4 registry artifacts dispatched
to the MLX runner; KV cache is MLX-native model precision, not q8. Each
operating point is one full sample after a warmup load.

The MLX runner serializes requests through a single slot, so all rows are
jobs=1. Two concurrent clients measured 1.91x single-request wall time and
four measured 4.08x, each with unchanged per-request eval rate and
staircase completion times -- queueing, not batching. Concurrency against
this server is therefore worth nothing beyond queueing convenience; the
operating points below are single-stream maxima.

Contexts are the measured per-model maxima from supervised runs with a
memory watchdog, not round numbers: Qwen3.6 completed its full native
ceiling, while Qwen3.8 tops out at 184,320 with essentially no headroom
(~123 GB of 128 GB system-wide at peak) -- run it near the ceiling only on
an otherwise quiet host, and override down to the wide-margin 131,072 when
working beside it. Allocation is the `/api/ps` value; peak is the runner's
own logged MLX active+cache high-water mark during the near-full-context
prefill.

| Profile | Context/request | Allocation CPU / GPU | Peak MLX | Decode | Near-full proof |
| -- | --: | --: | --: | --: | -- |
| Qwen3.6 35B-A3B coding NVFP4, 1 job | 262,144 | 0.00 / 20.51 GiB | 48.62 GiB | 122.58 tok/s | 246,096 tokens in 4m 34s |
| Qwen3.8-27B NVFP4, 1 job | 184,320 | 0.00 / 17.22 GiB | 92.78 GiB | 72.26 tok/s | 173,041 tokens in 8m 13s |

Prefill at the maximum contexts (14,187-token short prompt, half of and
near the configured ceiling, all tokenizer-reported):

| Profile | Short | Half context | Near ceiling |
| -- | --: | --: | --: |
| Qwen3.6 35B-A3B coding NVFP4 | 4,076.5 tok/s | 1,384.7 tok/s (130,920 tok) | 897.9 tok/s (246,096 tok) |
| Qwen3.8-27B NVFP4 | 827.0 tok/s | 496.0 tok/s (92,058 tok) | 350.6 tok/s (173,041 tok) |

### Nemotron 3.5 Lightning 30B-A3B MLX -- AuditBench v1 canonical

Measured at repository commit 446f840 with the finalized
output-control prompt on the managed 0.32.14 MLX runner: context 262,144
(the proven launch default), safetensors NVFP4 artifact at identity digest
`8b1474be6e54`, 140 W adapter contract verified, battery 90%, battery gate
active. KV cache type mlx-native; `/api/ps` allocation 0.00 / 21.19 GiB
GPU at short context, 30.8 GiB during the deep-context phases. Medians
from three samples; the capacity proof runs once. The MLX runner
serializes this architecture to one slot, so every arm is single-stream
and the concurrent points are unsupported, not unmeasured.

| Phase | Streams | Result |
| -- | -- | --: |
| Prefill 32,769 | 1 | 4,039.8 tok/s |
| Prefill 65,539 | 1 | 3,072.1 tok/s |
| Prefill 131,079 | 1 | 2,627.7 tok/s |
| Capacity 245,773 | 1 | passed, 1,929.6 tok/s, 127.4 s |
| Decode | 1 | 141.7 tok/s |
| audit_32k calls/hour | 1 | 212.8 |
| audit_half (131k) calls/hour | 1 | 58.3 |
| audit_deep (229k) calls/hour | 1 | 31.1 |

The depth economics are the Mamba/attention hybrid showing through: only
6 of 52 layers attend, so prefill falls just 2.1x from 32k to the 245,773
capacity proof where Qwen3.6 coding falls 4.5x over the same span, and the
near-full ingest completes in 127.4 s against that profile's 274 s. The
audit cadence (212.8 / 58.3 / 31.1 calls/hour) leads every canonical
profile on this host at every depth, single-stream against their best
measured concurrency. Capability gating for this artifact is recorded in
[../CAPABILITIES.md](../CAPABILITIES.md); the run JSON is retained
outside the repository.

### Qwen3.6 35B-A3B NVFP4 base and coding -- AuditBench v1 canonical

Measured at repository commit `98f9b2c` with the finalized
output-control prompt on the managed 0.32.14 MLX runner, at the
131,072-token operating point both confs pin since the native-262k hard
reset below. Identity digests `e92a3e94bbca` (base) and `cd2692a833e6`
(coding, the re-pulled manifest), 140 W adapter contract, battery 100%,
battery gate active, dedicated server lifecycle per profile. Single
slot (the runner forces this architecture to one), so every arm is
single-stream. At this context the plan's prefill rows stop at 65,536
and the depth targets scale down with it: audit_half is 65,547 and
audit_deep 114,689 prompt tokens, so these depth labels are NOT
comparable to the 262,144-context profiles' 131k/229k targets.

| Phase | Base NVFP4 | Coding NVFP4 |
| -- | --: | --: |
| Prefill 32,780 | 3,190 tok/s | 3,242 tok/s |
| Prefill 65,547 | 2,224 tok/s | 2,305 tok/s |
| Capacity 122,861 | passed, 84.7 s | passed, 78.8 s |
| Decode | 140.8 tok/s | 126.7 tok/s |
| audit_32k calls/hour | 188.7 | 180.4 |
| audit_half (65k) calls/hour | 91.2 | 88.5 |
| audit_deep (114.7k) calls/hour | 47.7 | 48.7 |

The two digests are rate-identical within a few percent -- the coding
manifest's earlier operating-point numbers (measured on retired digest
`e839e5321a76`) carry over to its replacement in shape, and the
131,072 point is now depth-proven on both current digests (the capacity
row is exactly the supervised depth-probe territory that the night
chain died in at 262,144). Against the vLLM-Metal qwen3.6 4-bit
canonical at the same 32k depth, one NVFP4 MLX stream (188.7/h) beats
that profile's best four-stream rate (110.8/h) by 1.7x. At matched
~115-131k depth Lightning remains the host's depth leader: 58.3
calls/hour at 131k versus 47.7 at 114.7k here. Run JSONs and preserved
server logs are retained outside the repository.

### The native-262k hard reset

The first Qwen3.8 NVFP4 run used the checkpoint's native 262,144 context.
Short prefill (810.0 tok/s), half-context prefill (130,920 tokens at 417.4
tok/s, peak 49.23 GiB), and decode (73.66 tok/s) completed, but the
246,085-token near-ceiling prefill exhausted 128 GB of unified memory at
about 192,512 processed tokens and hard-reset the machine. The retained
panic log (`panic-full-2026-08-20-131217`) shows a system watchdog panic --
`watchdog timeout: no checkins from watchdogd in 93 seconds` -- not a GPU
driver fault: the runner's wired limit had been sized for the 16.91 GiB
model only, so KV growth was ordinary pageable memory, and starvation
stalled userspace until the watchdog fired.

The same failure class is public in the MLX ecosystem: `mlx_lm.server`
wires ~75% of system RAM and ships no server-side KV bound
(ml-explore/mlx-lm issue 883), where the end state is an
`IOGPUMemory.cpp` kernel panic instead because Jetsam never sees wired
memory as pressure. Reports of that issue claim Ollama's fixed context
prevents it; this incident shows the bound only protects when the
configured context itself fits in physical memory. Ollama enforces
`num_ctx` logically and nothing checks it against RAM at load time.

The maxima above were then found with supervised runs: a watchdog sampled
available memory every 2 s and would kill the server's process group below
an 18 GiB floor. Qwen3.6 passed its full native ceiling; Qwen3.8's
184,320 pass had no room left above it. Raising a context above a profile
default is that kind of supervised experiment, per model -- on unified
memory the failure mode is the whole machine, not an OOM-killed server
process, and headroom never transfers between models.

### The re-pulled manifest hard reset

The same failure recurred on the CODING variant after its registry tag
moved: the replacement manifest (digest `cd2692a833e6`), run unsupervised
at the old 262,144 operating point during a canonical AuditBench attempt,
exhausted unified memory during a 131k-token prefill sample -- roughly
half the depth the OLD manifest had proven to 246,096 tokens at a
48.62 GiB peak. The panic log (`panic-full-2026-08-26-070253`, watchdog
timeout, 721 free pages at death) matches the qwen3.8 incident exactly.
Two lessons harden the rule above: depth proofs belong to a manifest
DIGEST, not a tag -- a repin voids every prior memory proof -- and an
overnight canonical run is not a supervised experiment. Both qwen3.6
NVFP4 profiles now launch at 131,072. The night's benchmark
outputs also died with the machine: they were written under /tmp, which
macOS clears on boot -- benchmark output belongs under the retained
campaign state directory, never /tmp.

Same-day supervised probes (memory watchdog armed, stepped
needle prefills at 49k/90k/128k) proved the 131,072 operating point on
BOTH current digests. The base artifact (`e92a3e94bbca`) completed a
127,975-token prefill at a 26.6 GiB peak; the coding artifact
(`cd2692a833e6`) completed 127,986 tokens at a 23.7 GiB peak -- the very
digest and depth that killed the host the night before, now clean under
the smaller allocation. Measured KV growth is linear (~37 KiB/token) and
projects a trivial 262k fit, which is exactly the math the crash
falsified. Probe rates (MagSafe 140 W, indicative, not canonical): at
~128k depth, base prefill 1,632 tok/s / decode 58.6 tok/s; coding
prefill 1,932 tok/s / decode 69.5 tok/s. Canonical AuditBench runs for
both remain owed.

A controlled repro the same morning then isolated the mechanism. Under
the 262,144 allocation, single deep prefills are NOT the trigger: a
fresh process walked 1k/16k/32k/64k/70k/90k/110k/120k/130k -- straight
through the fatal ~127k depth -- cleanly. The killer is repeated
distinct deep prefills on one process: each ~130k request retained
2-3.4 GiB that was never released (identical repeats are masked by the
prompt cache and must be busted with a unique prefix), and on the third
cache-busted 130k prefill growth went vertical -- free memory fell
19.5 GiB to 2.3 GiB in a single 0.5 s sample, a ~17 GiB instantaneous
allocation mid-prefill. The probe watchdog killed the process group on
the first tick below its 12 GiB floor and the host survived; the night
run had no watchdog, and AuditBench's three-samples-per-depth structure
is exactly this shape, so sample repetition -- not the fatal sample's
own depth -- exhausted the machine. Two operational facts fall out:
kernel memory-pressure level stayed "normal" through the entire runaway
(a free-page floor is the only early warning that works), and the
131,072 allocation is immune in the same experiment (nine distinct
prefills to near-ceiling, no runaway, retention stabilized). Both NVFP4
tags share one config blob (hybrid GDN: 30 linear + 10 full-attention
layers, fp32 SSM state), so the 262,144 ban applies to both digests
equally. The old manifest's config is unrecoverable (registry dropped
the digest-addressed manifest, the local copy was overwritten, and the
crash-era server log was truncated on restart), so why the OLD digest
served 262k to 246k tokens remains open; the retest hook is the next
Ollama pin bump.

API correctness was verified at the operating points: streaming reasoning
(separate `thinking`/`reasoning` fields, native and OpenAI APIs), structured
single tool calls on both models, and a multi-turn tool loop on Qwen3.8.
Qwen3.6's NVFP4 manifest does not declare the `tools` capability, but
structured tool calls work through the qwen3.5 parser.

Registry identity update: the
`qwen3.6:35b-a3b-coding-nvfp4` tag moved from manifest
`e839e5321a76` to `cd2692a833e6`. The replacement remains safetensors NVFP4
at native 262,144 context and passed Capability Check v1, including tools.
The 262,144-context operating-point rates above remain evidence for the
earlier artifact only; the current digests carry their own canonical
rates at the 131,072 operating point (canonical section above).

### Muse Glimmer 30B MLX smoke

`muse-glimmer:30b-mlx` (safetensors mixed-precision, ~21 GiB, dispatched to
the MLX runner) passed its three-gate smoke on the managed 0.32.14 pin:
model registration, a chat request with the reasoning channel populated
under a `Reasoning strength: low` system prompt, and a clean structured
`get_weather` tool call through the OpenAI-compatible API. Full lifecycle
verified including stop with an empty process group.

That smoke predates the tag's current manifest. The registry has since
moved `muse-glimmer:30b-mlx` from `3d5c4b80e60b` to `ef32a55b4976`; the new
NVFP4 manifest packages DFlash assistant weights and passed Capability Check
v1. No performance or DFlash speedup number transfers from the earlier smoke.

Operating facts from the smoke, not a benchmark: 19.83 GiB GPU allocation
at the native 131,072 context, 100% GPU; a single short probe measured
54.8 tok/s decode and 317 tok/s short-prompt prefill (tiny prompt,
indicative only). Caveats: no near-ceiling proof run yet (the MLX
per-model maximum rule applies), the registry's `-dflash` tag resolved to
the same blob as this tag at research time (ollama/ollama#17683) so no
DFlash speedup is claimed, and no AuditBench canonical exists. It
remains a candidate outside the canonical serving set.

The GGUF sibling (`muse-glimmer:30b`, Q4_K_M, llama.cpp runner, q8 KV,
Flash Attention) answered the concurrency question the MLX runner cannot:
this architecture is **not slot-forced**. With short prompts and 200
output tokens, parallel=2 ran both requests to simultaneous completion at
1.43x the single wall (20.9 tok/s per stream, 41.8 aggregate vs 30.0
single) and parallel=4 at 2.17x (13.9 per stream, 55.7 aggregate) --
genuine overlap, not the Qwen staircase. The server accepted 131,072
tokens per slot at both parallelisms and stayed fully GPU-resident at
17.28 GiB, so llama.cpp is honoring the model's 2048-token sliding window
rather than allocating dense per-slot KV. The two artifacts split the
workload cleanly: the MLX runner wins single-stream latency (54.8 vs 30.0
tok/s), while the GGUF's 4-slot aggregate (55.7) edges past the MLX
runner's single-stream ceiling. Multi-slot behavior near full context is
unproven; per-slot maxima are measured, never assumed.

A matched single-stream probe (identical 22,471-token prompt, 200 output
tokens, one sample each) put numbers on the artifact split:

| Probe | GGUF Q4_K_M | MLX |
| -- | --: | --: |
| Prefill at 22k | 490.0 tok/s | 638.5 tok/s |
| Decode at 22k resident | 25.3 tok/s | 32.9 tok/s |
| Decode, short prompt | 30.0 tok/s | 54.8 tok/s |

The MLX runner's decode lead shrinks from +83% short-prompt to +30% with
22k resident -- its decode collapses with context (-40%) where llama.cpp
degrades gently (-16%) -- so at audit depths the per-stream rates approach
parity and the GGUF's real slots decide throughput. Single probes, not
medians.

#### AuditBench verdict: protocol-incompatible

Two canonical attempts on the MLX artifact aborted in the decode-ceiling
phase: the model refuses the output-control workload. At default effort it
deliberates and declines ("Let me know what length or pattern you actually
need", 602 of 1,024 tokens); under its documented `Reasoning strength: low`
control (the AuditBench protocol decode-compliance provision, recorded in
settings) compliance turned out variant-dependent at temperature 0 -- some
benchmark stream codes comply for the full 1,024 tokens, others refuse
("I can't generate a truly never-ending, infinite output", 190-342
tokens). Every documented control was exhausted at a refusing variant:
effort low, medium, and xhigh, and Ollama's `think: false`, all refuse.
Per protocol, both artifacts are recorded protocol-incompatible for the
output-bearing phases, never bench-marked with a shorter workload. The
knife edge moves but never disappears: the GGUF Q4_K_M complied at the
exact variant, seed, and temperature that made the MLX artifact refuse
(quantization rounding alone shifts the trajectory), and its canonical
attempt then passed the single-stream decode sample in full before both
streams of the 2x batch refused (444 and 254 of 1,024 tokens). Compliance
is trajectory-dependent -- variant digits, quantization, and batching each
tip it -- so no run can be trusted to complete, which is itself the
finding.

The prompt-only phases completed before each abort and are retained as
non-canonical observations. MLX: prefill 778 tok/s at 32k and 767 at 64k
(nearly flat across depth, unlike every measured Qwen or Gemma), and the
122,872-token near-context proof passed twice at 656-699 tok/s. GGUF at
four slots: prefill 481 at 32k and 402 at 64k, the near-context proof at
1x (295 tok/s, 417 s), and -- the concurrency capability proven at depth --
four simultaneous 122,872-token requests completed at 298.8 tok/s
aggregate in 3.95x the 1x wall, compute-bound with no preemption. The
model serves real work fine -- the smoke's tool call, reasoning channel,
and matched probes above stand -- it just declines synthetic
never-conclude output, which is an alignment property, not a serving
fault. Audit-shaped calls/hour for Glimmer therefore have no canonical
number on this runtime.

## Audit conversation profile

The conversation profile (AuditBench protocol) measures the production
audit shape: growing conversation resent every turn, tool results
mid-context, findings-ledger verdict at depth. Ollama exposes no cache
controls, so every row runs under the runtime's always-on caching
(llama.cpp slot reuse for GGUF, the MLX prefix trie for safetensors);
the runner log confirms trie hits (`cache hit ... matched=131,758`)
but the API reports no cached-token counts. Medians over compliant
samples.

Local M5 Max MLX profiles (16-file/~165k shape at 262,144 contexts;
9-file/~109k shape at the qwen3.6 131,072 operating points -- shallower,
so not directly comparable across context tiers):

| Profile | Context | Compliant | Conversations/hour | Recall |
| -- | --: | -- | --: | -- |
| `qwen3.6-35b-a3b-coding-mlx-nvfp4` | 131,072 | yes | 50.9 | 9/9 |
| `qwen3.6-35b-a3b-mlx-nvfp4` | 131,072 | yes | 48.1 | 9/9 |
| `nemotron-3.5-lightning-30b-mlx` | 262,144 | yes | 34.4 | 16/16 |
| `qwen3.8-27b-mlx-nvfp4` | 184,320 | NO | (7.7 sample 1) | 15/15 |

Lightning is the deep-context standout: full 16-file conversations at
34.4/hour with perfect recall, three for three. The qwen3.8 NVFP4 row is
a serving finding, not a rate: its first conversation completes cleanly
(469 s), and the second conversation on the same process fails with an
HTTP 500 after fully prefilling its fresh evidence -- reproduced twice.
That matches the MLX runner's documented prefix-trie snapshot retention
at the large 184,320 allocation (see the hard-reset mechanism above):
the runtime now fails gracefully where it once took down the host, but
it cannot serve consecutive deep audit conversations at this pin. The
500's runner-side cause is preserved in the retained server log.

Remote A100 profiles (16-file/~165k shape, isolated Ollama 0.32.14):

| Profile | Compliant | Conversations/hour | Recall |
| -- | -- | --: | -- |
| `qwen3.6-35b-a3b` | yes | 32.0 | 16/16 |
| `qwen3-coder-30b` | yes | 26.0 | 16/16 |
| `qwen3.8-27b-native` | yes | 14.5 | 16/16 |
| `gemma4-26b` | NO | -- | mixed |
| `glm4.7-flash` | NO | -- | -- |

The cross-runtime headline: Ollama's implicit slot cache carries
qwen3.8 GGUF to 14.5 conversations/hour on the same host where
cache-off CUDA vLLM manages 4.1 -- and align-APC vLLM carries qwen3.6
to 85.9. Cache policy, not model speed, dominates this workload.
GLM think-runs-away or paraphrases the ledger on both runtimes; gemma4
alternates between hallucinated file names and clean completions.

## Audit replay profile: A100 remote

The replay profile (AuditBench protocol) scripts every
turn, so it measures the server with no dependence on model protocol
compliance. Harness commit `03b9b2c`, isolated Ollama 0.32.14,
16-file/~165k shape. Replays/hour is not comparable to
conversations/hour (probe turns decode almost nothing; the verdict
decode is pushed toward the 16,384 cap).

| Profile | Replays/h | Turn walls | Verdict | Note |
| -- | --: | -- | -- | -- |
| `gemma4-26b` | 30.0 | flat 10.4 -> 6.9 s | 1.6-2.6k tok, stops early | slot cache confirmed behaviorally |
| `glm4.7-flash` | -- | 12 turns clean, then HTTP 500 | never reached | /v1 128Ki wall, below |

Gemma finally has audit-shaped serving numbers despite its mixed
conversation compliance: turn walls stay flat across 16 turns, proving
the llama.cpp slot cache engages even though the API reports no
cached-token counters, and each replay processes 1,672,211 prompt
tokens in ~120 s. Its verdicts ignore the never-conclude control
(1,599-2,594 tokens, `finish_reason: stop`), so its 30.0 replays/hour
is not comparable against a cap-filling model.

GLM cannot complete the shape, and the failure is a serving bug with a
crisp boundary, reproduced three times (twice in the slate run, once in
a dedicated retry with the server log preserved): the first turn whose
prompt crosses 131,072 tokens returns HTTP 500 from
`/v1/chat/completions` -- after the runner has done all the work. The
preserved log shows task 663 hit the slot cache at 126,382 tokens,
prefilled the remaining ~8k at 330 tok/s, generated the 32-token probe,
and released cleanly (`n_tokens = 131553, truncated = 0`); the GIN
layer then returned 500 with nothing logged. The allocation is fine
(202,752 per slot, and this host's canonical near-context proof pushed
8 x 190,092-token prompts through the native `/api` endpoint on the
same model), so the wall is specific to the OpenAI-compat chat path at
exactly 128Ki prompt tokens. Diagnosed and recorded locally in the
retained server log.

## A100-SXM4-80GB

Host: A100-SXM4-80GB with 81,920 MiB VRAM and 211 GiB RAM. Canonical
AuditBench v1 ran with the full profile,
three measured samples, isolated Ollama 0.32.14, Flash Attention, and q8 KV.
The server was stopped after every operating point and the GPU returned to
0 MiB.

Decode-only tuning selected the highest useful fully resident slot count before
each canonical run. Qwen3 Coder uses four slots; its eight-slot attempt
offloaded 50.64 GiB to CPU and fell to 64.82 aggregate decode tok/s. Gemma and
GLM remain fully GPU-resident at eight slots. Ollama forces Qwen3.6 and Qwen3.8
to one effective slot.

Capacity is one proof sample at 15/16 of configured context. Ollama exposes an
allocated context per effective slot, not a fungible KV pool.

| Profile | Context/request | Slots | Aggregate context | Allocation CPU / GPU | Near-context capacity proof |
| -- | --: | --: | --: | --: | -- |
| Qwen3.6 35B-A3B | 262,144 | 1 | 262,144 | 0.00 / 25.34 GiB | 1 x 245,752 in 85.26s |
| Qwen3.8 27B | 262,144 | 1 | 262,144 | 0.00 / 17.27 GiB | 1 x 245,752 in 340.97s |
| Qwen3 Coder 30B | 262,144 | 4 | 1,048,576 | 0.00 / 70.39 GiB | 4 x 245,762 in 1,016.28s |
| Gemma 4 26B-A4B | 262,144 | 8 | 2,097,152 | 0.00 / 25.32 GiB | 8 x 245,777 in 1,030.85s |
| GLM-4.7-Flash | 202,752 | 8 | 1,622,016 | 0.00 / 63.01 GiB | 8 x 190,092 in 3,703.26s |

Performance cells are median tok/s followed by `[min-max]`. Prefill generates
one token; decode generates exactly 1,024 tokens per stream.

| Profile | 32k prefill | 64k prefill | 128k prefill | Decode 1x | Decode 2x | Decode 4x | Decode 8x |
| -- | --: | --: | --: | --: | --: | --: | --: |
| Qwen3.6 35B-A3B | 4,165.7 [4,161.6-4,196.5] | 4,050.1 [3,524.4-4,063.3] | 3,569.6 [3,561.3-3,599.3] | 84.58 [76.96-87.52] | - | - | - |
| Qwen3.8 27B | 1,081.5 [1,075.4-1,092.3] | 1,007.8 [994.3-1,018.2] | 876.2 [876.1-893.3] | 57.80 [56.68-61.37] | - | - | - |
| Qwen3 Coder 30B | 2,729.4 [2,728.0-2,838.8] | 2,179.2 [2,173.9-2,246.3] | 1,404.9 [1,375.7-1,532.1] | 114.41 [111.19-114.45] | 159.28 [153.57-160.18] | 186.96 [186.95-188.24] | - |
| Gemma 4 26B-A4B | 3,246.7 [3,223.4-3,269.5] | 3,034.0 [3,019.7-3,050.5] | 2,490.2 [2,484.6-2,509.2] | 97.32 [46.16-97.36] | 153.47 [51.44-154.13] | 170.46 [65.49-183.98] | 231.48 [111.56-250.34] |
| GLM-4.7-Flash | 1,457.8 [1,455.0-1,480.0] | 958.4 [862.4-959.3] | 564.0 [554.0-568.7] | 99.66 [32.86-99.77] | 139.77 [41.21-154.67] | 204.96 [52.67-207.32] | 268.75 [87.34-284.10] |

Observed 32k/64k/128k prompt counts were respectively
32,780/65,547/131,071 for both Qwen3.6 and Qwen3.8,
32,762/65,543/131,068 for Qwen Coder, 32,779/65,535/131,058 for Gemma,
and 32,766/65,547/131,060 for GLM.

Audit cells are median calls/hour followed by `[min-max]`. The 32k and
half-context phases generate 1,024 tokens; deep generates 256.

| Profile | Audit 32k 1x | Audit 32k 2x | Audit 32k 4x | Audit 32k 8x | Audit half 1x | Audit deep 1x | Audit deep max |
| -- | --: | --: | --: | --: | --: | --: | --: |
| Qwen3.6 35B-A3B | 176.52 [169.82-180.21] | - | - | - | 64.82 [63.58-65.28] | 42.81 [42.52-43.06] | 1x |
| Qwen3.8 27B | 74.48 [73.82-79.98] | - | - | - | 21.62 [21.44-22.00] | 11.28 [11.25-11.39] | 1x |
| Qwen3 Coder 30B | 117.88 [114.92-121.91] | 125.19 [121.75-126.48] | 132.09 [129.70-132.86] | - | 26.45 [26.01-26.72] | 14.82 [14.36-14.84] | 4x: 14.36 [14.18-14.38] |
| Gemma 4 26B-A4B | 171.81 [170.96-172.96] | 197.90 [192.51-199.52] | 206.06 [200.82-206.31] | 222.32 [221.89-225.62] | 53.51 [52.15-53.63] | 27.60 [27.25-29.54] | 4x: 27.68 [27.53-28.43] |
| GLM-4.7-Flash | 97.67 [94.76-98.46] | 104.11 [102.49-104.56] | 109.18 [107.16-109.47] | 112.63 [112.02-113.01] | 21.23 [21.12-21.24] | 8.39 [8.36-8.67] | 4x: 8.37 [8.34-8.46] |

Gemma is the best Ollama operating point for the audit workload, reaching
222.32 cold-32k calls/hour while preserving eight simultaneous near-full
contexts. Qwen3.6 is the strongest one-slot and long-audit profile:
176.52 cold-32k, 64.82 half-context, and 42.81 deep calls/hour. GLM leads
aggregate Ollama decode at 268.75 tok/s, but its prompt-heavy audit rates and
202,752-token context are much weaker. Qwen Coder's four-slot decode gain
barely changes 32k audit throughput and slightly reduces deep throughput.

All five profiles remain slower on the audit workload than vLLM
`qwen3.6-35b-a3b-awq`. These rankings measure serving performance and capacity,
not answer quality.

## Retired A100 harness evidence

The measurements below predate AuditBench v1. They remain only as historical
capacity and residency evidence; none of their rates feed the canonical tables
above or the cross-runtime overview.

Host: A100-SXM4-80GB with 81,920 MiB VRAM and 211 GiB RAM. All rows use the
isolated Ollama 0.32.14 deployment, Flash Attention, and q8 KV. The server was
stopped after the measurements and GPU use returned to 0 MiB.

### Operating points

Decode rates are aggregate across active streams. Every supported row completed
one prompt between 90% and 100% of the configured context in every slot.

| Profile | Context/request | Aggregate context | Allocation CPU / GPU | Decode | Near-full proof |
| -- | --: | --: | --: | --: | -- |
| Qwen3 Coder 30B, 1 job | 262,144 | 262,144 | 0.00 / 31.46 GiB | 49.03 tok/s | 246,151 tokens in 3m 25s |
| Qwen3 Coder 30B, 2 jobs | 262,144 | 524,288 | 0.00 / 44.71 GiB | 26.48 tok/s (0.54x) | 2 x ~246,152 in 6m 49s |
| Qwen3 Coder 30B, 4 jobs | 262,144 | 1,048,576 | 0.00 / 70.39 GiB | 27.78 tok/s (0.57x) | 4 x ~246,150 in 17m 03s |
| GLM-4.7-Flash, 1 job | 202,752 | 202,752 | 0.00 / 23.47 GiB | 57.82 tok/s | 190,591 tokens in 7m 40s |
| GLM-4.7-Flash, 2 jobs | 202,752 | 405,504 | 0.00 / 29.12 GiB | 77.44 tok/s (1.34x) | 2 x ~190,554 in 15m 19s |
| GLM-4.7-Flash, 4 jobs | 202,752 | 811,008 | 0.00 / 40.42 GiB | 51.28 tok/s (0.89x) | 4 x ~190,519 in 30m 37s |
| Qwen3.6 35B-A3B, 1 job | 262,144 | 262,144 | 0.00 / 25.34 GiB | 62.26 tok/s | 246,096 tokens in 1m 24s |
| Qwen3.8 27B, 1 job | 262,144 | 262,144 | 0.00 / 17.27 GiB | 38.78 tok/s | 246,096 tokens in 5m 40s |
| Gemma 4 26B-A4B, 1 job | 262,144 | 262,144 | 0.00 / 18.31 GiB | 60.27 tok/s | 246,050 tokens in 1m 52s |
| Gemma 4 26B-A4B, 2 jobs | 262,144 | 524,288 | 0.00 / 19.62 GiB | 85.07 tok/s (1.41x) | 2 x ~246,050 in 3m 42s |
| Gemma 4 26B-A4B, 4 jobs | 262,144 | 1,048,576 | 0.00 / 21.21 GiB | 103.87 tok/s (1.72x) | 4 x ~246,049 in 8m 39s |

Qwen3.6 and Qwen3.8 requested both 2 and 4 jobs, but Ollama started an
effective `-np 1` runner for each. Those cells are unsupported rather than
unmeasured.

### Comparability and method

- The same barrier-synchronized harness and 256-token decode workload were
  used for every operating point.
- Qwen3 Coder used 13,883 short tokens and 130,918 long tokens at 1x. GLM used
  10,443 and 101,380. Qwen3.6 and Qwen3.8 used 14,187 and 130,920. Gemma used
  14,188 and 130,874.
- Token counts vary slightly with concurrent prompt variants and dynamic
  near-ceiling line scaling. The tables below retain the observed ranges.
- Each row is one complete post-warmup sample, not a confidence interval.
- `/api/ps` allocation and physical VRAM are both retained. Every supported
  A100 point kept every reported model layer on GPU, but runtime buffers make
  physical VRAM higher than the API allocation.

### Qwen3 Coder 30B-A3B

Official `qwen3-coder:30b` at its native 262,144-token context. All tested
slots completed near-ceiling prompts and all 49 reported layers stayed on GPU.

| Jobs | Context per slot | Aggregate context | CPU allocation | GPU allocation | Physical VRAM | Layers on GPU |
| --: | --: | --: | --: | --: | --: | --: |
| 1 | 262,144 | 262,144 | 0.00 GiB | 31.46 GiB | 32,753 MiB | 49 / 49 |
| 2 | 262,144 | 524,288 | 0.00 GiB | 44.71 GiB | 46,323 MiB | 49 / 49 |
| 4 | 262,144 | 1,048,576 | 0.00 GiB | 70.39 GiB | 72,589 MiB | 49 / 49 |

| Jobs | Short prefill, ~13.9k/stream | Half-context prefill, ~130.9k/stream | Near-ceiling prefill, ~246.2k/stream | Decode | Near-ceiling elapsed |
| --: | --: | --: | --: | --: | --: |
| 1 | 1,416.4 tok/s | 1,967.9 tok/s | 1,202.2 tok/s | 49.03 tok/s | 3m 25s |
| 2 | 4,744.8 tok/s | 1,998.2 tok/s | 1,202.5 tok/s | 26.48 tok/s (0.54x) | 6m 49s |
| 4 | 3,231.1 tok/s | 1,586.6 tok/s | 962.7 tok/s | 27.78 tok/s (0.57x) | 17m 03s |

Near-ceiling prompts were 246,151 at 1x, 246,151-246,152 at 2x, and
246,148-246,152 at 4x. More slots increase simultaneous capacity but do not
improve serving throughput: aggregate decode falls by 46% at 2x and 43% at 4x.

### GLM-4.7-Flash

Official `glm-4.7-flash` at its 202,752-token context. All 48 reported layers
stayed on GPU through four slots.

| Jobs | Context per slot | Aggregate context | CPU allocation | GPU allocation | Physical VRAM | Layers on GPU |
| --: | --: | --: | --: | --: | --: | --: |
| 1 | 202,752 | 202,752 | 0.00 GiB | 23.47 GiB | 24,549 MiB | 48 / 48 |
| 2 | 202,752 | 405,504 | 0.00 GiB | 29.12 GiB | 30,337 MiB | 48 / 48 |
| 4 | 202,752 | 811,008 | 0.00 GiB | 40.42 GiB | 41,889 MiB | 48 / 48 |

| Jobs | Short prefill, ~10.4k/stream | Half-context prefill, ~101.4k/stream | Near-ceiling prefill, ~190.6k/stream | Decode | Near-ceiling elapsed |
| --: | --: | --: | --: | --: | --: |
| 1 | 2,043.3 tok/s | 699.1 tok/s | 414.5 tok/s | 57.82 tok/s | 7m 40s |
| 2 | 2,192.1 tok/s | 713.3 tok/s | 414.5 tok/s | 77.44 tok/s (1.34x) | 15m 19s |
| 4 | 2,285.2 tok/s | 718.7 tok/s | 414.9 tok/s | 51.28 tok/s (0.89x) | 30m 37s |

Near-ceiling prompts were 190,591 at 1x, 190,551-190,556 at 2x, and
190,516-190,522 at 4x. Two jobs are the best decode point. Four jobs double
simultaneous context again but decode falls below the one-job rate.

### Qwen3.6 35B-A3B

Official `qwen3.6:35b-a3b` at its native 262,144-token context.

| Requested jobs | Effective jobs | Max context/request | Aggregate context | Result |
| --: | --: | --: | --: | -- |
| 1 | 1 | 262,144 | 262,144 | 246,096-token prompt completed |
| 2 | 1 | not available | not available | Ollama forced `-np 1` |
| 4 | 1 | not available | not available | Ollama forced `-np 1` |

| Metric | Value |
| -- | --: |
| Short prefill, 14,187 tokens | 3,843.2 tok/s |
| Half-context prefill, 130,920 tokens | 3,619.0 tok/s |
| Near-ceiling prefill, 246,096 tokens | 2,913.9 tok/s |
| Near-ceiling elapsed | 1m 24s |
| Decode, 256 tokens | 62.26 tok/s |
| CPU / GPU allocation | 0.00 / 25.34 GiB |
| Physical VRAM after benchmark | 27,489 / 81,920 MiB |
| Model layers on GPU | 42 / 42 |

The A100 removes the CPU offload seen on the 12 GiB host, but it cannot unlock
parallel requests because `qwen35moe` is blocked by the scheduler guard.

### Qwen3.8 27B

Official `qwen3.8:27b` at its native 262,144-token context.

| Requested jobs | Effective jobs | Max context/request | Aggregate context | Result |
| --: | --: | --: | --: | -- |
| 1 | 1 | 262,144 | 262,144 | 246,096-token prompt completed |
| 2 | 1 | not available | not available | Ollama forced `-np 1` |
| 4 | 1 | not available | not available | Ollama forced `-np 1` |

| Metric | Value |
| -- | --: |
| Short prefill, 14,187 tokens | 1,086.2 tok/s |
| Half-context prefill, 130,920 tokens | 905.0 tok/s |
| Near-ceiling prefill, 246,096 tokens | 723.8 tok/s |
| Near-ceiling elapsed | 5m 40s |
| Decode, 256 tokens | 38.78 tok/s |
| CPU / GPU allocation | 0.00 / 17.27 GiB |
| Physical VRAM after benchmark | 29,175 / 81,920 MiB |
| Model layers on GPU | 66 / 66 |

The model is fully resident on A100, unlike either local operating point, but
the `qwen35` scheduler guard still limits it to one request.

### Gemma 4 26B-A4B

Official `gemma4:26b` at its native 262,144-token context. All tested slots
completed near-ceiling prompts with all 31 reported layers on GPU.

| Jobs | Context per slot | Aggregate context | CPU allocation | GPU allocation | Physical VRAM | Layers on GPU |
| --: | --: | --: | --: | --: | --: | --: |
| 1 | 262,144 | 262,144 | 0.00 GiB | 18.31 GiB | 23,167 MiB | 31 / 31 |
| 2 | 262,144 | 524,288 | 0.00 GiB | 19.62 GiB | 27,231 MiB | 31 / 31 |
| 4 | 262,144 | 1,048,576 | 0.00 GiB | 21.21 GiB | 34,269 MiB | 31 / 31 |

| Jobs | Short prefill, ~14.2k/stream | Half-context prefill, ~130.9k/stream | Near-ceiling prefill, ~246.1k/stream | Decode | Near-ceiling elapsed |
| --: | --: | --: | --: | --: | --: |
| 1 | 3,795.6 tok/s | 3,089.2 tok/s | 2,194.9 tok/s | 60.27 tok/s | 1m 52s |
| 2 | 4,433.7 tok/s | 3,240.0 tok/s | 2,214.1 tok/s | 85.07 tok/s (1.41x) | 3m 42s |
| 4 | 4,388.4 tok/s | 2,829.0 tok/s | 1,895.6 tok/s | 103.87 tok/s (1.72x) | 8m 39s |

Near-ceiling prompts were 246,050 at 1x, 246,049-246,050 at 2x, and
246,048-246,050 at 4x. Gemma has the highest measured aggregate Ollama decode
rate on this host, and four slots still use less than half of physical VRAM.
