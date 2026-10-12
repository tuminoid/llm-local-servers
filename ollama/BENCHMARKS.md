# Ollama benchmark results

Measured throughput, memory, context, and concurrency baselines for the
script-managed Ollama deployments on the hosts below.

Use each host's operating-point table for its measured hardware. The later
sections preserve the measurements and memory explanations behind those
recommendations.

The A100, M5 and RTX PRO 3000 sections titled AuditBench v2 use canonical
[AuditBench v2](https://github.com/tuminoid/llm-audit-bench); every other
section is AuditBench v1 or older history, never comparable with v2. The
later A100 rows use canonical AuditBench v1. The Apple operating-point
tables use the retired runtime-specific harness; the Apple AuditBench v1
sections (Nemotron and the conversation profile)
are canonical and dated per section. Retired A100 measurements remain
clearly separated later in this file and must not be combined with canonical
rates. Their top-level retained JSON on the M5 and A100 was removed on
2026-09-30; trial-directory copies remain, and the figures stay here and in
git history.

## AuditBench v2: A100-SXM4-80GB

Isolated remote Ollama 0.40.3, Flash Attention, q8 KV. Canonical AuditBench v2 `session`
profile (llm-audit-bench 2.1.0; each JSON records its harness hash), run
2026-10-11 from fleet commit `98e4052` at each conf's declared sampling.
The harness measured 1 stream and the largest of 2/4/8 that fits admission
and the KV pool: 16 tool steps from 32k evidence, report at about 165k.
Sessions/h is the median over 2-3 samples; complete counts sessions whose
report ended on its own and named at least 7/8 of its findings. pp512/tg128
is the llama-bench-method reference (one stream, greedy, depth ~0), not a
serving result. JSON files are retained under
`auditbench-trials/2026-10-11-ollama-canonical/` on the host. Slots are the
conf's `OLLAMA_NUM_PARALLEL`: one for Ornith, two for flash-next. The KV
column is configured context times slots, not a measured pool. Ollama has no
`ignore_eos`, so the reference is unavailable where the model stopped before
128 tokens, and prefill is absent where the server does not report cached
tokens.

| Runtime and profile | Context | Slots | KV pool | Sessions/h by streams | Out tok/session 1x | Prefill tok/s 1x | Report decode 1x | Complete | pp512 / tg128 | Capability v2 | Publishable | JSON |
| -- | --: | --: | --: | -- | --: | --: | --: | -- | -- | -- | -- | -- |
| Ollama `ornith1.5-35b-a3b` | 262,144 | 1 | 262,144 | 1x 27.77 | 4,357.5 | 2,711.6 | 58.3 | 2/2 | unavailable | pass | yes | `20261011T181437.335690+0000_ollama_ornith1-5-35b-a3b_session.json` |
| Ollama `qwen3.8-flash-next-gguf-iq4xs` | 262,144 | 2 | 524,288 | 1x 7.98 / 2x 8.68 | 6,073.5 | 694.8 | 25.8 | 6/6 | unavailable | pass | yes | `20261011T195249.035872+0000_ollama_qwen3-8-flash-next-gguf-iq4xs_session.json` |

- Both profiles pass Capability Check v2. `ornith1.5-35b-a3b` runs 27.77
  sessions/h; on 0.40.1 (2026-10-11, `ad06c70`) it measured 31.65 with
  3,464 output tokens per session against 4,357.5 now.
  `qwen3.8-flash-next-gguf-iq4xs` runs 7.98 at one stream and 8.68 at two
  (6.36 / 6.43 and unpublishable on 0.34.2).
- The same campaign measured the A100's other Ollama profiles, dropped on
  2026-10-12 because vLLM serves those models faster here or they failed the
  gate on both runtimes: `qwen3.6-35b-a3b` 18.06, `qwen3-coder-30b` 18.51
  (fail), `gemma4-26b` 14.18 (unpublishable), `qwen3.8-27b-native` 11.24 and
  `glm4.7-flash` 7.37 (fail). Their rows, and the A100 AuditBench v1,
  conversation, replay and pre-v1 evidence for them, are in git history.

## AuditBench v2: Apple M5 Max

Managed Ollama 0.32.14 for the MLX profiles (the runner serializes requests
to one slot). Contexts are the confs': 131,072 for Glimmer and 262,144 for
nemotron. Canonical
AuditBench v2 `session` profile (llm-audit-bench v2.0.0 plus the amendments
released as v2.1.0; each JSON records its harness hash), run 2026-09-27 to
2026-09-29 on the M5 Max (128 GB, macOS 27.0) from fleet commit `bee4a24` at
each conf's declared sampling. The harness measured 1 stream and the largest
of 2/4/8 that fits admission and the KV pool: tool steps from 32k evidence,
16 at 262,144 configured context and 9 at 131,072, report at depth.
Sessions/h is the median over 2-3 samples; complete counts sessions whose
report ended on its own and named at least 7/8 of its findings. pp512/tg128
is the llama-bench-method reference (one stream, greedy, depth ~0), not a
serving result. JSON files are retained under
`~/.local/state/auditbench/trials/2026-09-27-v2-canonical/m5/`.

| Runtime and profile | Context | Slots | KV pool | Sessions/h by streams | Out tok/session 1x | Prefill tok/s 1x | Report decode 1x | Complete | pp512 / tg128 | Capability v2 | Publishable | JSON |
| -- | --: | --: | --: | -- | --: | --: | --: | -- | -- | -- | -- | -- |
| Ollama `nemotron-3.5-lightning-30b-mlx` | 262,144 | 1 | 262,144 | 1x 21.12 | 9,913 | - | 86.7 | 2/2 | 2,647 / 157.0 | fail | yes | `20260929T184051.620932+0000_ollama_nemotron-3-5-lightning-30b-mlx_session.json` |
| Ollama `muse-glimmer-30b-mlx` | 131,072 | 1 | 131,072 | 1x 18.45 | 1,504 | - | 34.8 | 2/2 | unavailable | fail | yes | `20260929T183047.934174+0000_ollama_muse-glimmer-30b-mlx_session.json` |

- Both MLX profiles fail Capability Check v2 on schema enforcement
  (`ignored`); their rates (nemotron 21.12, Glimmer 18.45) cannot promote
  them. The Qwen3.6 and Qwen3.8 Ollama profiles left the M5 on 2026-10-11
  (Splash serves Qwen3.6 35B-A3B and Qwen3.8 27B there; ds4 serves
  Flash-Next).

## AuditBench v2: RTX PRO 3000 Blackwell

Local host, RTX PRO 3000 Blackwell laptop GPU with 12,227 MiB VRAM, 62 GiB
RAM. Ollama 0.40.3, Flash Attention, one slot. Canonical AuditBench v2
`session` profile (llm-audit-bench 2.1.0), run 2026-10-12 at the conf's
declared sampling from fleet commit `1e7318d`: 13 tool steps at 163,840
configured context. Columns as in the A100 table.

| Runtime and profile | Context | Slots | KV pool | Sessions/h by streams | Out tok/session 1x | Prefill tok/s 1x | Report decode 1x | Complete | pp512 / tg128 | Capability v2 | Publishable | JSON |
| -- | --: | --: | --: | -- | --: | --: | --: | -- | -- | -- | -- | -- |
| Ollama `saluki-27b` (q4_0 KV) | 163,840 | 1 | 163,840 | 1x 3.26 | 3,377 | 218.3 | 7.8 | 3/3 | unavailable | pass | yes | `20261012T064953.361627+0000_ollama_saluki-27b_session.json` |

- `saluki-27b` passes Capability Check v2 (1/12): 3.26 sessions/h over 13
  steps, all 65 layers and its 10.90 GiB on the GPU. Turn decode falls from
  12.4 to 6.5 tok/s across the session. An exploratory run at 184,320 with
  3 layers on the CPU (15 steps) measured 3.65 with decode 12.7 to 8.4, so
  at depth decode is bound by the q4_0 KV reads, not by those layers.
- It is the host's one profile. The 2026-10-11 campaign also measured
  `gemma4-e2b` (40.98 sessions/h), `qwen3.5-4b` (17.49), `qwen3.5-9b`
  (14.73) and `gemma4-12b` (7.87), all fully on the GPU and all failing
  audit fitness, and the CPU-assisted `qwen3.6-35b-a3b` (3.06,
  unpublishable). They were dropped on 2026-10-12; their rows and the
  host's AuditBench v1 operating points are in git history.

## Apple M5 Max MLX operating points

Host: MacBook Pro `Mac17,6`, Apple M5 Max, 40 GPU cores, 128 GB unified
memory, macOS 26.6.2 (25G83), on external power. The MLX rows use the managed
official Ollama 0.32.14 (`ollama-darwin.tgz`), whose MLX runner loaded the
`mlx_metal_v4` backend (MLX 0.32.0-213-gadf21de, device gpu) -- the Metal 4
path on M5. The MLX profiles are safetensors registry artifacts dispatched
to the MLX runner; KV cache is MLX-native model precision, not q8.

The MLX runner serializes requests through a single slot, so all rows are
jobs=1. Two concurrent clients measured 1.91x single-request wall time and
four measured 4.08x, each with unchanged per-request eval rate and
staircase completion times -- queueing, not batching. Concurrency against
this server is therefore worth nothing beyond queueing convenience; the
operating points below are single-stream maxima.

The MLX runner silently enables speculative decoding whenever an artifact
packages a draft head -- there is no serving switch and no log line at
default verbosity, so a rate from such an artifact is speculated, not
plain. A bandwidth audit established it on the since-dropped Qwen3.8 NVFP4
profile.

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
capacity proof, and the near-full ingest completes in 127.4 s. The
audit cadence (212.8 / 58.3 / 31.1 calls/hour) leads every canonical
profile on this host at every depth, single-stream against their best
measured concurrency. Capability gating for this artifact is recorded in
[../CAPABILITIES.md](../CAPABILITIES.md); the run JSON is retained
outside the repository.

### The native-262k hard reset

The two hard-reset records below come from the Qwen3.6 and Qwen3.8 NVFP4
profiles, dropped from the M5 on 2026-10-11. They stay as the MLX runner's
memory evidence: they are why raising an MLX context is a supervised
experiment.

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

The dropped profiles' context maxima (Qwen3.6 262,144 with a 246,096-token
proof, Qwen3.8 184,320) were then found with supervised runs: a watchdog
sampled available memory every 2 s and would kill the server's process
group below an 18 GiB floor. Qwen3.6 passed its full native ceiling;
Qwen3.8's 184,320 pass had no room left above it. Raising a context above
a profile default is that kind of supervised experiment, per model -- on
unified memory the failure mode is the whole machine, not an OOM-killed
server process, and headroom never transfers between models.

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
crash-era server log was truncated on restart), but the question is
closed by a supervised 2026-09-04 retest on the pinned 0.32.14: the
CURRENT digest completed two consecutive single-shot needle prefills
at 235,597 and 246,104 tokens under the 262,144 allocation (available
memory never below 67 GiB; needle retrieved both times), and the third
cache-busted deep request then detonated AFTER its prefill completed
-- ~68 GiB of available memory allocated in ~2 s with kernel pressure
still normal; the available-memory watchdog killed the process group
and the host was unharmed. The old digest was never special: its 246k
proof was the same single-shot shape the current digest passes, so the
fatal variable is request REPETITION, not the manifest repin, and the
detonation point is the post-prefill commit -- the same point where
the 0.33.2 trial's conversation-profile regression fires (see that
section). The 262,144 ban therefore holds on shape grounds for every
digest and pin until three consecutive cache-busted near-ceiling
prefills pass under a watchdog. (The 0.33.2 trial also left the
131,072 point bounded, consistent with its immunity here.)

