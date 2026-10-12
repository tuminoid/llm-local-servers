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

Isolated remote Ollama, Flash Attention, q8 KV; 0.40.3 for every profile
except `qwen3-coder-30b` on 0.32.14. Canonical AuditBench v2 `session`
profile (llm-audit-bench 2.1.0; each JSON records its harness hash), run
2026-10-11 from fleet commit `98e4052` at each conf's declared sampling.
The harness measured 1 stream and the largest of 2/4/8 that fits admission
and the KV pool: 16 tool steps from 32k evidence, report at about 165k.
Sessions/h is the median over 2-3 samples; complete counts sessions whose
report ended on its own and named at least 7/8 of its findings. pp512/tg128
is the llama-bench-method reference (one stream, greedy, depth ~0), not a
serving result. JSON files are retained under
`auditbench-trials/2026-10-11-ollama-canonical/` on the host. Slots are the
conf's `OLLAMA_NUM_PARALLEL`: one everywhere except flash-next's two. The KV
column is configured context times slots, not a measured pool. Ollama has no
`ignore_eos`, so the reference is unavailable where the model stopped before
128 tokens, and prefill is absent where the server does not report cached
tokens.

| Runtime and profile | Context | Slots | KV pool | Sessions/h by streams | Out tok/session 1x | Prefill tok/s 1x | Report decode 1x | Complete | pp512 / tg128 | Capability v2 | Publishable | JSON |
| -- | --: | --: | --: | -- | --: | --: | --: | -- | -- | -- | -- | -- |
| Ollama `gemma4-26b` | 262,144 | 1 | 262,144 | 1x 14.18 | 13,876 | 2,048.2 | 77.6 | 2/3 | unavailable | pass | no | `20261011T183519.907677+0000_ollama_gemma4-26b_session.json` |
| Ollama `qwen3-coder-30b` | 262,144 | 1 | 262,144 | 1x 18.51 | 1,703 | - | 18.1 | 2/2 | unavailable | fail | yes | `20261011T213025.516563+0000_ollama_qwen3-coder-30b_session.json` |
| Ollama `ornith1.5-35b-a3b` | 262,144 | 1 | 262,144 | 1x 27.77 | 4,357.5 | 2,711.6 | 58.3 | 2/2 | unavailable | pass | yes | `20261011T181437.335690+0000_ollama_ornith1-5-35b-a3b_session.json` |
| Ollama `qwen3.6-35b-a3b` | 262,144 | 1 | 262,144 | 1x 18.06 | 5,449 | 2,209.6 | 75.6 | 3/3 | 1,566 / 107.2 | pass | yes | `20261011T173950.452849+0000_ollama_qwen3-6-35b-a3b_session.json` |
| Ollama `qwen3.8-27b-native` | 262,144 | 1 | 262,144 | 1x 11.24 | 4,735.5 | 776.4 | 39.5 | 2/2 | unavailable | pass | yes | `20261011T190151.364043+0000_ollama_qwen3-8-27b-native_session.json` |
| Ollama `glm4.7-flash` | 202,752 | 1 | 202,752 | 1x 7.37 | 6,580.5 | 488.9 | 38.9 | 2/2 | 2,685 / 109.7 | fail | yes | `20261011T210622.723853+0000_ollama_glm4-7-flash_session.json` |
| Ollama `qwen3.8-flash-next-gguf-iq4xs` | 262,144 | 2 | 524,288 | 1x 7.98 / 2x 8.68 | 6,073.5 | 694.8 | 25.8 | 6/6 | unavailable | pass | yes | `20261011T195249.035872+0000_ollama_qwen3-8-flash-next-gguf-iq4xs_session.json` |

- `ornith1.5-35b-a3b` is the fastest Ollama profile that passes Capability
  Check v2 here, at 27.77 sessions/h; on 0.40.1 (2026-10-11, `ad06c70`) it
  measured 31.65 with 3,464 output tokens per session against 4,357.5 now.
- Five profiles pass Capability Check v2: `ornith1.5-35b-a3b`,
  `qwen3.6-35b-a3b` (18.06 sessions/h, 15.55 on 0.32.14),
  `qwen3.8-27b-native` (11.24, 11.89 on 0.34.2),
  `qwen3.8-flash-next-gguf-iq4xs` (7.98 at one stream and 8.68 at two,
  6.36 / 6.43 and unpublishable on 0.34.2) and `gemma4-26b`, which failed
  the gate on 0.32.14 and passes on 0.40.3; its run is unpublishable: one
  of three reports did not end on its own.
- `qwen3-coder-30b` stays on 0.32.14 (0.40.x returns duplicate tool
  calls) and `glm4.7-flash` fails audit fitness; both publish rates that
  cannot promote them. Every profile ran at one slot except flash-next, the
  conf defaults.

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
truncated-tool-call parser class already documented for GLM 4.7
Flash, now shown to affect the qwen4exp path too. Retest on a release
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

Remote A100 profiles (16-file/~165k shape, isolated Ollama; qwen3.8-27b-native
and flash-next on 0.34.2, the rest on 0.32.14):

| Profile | Compliant | Conversations/hour | Recall |
| -- | -- | --: | -- |
| `qwen3.6-35b-a3b` | yes | 32.0 | 16/16 |
| `qwen3-coder-30b` | yes | 26.0 | 16/16 |
| `qwen3.8-27b-native` | yes | 15.3 | 16/16 |
| `qwen3.8-flash-next-gguf-iq4xs` | yes | 10.5 | 16/16 |
| `gemma4-26b` | NO | -- | mixed |
| `glm4.7-flash` | NO | -- | -- |

