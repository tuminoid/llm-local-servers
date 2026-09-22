# vLLM-Metal benchmark results

Measured baselines for the script-managed vLLM-Metal server on Apple
Silicon. The cross-runtime summary is [../README.md](../README.md); the
same-host Ollama MLX baselines are in
[../ollama/BENCHMARKS.md](../ollama/BENCHMARKS.md).

The AuditBench v1 sections below (operating-point, conversation, replay,
and concurrent-replay profiles) are
canonical under the finalized output-control prompt; each states its
plugin pin and cache condition. The other sections use the retired
vLLM-Metal bring-up harness or the earlier prompt. Do not combine those
legacy rates with canonical results.

## Audit conversation profile

The conversation profile (AuditBench protocol) is the production-shaped
workload: 32k evidence, a sequential 16-file tool chain resent in full
every turn, findings-ledger verdict at ~164k depth. All rows run at
their serving-default cache pins on the finalized control-free
fixture at plugin 0.29.0 (repo commit `705c493`). Medians over
compliant samples; cached fraction from the engine's own counters.

| Profile | Cache pin | Compliant | Conversations/hour | Cached | Recall |
| -- | -- | -- | --: | --: | -- |
| `qwen3.6-35b-a3b-4bit` | APC on | yes | 12.9 | 0.897 | 16/16 |
| `qwen3.8-27b-4bit` | APC on | yes | 4.2 | 0.899 | 16/16 |
| `gemma4-31b-4bit` | APC on | yes | 2.4 | 0.902 | 16/16 |
| `ornith1.5-35b-a3b-4bit` | APC on | 1/2 | 7.6 | 0.896 | 16/16 |
| `granite4.2-30b-4bit` (131k fixture) | APC on | no | -- | 0.525 | 2/9 files |
| `nemotron-3.5-lightning-30b-4bit` | off | yes | 4.9 | -- | 16/16 |

Findings:

- qwen3.6 with align-mode APC is this host's only practical audit
  conversation server: 12.9 conversations/hour with 89.7% of prompt
  tokens served from cache and perfect recall on every sample.
- qwen3.8 with align-mode APC completes a conversation in 849 s with
  89.9% of prompt tokens cached and perfect recall. The cache removes
  the quadratic resend; what bounds the row is dense decode at depth
  (5.5 tok/s verdict decode, see the replay profile).
- gemma4 completes with perfect recall but at 1,500 s per conversation
  (decode-bound); it stays a capability point, not an audit choice.
- ornith completes a conversation in 471 s with 89.6% cached and
  perfect recall when it completes, but one of two samples stopped at
  15/16 files, so the row stays unranked in the cross-runtime table.
- granite stopped after one or two of its 131k fixture's nine files in
  both samples: not a conversation server on this host.
- nemotron, cache off by pin, completes a conversation in 730 s with
  perfect recall: every turn resends the whole transcript and 3,300
  tok/s prefill absorbs the quadratic resend. Plugin 0.29.0 refuses
  prefix caching for the `nemotron_h` state family (`mamba_cache_mode`
  none only), so cache off is the only operating point.

### qwen3.8 align-APC trial and adoption