### Muse Glimmer 30B MLX smoke

`muse-glimmer:30b-mlx` (safetensors mixed-precision, ~21 GiB, dispatched to
the MLX runner) passed its three-gate smoke on the managed 0.32.14 pin:
model registration, a chat request with the reasoning channel populated
under a `Reasoning strength: low` system prompt, and a clean structured
`get_weather` tool call through the OpenAI-compatible API. Full lifecycle
verified including stop with an empty process group.

That smoke predates the tag's current manifest. The registry has since
moved `muse-glimmer:30b-mlx` twice: to `ef32a55b4976` (reviewed
2026-08-25) and then to `015fa21845be`, reviewed and pinned 2026-09-07
after the identity guard refused it. No performance or DFlash speedup
number transfers across either move, and the numbers below belong to the
`ef32a55b4976` artifact. The current digest is ~3 GiB smaller and
measured 17.72 GiB of GPU residency at the native 131,072 context during
its capability check (an operating fact, not a benchmark); it passes
every applicable capability check, failing only the MLX runner's
schema-enforcement defect (see [CAPABILITIES.md](../CAPABILITIES.md)).

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

### Qwen3.8-Flash-Next GGUF IQ4_XS -- AuditBench v1 canonical (A100)

The `qwen3.8-flash-next-gguf-iq4xs` profile (Ollama 0.34.2, 2 x 262,144
q8_0 shape, 62.84 GiB GPU allocation, 49/49 layers on GPU) has canonical
AuditBench v1 full and conversation rows; replay is blocked by the
truncated-tool-call 500 below.