The cross-runtime headline: cache policy, not model speed, dominates
this workload. On the same host the same qwen3.8 weights run 4.1
conversations/hour on cache-off CUDA vLLM (since retired), 15.3 here
through Ollama's implicit slot cache, and 21.5 on vLLM's adopted
align-APC pin -- and align-APC vLLM carries qwen3.6 to 85.9.
GLM think-runs-away or paraphrases the ledger on both runtimes; gemma4
alternates between hallucinated file names and clean completions.

## Audit replay profile: A100 remote

The replay profile (AuditBench protocol) scripts every turn, so it
measures the server with no dependence on model protocol compliance. Gemma
and GLM ran at harness commit `03b9b2c`, the three Qwen rows at `8425d08`
(the replay workload is unchanged between the two), the qwen3.8 row on
0.34.2; isolated Ollama, 16-file/~165k shape. Replays/hour is not
comparable to conversations/hour (probe turns decode almost nothing; the
verdict decode is pushed toward the 16,384 cap).

| Profile | Replays/h | Turn walls | Verdict | Note |
| -- | --: | -- | -- | -- |
| `qwen3.6-35b-a3b` | 9.92 | 11.9 s cold, 3.7 -> 6.7 s | 16,384 tok @ 59.4 tok/s | slot cache behavioral |
| `qwen3.8-27b-native` | 7.43* | 30.6 s cold, 8.9 -> 14.7 s | 2 of 3 fill cap @ 58.4 tok/s | mixed verdict lengths |
| `qwen3-coder-30b` | 3.39 | 8.6 s cold, 3.9 -> 10.9 s | 16,384 tok @ 17.4 tok/s | depth-decode bound |
| `gemma4-26b` | 30.0 | flat 10.4 -> 6.9 s | 1.6-2.6k tok, stops early | slot cache confirmed behaviorally |
| `glm4.7-flash` | -- | 12 turns clean, then HTTP 500 | never reached | truncated tool-call 500, below |

The three Qwen rows complete the cross-runtime replay comparison on
this host:

- The llama.cpp slot cache engages behaviorally on all three (first
  turn pays the 33k evidence prefill, later turns only the ~8.2k
  suffix), but at depth it is no match for align APC: qwen3.6 runs
  9.92 replays/h against vLLM's 18.3 on the same fixture, and the gap
  is at both ends -- growing turn walls (3.7 -> 6.7 s vs flat 2.3-2.5 s)
  and verdict decode at ~165k depth (59.4 vs 98.0 tok/s).
- qwen3.8's median (7.43*) rides on mixed verdict lengths: one sample
  obeyed its own stop instinct at 926 tokens (14.34 replays/h), the
  other two filled the 16,384 cap (7.36-7.43). The same
  variant-dependent never-conclude compliance was recorded on its vLLM
  legs; compare turn walls and verdict rate, not the starred median.
- qwen3-coder is depth-decode bound: 17.4 tok/s verdict decode at 164k
  makes the verdict 89% of its 1,061 s replay wall, the same
  context-loaded decode collapse its conversation profile shows.

Gemma finally has audit-shaped serving numbers despite its mixed
conversation compliance: turn walls stay flat across 16 turns, proving
the llama.cpp slot cache engages even though the API reports no
cached-token counters, and each replay processes 1,672,211 prompt
tokens in ~120 s. Its verdicts ignore the never-conclude control
(1,599-2,594 tokens, `finish_reason: stop`), so its 30.0 replays/hour
is not comparable against a cap-filling model.

GLM cannot complete the shape, and the failure is root-caused: a
truncated tool call trips the runtime's GLM tool-call parser, and the
earlier "128Ki wall" reading was a coincidence of depth. The observed
shape stands -- three times, the first turn whose prompt crossed
131,072 tokens returned HTTP 500 after the runner had done all the
work (the preserved log shows task 663 hit the slot cache at 126,382
tokens, prefilled the remaining ~8k at 330 tok/s, generated the
32-token probe, and released cleanly with `truncated = 0`, and the GIN
layer then returned 500 with nothing logged). The mechanism: at that
turn the deterministic temperature-0 output opens a `<tool_call>`
inside the 32-token probe window, the cap slices the XML mid-call, and
on stream end the builtin glm4.7 parser's finalize step fails to parse
the fragment; the server converts that parser error into the 500 after
generation, through an error path that writes nothing to the log. A
minimal repro at 230 prompt tokens (tools declared, thinking disabled,
`max_tokens` 6-12 slicing the call) returns the same 500 from both
`/v1/chat/completions` and native `/api/chat`, with the error body
naming the cause: `incomplete GLM tool call: XML syntax error on line
1: element <arg_value> closed by </tool_call>`. Earlier turns pass
because their 32 probe tokens stay inside thinking or content, never
entering the parser's tool-call state; prompt depth only decided when
the model first reached for a tool that fast. Any client that caps
completion tokens below a GLM tool call in flight trips this; the
16,384-token conversation profile never does, which is why GLM's
conversation samples completed all 17 turns. Retested on a 0.33.2
trial: byte-identical 500 on both endpoints (the parser is unchanged
there), though the runtime now recovers the runner cleanly after a
mid-stream parser error where it previously wedged. The retest
condition stays open for future releases: the fault is in the
runtime's parser finalization, not in this deployment or the model
artifact.

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