The align-mode budget math for qwen3.8: one GDN layer's state is
3,207,168 B (48 v-heads x 128 x 128 fp32 recurrent + 3 x 10,240 bf16
conv); align mode carries 17 state pools per block (one per
full-attention layer plus one growth overlap -- qwen3.6's "10 + 1"
generalizes as full-attention count + 1) beside a 784-token block's KV
pages, giving 105,902,080 B/block, verified against the planner's
per_block_bytes line to the byte, or 135,080 B/token -- 2.06x the plain
paged-KV cost. The pool lands at 611,156 tokens (2.33 native
sequences, down from cache-off's 4.83).

Trial at plugin dev20260826100011, MagSafe 140 W (relative same-session
measurements, indicative rates; user bar <=20% decode for >=10x warm
prefill):

| Measure | Cache off | Align APC on | Delta |
| -- | --: | --: | -- |
| Decode 1x/2x/4x tok/s | 32.9 / 59.9 / 93.6 | 28.8 / 51.7 / 82.7 | -12.5 / -13.8 / -11.6% |
| Warm-prefix TTFT | 20.3-21.5 s | 0.44 s | 47-49x |

Decode held flat across samples (no per-request decay -- the PR #634
fix covers this model too), and the correctness gate passed at the
strong bar: cold-vs-hit byte-identical on both probe conversations
across server restarts, cache-off control also deterministic, semantic
needles 8/8. The pin flipped to align APC on. Align mode changes temp-0
outputs versus cache-off (documented plugin behavior), so the cache-off
canonical rates do not transfer; the APC operating point has its own
canonical table below.

## Audit replay profile: M5 Max

Canonical replay runs (AuditBench protocol) at the
serving-default cache pins (align APC on for both hybrids), repo commit
`705c493`, plugin 0.29.0, Dell brick at the 140 W contract,
dedicated server lifecycle per model. Replays/hour is never comparable
to conversations/hour, and here it is not even comparable across
models: qwen3.6, nemotron, granite and gemma4 filled the forced
16,384-token verdict (`finish_reason: length`) while qwen3.8 and
ornith ignored the never-conclude control in both samples and stopped
at 0.9-1.6k tokens, so their replays/h ride on 10-18x less verdict
decode. The server-comparable columns are the turn walls and the
verdict decode rate.

| Profile | Replays/h | Turn walls (16 turns) | Cached | Verdict decode at ~164k depth |
| -- | --: | -- | --: | -- |
| `qwen3.6-35b-a3b-4bit` | 2.13 | 13.3 s cold, 6.2 -> 18.8 s | 0.824 | 16,384 tok @ 11.0 tok/s |
| `qwen3.8-27b-4bit` | 4.04* | 59.3 s cold, 21.2 -> 52.6 s | 0.899 | 1.5-1.6k tok @ 5.5-5.6 tok/s (stopped early) |
| `ornith1.5-35b-a3b-4bit` | 12.6* | 13.2 s cold, 6.1 -> 18.6 s | 0.897 | 0.9k tok @ 10.5 tok/s (stopped early) |
| `granite4.2-30b-4bit` (131k fixture, 9 turns) | 0.95 | 58.8 s cold, 22.3 -> 38.9 s | 0.848 | 16,384 tok @ 4.7 tok/s (107k depth) |
| `gemma4-31b-4bit` | 0.42 | 96.8 s cold, 40.5 -> 121.3 s | 0.902 | 16,384 tok @ 2.3 tok/s |
| `nemotron-3.5-lightning-30b-4bit` (cache off) | 2.80 | 9.9 s cold, 13.0 -> 72.6 s | -- | 16,384 tok @ 24.2 tok/s |

- qwen3.6: 88% of the 1,689 s median wall is the forced verdict
  decode (1,489 s); the same fixture on the A100 runs 18.3 replays/h
  with the verdict at 98 tok/s, so the M5 gap at audit depth is almost
  entirely single-stream decode bandwidth (11.0 tok/s), not caching.
  Cached fraction matches the A100 anchor exactly (0.824, same
  block-rounding of the shared fixture).
- qwen3.8: even with 89.9% of prompt tokens cached, turn walls grow
  21 -> 53 s with depth -- the ~8.2k-token uncached suffix each turn
  prefills against growing attention depth, and align-mode Metal
  prefill pays it. Contrast the A100's flat 4.3-7.4 s turns on the same
  fixture. Verdict decode of 5.5 tok/s at 164k depth confirms the
  settled fleet role: quality reserve, not a live audit server.
- nemotron, cache off by pin: 2.80 replays/h. 53% of the 1,287 s wall
  is the forced verdict at 24.2 tok/s; the rest is the uncached resend,
  turn walls growing 13 -> 73 s with depth; plugin 0.29.0 offers no
  prefix caching for this state family, so that cost stands until a
  plugin bump.
- ornith: 12.6 replays/h with turn walls of 6-19 s at 89.7% cached;
  the verdict stopped at 0.9k tokens (never-conclude control ignored,
  as qwen3.8) decoding at 10.5 tok/s at 165k depth.
- granite: 0.95 replays/h on the 9-turn 131k fixture; 92% of the
  3,783 s wall is the forced verdict at 4.7 tok/s.
- `gemma4-31b-4bit`: 8,497 s per replay, 85% of it the forced
  16,384-token verdict at 2.3 tok/s (7,196 s, four seconds inside the
  7,200 s request timeout). Turn walls grow 40 -> 121 s with depth at
  90.2% cached. This is the dense-31B depth-decode wall, consistent
  with its 1.4 deep audit calls/h; a capability point, not an audit
  server.

## Concurrent audit replay profile: M5 Max

Canonical replay-concurrent runs (AuditBench protocol) at the
serving-default align-APC pins, repo commit `705c493`, plugin 0.29.0,
Dell brick at the 140 W contract, dedicated server lifecycle per
model. The profile is the multi-agent
audit shape: N scripted replays at once share the 32k evidence prefix
(same repository, distinct per-agent file chains) and every probe turn
decodes a 1,024-token agent turn, so aggregate decode contention is
part of the number. Replays/hour here is not comparable to the 1x
replay profile above (32-token probes), and not across these two
models either: qwen3.6 decodes every turn to the full 1,024 cap while
qwen3.8 stops at ~810 median.

### qwen3.6-35b-a3b-4bit APC -- concurrent replay canonical

Context 262,144, pool 1,326,140 tokens; streams 1, 2, and 4 fit; peak
2 streams.

| Streams | Batch wall | Replays/h | Scaling | Turn walls first -> final | Verdict decode | Cached |
| --: | --: | --: | --: | -- | --: | --: |
| 1 | 2,312 s | 1.56 | 1.00 | 28.9 -> 92.4 s | 12.2 tok/s | 0.892 |
| 2 | 2,996 s | 2.40 | 1.54 | 40.2 -> 146.4 s | 8.1 tok/s | 0.902 |
| 4 | 7,383 s | 1.95 | 1.25 | 54.6 -> 293.1 s | 3.8 tok/s | 0.912 |

Two concurrent agents are the knee: 4x falls below 2x aggregate while
doubling per-agent latency, and the shared prefix helps (cached
fraction rises with streams) but stays minor against a ~167k final
conversation. The 2x median-of-3 carries a wide sample range
(2,982-3,729 s).

### qwen3.8-27b-4bit APC -- concurrent replay canonical

Context 262,144, pool 603,469 tokens; the 184,320-token per-stream
demand fits streams 1 and 2 only; peak 2 streams.

| Streams | Batch wall | Replays/h | Scaling | Turn walls first -> final | Verdict decode | Cached |
| --: | --: | --: | --: | -- | --: | --: |
| 1 | 1,937 s | 1.86 | 1.00 | 93.4 -> 58.8 s | 5.6 tok/s | 0.898 |
| 2 | 3,379 s | 2.13 | 1.15 | 96.2 -> 63.5 s | 4.1 tok/s | 0.908 |

qwen3.8 under-decodes the per-turn control (~810 of 1,024 median), so
its replays/hour buys less work per replay than qwen3.6's. Both stream
counts needed a third sample (1x range 1,867-2,133 s, 2x
3,179-3,699 s).

## Apple M5 Max operating points

Host: MacBook Pro `Mac17,6`, Apple M5 Max, 40 GPU cores, 128 GB unified
memory, macOS 26.6.2 (25G83), on external power. The two align-APC
serving points are measured at the current plugin pin 0.29.0; the
cache-off comparison tables name the earlier dev pins they were
measured on, and each pin move (dev20260826100011 with the PR #634 APC
decay fix, 0.28.0, 0.29.0) re-gated decode and cold 32k/64k prefill
within ~3% of the previous pin. The legacy
bring-up rows ran on the earlier pin, vLLM 0.27.1 and MLX 0.32.0, paged
KV path, utilization 0.60, max-num-seqs 4, NAX prefill kernels
confirmed loaded from the engine log (`NAX prefill attention kernels
loaded (M5 tensor units)`), one full sample after warmup.

### qwen3.6-35b-a3b-4bit -- AuditBench v1 canonical (cache-off)

Measured at plugin 0.3.0.dev20260826100011. Cache-off condition (`VLLM_PREFIX_CACHING=0`):
context 262,144, util 0.46, paged KV pool 1,407,463 tokens, seqs 5.

| Phase | Streams | Result |
| -- | -- | --: |
| Prefill 32,780 | 1 | 2,942.8 tok/s |
| Prefill 65,547 | 1 | 1,685.8 tok/s |
| Prefill 131,071 | 1 | 1,083.8 tok/s |
| Capacity 245,752 | 1 | passed, 657.0 tok/s, 374 s |
| Capacity 245,752 | 4 | passed, 656.0 tok/s aggregate, 1,499 s |
| Decode | 1 / 2 / 4 | 121.1 / 205.3 / 320.0 tok/s (1.70x / 2.64x) |
| audit_32k calls/hour | 1 / 2 / 4 | 124.2 / 113.3 / 118.5 (peak streams 1) |
| audit_half (131k) calls/hour | 1 | 19.6 |
| audit_deep (229k) calls/hour | 1 / 4 | 10.1 / 9.9 (peak streams 1) |

### qwen3.6-35b-a3b-4bit APC operating point -- AuditBench v1 canonical

Measured at plugin 0.29.0, repo commit `705c493`. The serving default
(`VLLM_PREFIX_CACHING=1`): context 262,144, util 0.71, paged KV pool
1,326,140 tokens, seqs 5.

| Phase | Streams | Result |
| -- | -- | --: |
| Prefill 32,780 | 1 | 2,543.4 tok/s |
| Prefill 65,547 | 1 | 1,646.1 tok/s |
| Prefill 131,071 | 1 | 1,065.9 tok/s |
| Capacity 245,752 | 1 | passed, 637.6 tok/s, 385 s |
| Capacity 245,752 | 4 | passed, 637.2 tok/s aggregate, 1,543 s |
| Decode | 1 / 2 / 4 | 102.0 / 174.3 / 265.0 tok/s (1.71x / 2.60x) |
| audit_32k calls/hour | 1 / 2 / 4 | 113.3 / 110.5 / 117.9 (peak streams 4) |
| audit_half (131k) calls/hour | 1 | 19.1 |
| audit_deep (229k) calls/hour | 1 / 4 | 9.8 / 9.9 (peak streams 4) |

Align-APC costs ~16% decode and ~9% cold 32k audit rate against the
cache-off table above; all benchmark requests are cold, and the
operating point exists for the warm TTFT win on resent audit
conversations (see the replay profile).

### qwen3.8-27b-4bit -- AuditBench v1 canonical

Measured at plugin 0.3.0.dev20260819180958, repository commit 623565d,
with the finalized output-control prompt, at the serving default
operating point: context
262,144, util 0.91, paged KV pool 1,264,961 tokens, seqs 5, external power,
battery gate at its fixed 80/90 levels. Medians are from three samples
(capacity proof runs once); ~12.2 h wall, of which roughly 4 h was eight
battery-gate recharge pauses -- the dense model's active bench time was
~8 h, close to the 7.5 h estimate.

| Phase | Streams | Result |
| -- | -- | --: |
| Prefill 32,784 | 1 | 495.6 tok/s |
| Prefill 65,556 | 1 | 429.1 tok/s |
| Prefill 131,075 | 1 | 304.0 tok/s |
| Capacity 245,748 | 1 | passed, 200.3 tok/s, 1,227 s |
| Capacity 245,748 | 4 | passed, 208.8 tok/s aggregate, 4,707 s |
| Decode | 1 / 2 / 4 | 33.1 / 59.3 / 92.3 tok/s (1.79x / 2.79x) |
| audit_32k calls/hour | 1 / 2 / 4 | 36.4 / 39.3 / 40.1 (peak streams 4) |
| audit_half (131k) calls/hour | 1 | 6.7 |
| audit_deep (229k) calls/hour | 1 / 4 | 3.3 / 3.3 (peak streams 1) |

The 8-stream points were omitted because admission is five slots; audit_deep
probes 1x and the maximum fitting candidate (4x) per protocol.

Findings beyond the raw rates:

- The canonical run confirms the legacy bring-up decode numbers
  (32.5/59.1/93.6 then, 33.1/59.3/92.3 now) instead of revising them, unlike
  qwen3.6 whose output-bearing metrics dropped under the finalized prompt.
- Dense audit economics against the same-host MoE: a cold 32k audit costs
  2.9x (36.4 vs 105.5 calls/hour), mid-context 2.8x (6.7 vs 18.7), deep 2.9x
  (3.3 vs 9.6). Concurrency helps modestly (+10% at 4 streams cold) where
  the MoE was flat, and decode still scales at four streams -- dense batching
  behaves as expected.
- Prefill is the wall: 3.6x-5.7x slower than the MoE across the curve, and
  the near-context proof runs at 200-209 tok/s (20 minutes for one 245k
  prefill, 78 minutes for four).
- Thermals: GPU 29.8-98.2 C over the run, median 68.9, no sag.
- Power incident, worth institutional memory: mid-run the Apple 140 W
  charger silently renegotiated its USB-PD EPR contract down to a 45 W
  20 V profile (cause not yet isolated: brick thermal protection or a PD
  hard reset). macOS kept reporting "AC Power, charging" while the host
  drained ~1.4%/min under 4-stream deep load; caught at 12% via the battery
  logger and fixed by replugging onto a 140 W-capable brick, which
  renegotiated the full 28 V profile. The in-flight sample completed and
  the gate then recharged 13% -> 90%. On a drain anomaly, check
  `pmset -g ac` wattage first; the raised fixed gate floor (80) exists so a
  long batch never starts with less than a full-batch margin.

### qwen3.8-27b-4bit APC operating point -- AuditBench v1 canonical

Measured at plugin 0.29.0, repo commit `705c493`. The serving default
(`VLLM_PREFIX_CACHING=1`): context 262,144, util 0.91, paged KV pool
603,469 tokens, seqs 5. The APC pool holds 2.30 near-full contexts, so
capacity and audit_deep probe 1x and 2x.

| Phase | Streams | Result |
| -- | -- | --: |
| Prefill 32,784 | 1 | 568.0 tok/s |
| Prefill 65,556 | 1 | 450.3 tok/s |
| Prefill 131,075 | 1 | 315.5 tok/s |
| Capacity 245,748 | 1 | passed, 207.0 tok/s, 1,187 s |
| Capacity 245,748 | 2 | passed, 206.9 tok/s aggregate, 2,375 s |
| Decode | 1 / 2 / 4 | 28.8 / 52.8 / 82.6 tok/s (1.83x / 2.87x) |
| audit_32k calls/hour | 1 / 2 / 4 | 34.7 / 38.1 / 39.0 (peak streams 4) |
| audit_half (131k) calls/hour | 1 | 6.6 |
| audit_deep (229k) calls/hour | 1 / 2 | 3.3 / 3.3 |

Against the cache-off table above, APC costs ~11-13% decode and halves
the token pool while audit calls/hour stay flat; the operating point
exists for the warm TTFT win on resent audit conversations.

### nemotron, ornith, granite, gemma4 -- AuditBench v1 canonical

Plugin 0.29.0, repo commit `705c493`, serving-default cache pins,
`max-num-seqs` 5, Dell brick at the 140 W contract, dedicated server
lifecycle per model (2026-09-21/22). Medians; the audit columns name
the best stream count.

| Profile | Cache pin | Context | KV pool | Prefill 32k/64k/128k tok/s | Decode 1/2/4 tok/s | audit_32k /h | audit_half /h | audit_deep /h | Near-context proof |
| -- | -- | --: | --: | --: | --: | --: | --: | --: | -- |
| `nemotron-3.5-lightning-30b-4bit` | off, util 0.32 | 262,144 | 1,591,012 | 3,359 / 2,738 / 2,323 | 123.0 / 185.6 / 267.0 | 197.4 @2x | 42.9 | 25.9 @1x | 4 x 245,773 in 564.90s |
| `ornith1.5-35b-a3b-4bit` | align APC, util 0.70 | 262,144 | 1,300,439 | 2,623 / 1,664 / 1,075 | 101.5 / 173.5 / 264.3 | 117.5 @4x | 19.0 | 9.9 @4x | 4 x 245,752 in 1,539.43s |
| `granite4.2-30b-4bit` | APC, util 0.91 | 131,072 | 331,584 | 558 / 446 / - | 30.8 / 55.6 / 88.6 | 31.0 @2x | 13.8 (65k) | 9.3 @1x (114.7k) | 2 x 122,876 in 753.08s |
| `gemma4-31b-4bit` | APC, util 0.91 | 262,144 | 617,308 | 355 / 243 / 148 | 26.6 / 47.9 / 72.0 | 17.3 @4x | 2.6 | 1.4 @2x | 2 x 245,774 in 5,601.60s |

- nemotron leads every column on this host (cache off, one private
  Mamba-2 state slot per request) and passes Capability Check v1 with
  the conf's qwen3 dialect parsers; its conversation and replay rows
  are above.
- ornith lands within 3% of qwen3.6 APC on prefill and decode with a
  1.30M-token pool.
- granite and gemma4 are dense-decode bound: 31 and 17 audit_32k
  calls/h and single-digit deep calls/h.

### qwen3.8-27b-8bit (mlx-community/Qwen3.8-27B-8bit) -- retired baseline

The phase bring-up checkpoint (upstream's verified example for this
family). Its config was removed once the 4-bit profile measured strictly
better decode at the same prefill and more KV; the operating points below
are retained as the recorded baseline.

Served at the checkpoint's native 262,144-token context. Three measured
operating points, identical except the memory budget and admission cap:

| | util 0.60, seqs 4 | util 0.80, seqs 8 | util 0.91, seqs 4 (default) |
| -- | --: | --: | --: |
| Paged KV pool | 521,185 tokens (1.99x native) | 870,193 tokens (3.32x native) | 1,061,760 tokens (4.05x native) |
| Engine footprint | 65-66 GB, stable | 88-89 GB, stable | 98 GB planned |
| Prefill 14,225 tok | 708 tok/s | 722 tok/s | - |
| Prefill 66,173 tok | 414 tok/s | 424 tok/s | - |
| Near-ceiling 245,478 tok | 206 tok/s | 204 tok/s | - |
| Decode 1 stream | 18.1 tok/s | 18.1 tok/s | - |
| Aggregate 2 streams | 35.4 (1.96x) | 35.5 (1.96x) | - |
| Aggregate 4 streams | 65.7 (3.64x) | 65.9 (3.65x) | - |
| Aggregate 8 streams | not admitted (seqs 4) | 84.7 (4.69x) | not admitted (seqs 4) |

The 0.91 point exists to hold four full-length requests at once -- the
launcher's large-memory default after measurement. It was startup-verified
and smoke-tested (memory pressure nominal, ~28 GB left) rather than fully
re-benchmarked, because rates measured identical between 0.60 and 0.80:
the budget buys KV capacity only.

A stream sweep on the 0.91 pool located the decode sweet spot and set the
default admission cap to 5. Aggregate decode by admitted streams, short
prompts, 200 output tokens each:

| Streams | Aggregate | Per stream |
| --: | --: | --: |
| 4 | 65.9 tok/s | ~16.5 |
| 5 | 76.1-79.5 tok/s | ~15-16 |
| 6 | 66.2-72.1 tok/s | ~11-12 |
| 8 | 84.7 tok/s | ~10.6 |

Six admitted streams measured consistently below five across repeated
interleaved runs -- a batch-shape effect, not noise. Eight has the highest
raw aggregate but drops per-stream decode to ~10.6 tok/s; five keeps
near-full per-stream speed at 90% of the 8-stream aggregate. Five
sequences also stay preemption-free while they average under ~212k tokens
(pool 1,061,760), and four worst-case 262,144-token sequences fit
outright. Admission is not memory-aware: the cap applies however small the
resident jobs are, and the pool with recompute preemption is what actually
governs memory.

The budget fraction resolves against Metal's recommended working-set limit
(~106 GB on this 128 GB host), not raw RAM: 0.60 yields a 66 GB footprint
and 0.80 yields 89 GB. Both footprints were planned at startup and held
flat through every workload including the near-ceiling prefill -- the
bounded-memory property this runtime was selected for. The same 246k
workload shape that hard-reset this machine under the unbounded Ollama MLX
runner completed at both budgets. Raising the budget buys KV capacity
only; prefill and decode rates are unchanged.

Continuous batching is real and its knee is between 4 and 8 streams:
near-linear to 4 (3.65x), then a diminishing step to 8 (4.69x aggregate,
per-stream falling from ~16.5 to ~10.6 tok/s) as the shared weight-stream
saving is exhausted against GDN per-sequence state and scheduling
overhead. ~85 tok/s aggregate is this checkpoint's practical decode
ceiling -- above the Ollama MLX runner's 72.26 tok/s single stream, which
that runtime cannot exceed at any client count. Contrast its measured
1.91x/4.08x wall-time staircase (pure queueing) on this host.

API correctness passed alongside throughput: streaming reasoning arrives
in `delta.reasoning` with no `</think>` leak, structured tool calls parse
through `qwen3_xml`, and the server survived a mid-stream client
cancellation and a full stop/start cycle with correct responses after
both.

### Comparison with the Ollama MLX baseline, and its limits

Same model family, different quantization (NVFP4 vs 8-bit) and different
context defaults, so rates are deployed-operating-point comparisons, not
same-bytes runtime isolation:

| | Ollama MLX (qwen3.8 NVFP4, 184k) | vLLM-Metal (qwen3.8 8-bit, 262k) |
| -- | --: | --: |
| Short prefill | 827.0 tok/s | 708 tok/s |
| Near-ceiling prefill | 350.6 tok/s @ 173k | 206 tok/s @ 245k |
| Decode 1x | 72.26 tok/s | 18.1 tok/s |
| Decode 4x aggregate | unsupported (queues) | 65.7 tok/s |
| Memory at ceiling | 92.78 GiB peak, no bound | 66 GB, bounded up front |
| Full native 262k | machine hard reset | completed |

The single-stream decode gap (72 vs 18 tok/s) decomposes into two
factors, only one of which is bytes: 8-bit weights are ~1.8x the bytes
of NVFP4, and -- established later by a bandwidth audit -- the Ollama
MLX runner silently runs the checkpoint's packaged MTP draft head
(speculative decoding on by default whenever an artifact ships a head),
worth ~1.5-1.6x on top. The 72.26 tok/s figure exceeds the plain-decode
ceiling of the M5 Max's 614 GB/s memory bandwidth over ~14 GiB of
weights (~44 tok/s), so it is not a plain rate at all. This profile's
own decode is honest plain autoregressive at ~82-88% of the bandwidth
roof -- the kernels are near-silicon, not deficient. Even four
concurrent streams (65.7 aggregate) do not reach the Ollama runner's
speculated single stream.
What vLLM-Metal buys on this model is bounded memory, the full native
context, and real multi-request semantics -- not raw decode speed. The
4-bit checkpoint below closes most of that gap.

### qwen3.8-27b-4bit (mlx-community/Qwen3.8-27B-4bit) -- serving profile

The sole remaining config and the recommended operating point: the same
quality tier as Ollama's NVFP4 baseline (both 4-bit weight classes),
measured at util 0.91 with seqs 8 admitted for the sweep. Weights
~15.5 GiB; the freed memory became KV: pool 1,264,961 tokens, 4.83x a
full native sequence, matching the ~4.9x theory (KV stays 64 KiB/token
whatever the weight bits). The 8-bit profile above was retired after
this measurement -- its numbers remain as the recorded baseline, its
config is gone.

| Workload | Result |
| -- | --: |
| Prefill 14,225 tok | 723 tok/s |
| Prefill 66,173 tok | 433 tok/s |
| Near-ceiling 245,478 tok | 206 tok/s |
| Decode 1 stream | 32.5 tok/s |
| Aggregate 2 streams | 59.1 (1.87x) |
| Aggregate 4 streams | 93.6 (2.96x) |
| Aggregate 5 streams | 100.1-103.6 (~20/stream) |
| Aggregate 6 streams | 92.2-94.9 (consistently below 5) |
| Aggregate 8 streams | 105.7 (3.34x, ~13.2/stream) |

Single-stream decode is 1.8x the 8-bit checkpoint and the aggregate
passes Ollama's 72.26 tok/s single-stream ceiling from three streams up,
peaking at ~106. Prefill is identical to 8-bit at every size: prefill is
compute-bound, so weight bytes buy decode speed and KV capacity only.
The 5-over-6 batch-shape dip reproduces here (100-104 vs 92-95 across
interleaved repeats), so seqs 5 remains the sweet spot: ~98% of the
8-stream aggregate at twice its per-stream speed. Structured tool calls
verified on this checkpoint.

### qwen3.6-35b-a3b-4bit (mlx-community/Qwen3.6-35B-A3B-4bit) -- MoE profile

The fine-grained MoE sibling (256 experts, 8 active, ~3B active
parameters), MLX 4-bit affine with 8-bit gates, ~19.5 GiB of weights,
measured at its native 262,144 context at util 0.91, seqs 5. Only 10 of
40 layers are full attention (2 KV heads
x 256 head dim), so paged KV costs 20 KiB/token -- 3.2x cheaper than
qwen3.8 -- and the 0.91 budget plans a 3,908,234-token pool, 14.9x a
full native sequence. The engine translates the hybrid block size to
1056 tokens and allocates GDN linear-attention state lazily
(64.4 MB/slot); planned footprint is ~105 GB usable Metal budget with
weights 19.5 GB and KV budget 81.3 GB inside it. That is far more KV
than five admitted requests can consume, so the serving default is now
sized from the declared KV cost instead: the launcher computes util 0.46
(1,410,584-token pool, five full native sequences outright, ~53 GB
bound). The budget buys KV capacity only, so the rates below carry over.

Two full samples with the retired bring-up harness, immediately before
AuditBench v1 replaced it (default cap 5, then a re-run at seqs 16 to
expose the plateau); ranges below span both:

| Workload | Result |
| -- | --: |
| Prefill 14,183 tok | 3,684-3,874 tok/s |
| Prefill 66,131 tok | 1,824-1,842 tok/s |
| Near-ceiling 246,143 tok | 627-631 tok/s |
| Decode 1 stream | 114.0-118.2 tok/s |
| Aggregate 2 streams | 195.6-197.2 (1.67x) |
| Aggregate 4 streams | 310.8-314.5 (2.66x) |
| Aggregate 8 streams | 312.8-313.7 (seqs 16 run) |
| Aggregate 16 streams | 317.4 (2.68x, seqs 16 run) |

Aggregate decode saturates at four streams: ~315 tok/s is the ceiling,
and 8 or 16 admitted streams add nothing (measured with the cap raised
to 16, so this is a real plateau, not admission queueing). That is the
expected MoE shape -- concurrent tokens route to different experts, so
batching stops amortizing weight reads much earlier than on the dense
checkpoint, which kept scaling to 8. The default cap of 5 therefore
already captures the model's maximum; raising it only dilutes per-stream
speed (16 streams decode ~20 tok/s each against 114 solo).

Solo decode is 3.5x the dense qwen3.8-4bit (114 vs 32.5) and short
prefill is 5.4x (3,684 vs 723 tok/s); the near-ceiling 246k prefill
completed at 631 tok/s -- 3x the dense checkpoint -- inside the bounded
footprint. Against the Ollama MLX runner on the same model family, solo
decode is a wash (122.58 tok/s there vs 114-118 here) and Ollama keeps a
short-prompt prefill edge, but Ollama serializes requests while this
runtime reaches 315 tok/s aggregate from four streams. Thinking-mode
chat, `enable_thinking: false`, and `qwen3_xml` structured tool calls
all verified on this checkpoint.

No MLX conversion of the registry-only `-coding` variant exists (the
official HF Qwen org never released one), so the base checkpoint is the
vLLM-Metal profile; the coding variant remains Ollama-only.

### NVFP4 checkpoints do not load

`unsloth/Qwen3.8-27B-NVFP4` (revision 7d6f8d4d) fails engine init loudly
at this pin: `ValueError: Received 937 parameters not in model` -- mlx-lm
has no weight mapping for NVFP4 block-scale safetensors of this
architecture. The verdict transfers to `nvidia/Qwen3.6-35B-A3B-NVFP4`
(same quantization format), so no NVFP4 profile exists here and the
Ollama registry remains the only NVFP4 path on this host. Re-test on an
mlx-lm bump rather than assuming this is permanent.

### Candidate smoke verdicts

Five downloaded mlx-community candidates were smoke-tested (start, chat,
structured tool call, verified teardown) at plugin 0.3.0.dev20260819180958,
vLLM 0.27.1, mlx-lm 0.31.3, mlx-vlm 0.6.4, transformers 5.12.1:

- `gemma-4-31b-it-4bit` **passed**: pool 617,308 tokens at the computed
  budget, `gemma4` parsers produced a structured call, teardown clean. It
  keeps its model config and is bench-eligible.
- `Devstral-Small-2-24B` and `Devstral-2-123B` fail at engine init:
  mlx-vlm's tokenizer wrapper reads `.vocab`, which transformers v5's
  `MistralCommonBackend` does not expose (the conversions declare an
  unresolvable `tokenizer_class`, forcing that fallback). Confirmed
  unfixed at mlx-vlm 0.6.15 + transformers 5.15.1 by a snapshot-and-
  rollback venv experiment; vLLM's `--tokenizer-mode` cannot reach the
  selection. Retest on a plugin bump whose mlx-vlm drops the `.vocab`
  assumption.
- `NVIDIA-Nemotron-3.5-Lightning-30B-A3B-OptiQ-4bit` loaded (pool
  1,331,525 tokens) but the first forward killed the engine
  (`TypeError: string indices must be integers`) at the plugin/mlx-lm
  boundary. It serves since plugin 0.29.0; its canonical rows are
  above.
- `gemma-4-12b-coder-fable5-composer2.5-4bit` is an incomplete artifact:
  every mlx-community gemma4-12B conversion (plain and OptiQ) lacks the
  processor files vLLM's gemma4 path requires; the 31B conversion has
  them. Needs a re-uploaded conversion, not a code bump.

Failing configs were removed per the fail-loudly convention; their
weights are no longer kept.

### History: qwen3.6 align-APC adoption (resolved)

The path to the APC serving default above, retained as diagnosis
evidence. The divergent-conversation correctness gate passed first
(align mode, `VLLM_PREFIX_CACHING=1`): cold and cache-hit
outputs byte-identical in both directions across restarts and across
32k/262k max-len configs; TTFT on a 15k shared prefix 4.09 s cold vs
0.11 s hot. Adoption was then blocked by the same-day decode smoke at
plugin 0.3.0.dev20260819180958: align-mode decode started at
93.6/149.0/214.7 tok/s (1/2/4), ~21% under the flat cache-off control
at 117/200/310, and degraded deterministically with requests served
per process -- 65/88/149 by sample 3, 26/45/82 after ~35 requests,
identical curve on every restart, no recovery without one, not thermal
(cooled rerun continued degraded). Root cause was upstream: full
recurrent-state-pool copies per update, fixed by plugin PR #634.
(since merged). A trial retest on
v0.3.0.dev20260826100011 measured APC-on decode flat at 101/171/257
then 99/167/255 tok/s across ~28 requests, cache-off control
119.6/202.0/316.1 -- decay fixed, a flat ~15-19% align cost remaining.
The pin then moved, the gates re-passed on the pinned venv, and the
APC canonical ran (table above). The smoke's cache-off
control (117/200/310) had also sat above the earlier canonical
decode (96.7/159.5/247.1); the newer cache-off canonical
(121.1/205.3/320.0) confirmed the higher rates and superseded that
row's decode figures.

### TurboQuant KV compression (2026-09-04): measured, not adopted

q8_0 keys / q3_0 values (the plugin defaults) on `qwen3.8-27b-4bit` at
plugin 0.28.0, cache-off, util 0.91. The capacity gain is real: the
paged pool grew 1,264,961 -> 3,177,028 tokens at the same budget
(packed SDPA page 1600 B/token vs 4096 fp16, engine-reported 2.56x),
with decode rates (31.3-32.6 / 60.8 / 94.7 tok/s at 1x/2x/4x) and
answer quality (temp-0 needle at ~10k depth, reasoning separation,
tool calls) at parity. Not adopted because cold prefill collapses and
keeps collapsing with depth -- 539 / 384 / 224 / 130 tok/s at
3.7k / 7.3k / 14.6k / 31.3k prompt tokens against the plain path's
flat ~570-600 -- and with NAX enabled a single cold prefill between
~15k and ~29k tokens hangs the engine permanently (the Metal command
buffer never completes; NAX on/off rates are identical at 14.6k, so
the packed path does not use the NAX kernels at all; NAX-off
completes). Prefill dominates audit cost and the plain pool already
holds 4.83x native, so the trade is strictly negative here. Retest on
a plugin release noting TurboQuant prefill performance or
NAX-compatible TurboQuant kernels: cold prefill ladder first
(2k-32k, NAX on), nothing deeper until it is flat and hang-free.