| Metric | 1 slot | 2 slots |
| -- | --: | --: |
| 32k / 64k / 128k prefill tok/s | 958.8 / 875.8 / 740.2 | |
| Decode tok/s | 51.38 | 83.26 |
| Audit 32k calls/h | 59.11 | 63.50 |
| Audit half calls/h | 15.88 | |
| Audit deep calls/h | 8.96 | 8.72 |
| Near-context proof | 245,748 in 424.06 s | 2 x 245,748 in 853.61 s |
| Conversation | 10.5/h, compliant, 16/16 | |

The model is PLE-over-PCIe and QSA bound, so cold deep prefills serialize
across slots and starve the sibling slot's decode. The
2 x 262,144 shape is locked: an 8 x 65,536 shape batched decode to only
143.5 tok/s aggregate at 63% GPU utilisation, and a big model on tiny
windows serves no fleet need.

The capability check's unaided long-document request reproducibly kills
the runner with a CUDA illegal memory access (Xid 31 in the quantized
matmul launch) on 0.33.3 and 0.34.2 alike; the same document under a
JSON schema completes, Ollama restarts the runner in ~10 s, and a later
12k-token unconstrained generation in the same session completed.
Constrain long generations with a schema; retest on every runtime bump.

The replay and replay-concurrent profiles CANNOT run canonically on
this model at its pin: their 32-token probe turns cap-truncate a tool
call mid-arguments and Ollama 0.33.3 and 0.34.2 return HTTP 500 ("invalid
tool call arguments ... unexpected end of JSON input") on both endpoints.
Minimal deterministic repro at temp 0: tools plus max_tokens 32 (16
stops before the call opens, 200 completes it) -- the same
truncated-tool-call parser class first found on GLM 4.7 Flash (its
profile was dropped 2026-10-12; the diagnosis is in git history), here on
the qwen4exp path. Retest on a release
whose parsers degrade truncation gracefully.

## Audit conversation profile

The conversation profile (AuditBench protocol) measures the production
audit shape: growing conversation resent every turn, tool results
mid-context, findings-ledger verdict at depth. Ollama exposes no cache
controls, so every row runs under the runtime's always-on caching
(llama.cpp slot reuse for GGUF, the MLX prefix trie for safetensors);
the runner log confirms trie hits (`cache hit ... matched=131,758`)
but the API reports no cached-token counts. Medians over compliant
samples.

Local M5 Max MLX profile (16-file/~165k shape at 262,144 context):

| Profile | Context | Compliant | Conversations/hour | Recall |
| -- | --: | -- | --: | -- |
| `nemotron-3.5-lightning-30b-mlx` | 262,144 | yes | 34.4 | 16/16 |

Lightning is the deep-context standout: full 16-file conversations at
34.4/hour with perfect recall, three for three. The since-dropped
`qwen3.8-27b-mlx-nvfp4` profile (184,320) was a serving finding, not a
rate: its first conversation completed cleanly
(469 s), and the second conversation on the same process failed with an
HTTP 500 after fully prefilling its fresh evidence -- reproduced twice.
That matches the MLX runner's documented prefix-trie snapshot retention
at the large 184,320 allocation (see the hard-reset mechanism above):
the runtime now fails gracefully where it once took down the host, but
it cannot serve consecutive deep audit conversations at this pin. The
500's runner-side cause is preserved in the retained server log.

A supervised 0.33.2 trial made this failure WORSE, and the finding
drove the decision to keep the fleet pin at 0.32.14: on 0.33.2 the
same shape (first conversation completes cleanly and compliant at
397 s, second conversation's fresh 33k evidence prefill starts as a
cache miss with the full 156,670-token prior conversation still
resident in the trie) no longer returns the graceful 500 -- the
prefill runs to completion and then memory demand goes vertical at the
snapshot commit, free memory falling from 34.6 GiB to 56 MiB in under
2.5 minutes with kernel pressure still reporting normal. The armed
memory watchdog killed the process group; unsupervised this is the
hard-reset shape again. The qwen3.6 131,072 operating point stayed
bounded on the same trial runtime (two consecutive deep conversations,
free-memory floor 27.8 GiB), so the regression bites at the large
allocation, not everywhere.

Supervised trials of 0.33.3 (2026-09-04) and 0.34.2 (2026-09-18) on
the same artifact and allocation reproduced the runaway, 0.34.2 inside
the first conversation at ~148k resident tokens and faster than an
available-memory watchdog could act; the host hard-reset. The pin stays
0.32.14 for every MLX profile. GGUF profiles never dispatch to the MLX
runner and are unaffected.

Remote A100 profile (16-file/~165k shape, isolated Ollama 0.34.2):
`qwen3.8-flash-next-gguf-iq4xs` was compliant at 10.5 conversations/hour
with 16/16 recall.
