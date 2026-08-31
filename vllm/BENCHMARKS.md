# vLLM benchmark results

Measured throughput, memory, context, and concurrency baselines for the two GPU
generations this tree is verified against. Results are grouped by host because
models are comparable only when they ran on the same hardware with the same
harness.

Use the tables at the top to choose an operating point. The later sections
preserve the measurements, architectural explanations, full-context tests, and
failure modes behind those summaries.

The RTX PRO 3000 and A100 rows use canonical
[AuditBench v1](https://github.com/tuminoid/llm-audit-bench).
Retired A100 measurements remain
clearly separated later in this file and must not be combined with canonical
rates.

## TL;DR: same-hardware comparisons

All throughput figures are observed rates, not model-quality scores. Compare
rows within one host table; do not compare a Blackwell row with an A100 row.

### Small card

RTX PRO 3000 Blackwell laptop GPU (sm_120), 12,227 MiB VRAM. Canonical
AuditBench v1 ran with three measured samples, vLLM 0.27.1,
Transformers 5.14.1, the full profile, and the proper power adapter. The host
profile reserved 1,024 MiB, resolved to utilization 0.916, and admitted two
sequences. Qwen used FlashInfer with fp8 KV; Gemma used vLLM-selected Triton
attention with automatic 16-bit KV.

Capacity is one proof sample. Input rate is aggregate prompt tok/s.

| Model | Context | Active slots | Raw KV pool | Near-context capacity proof |
| -- | --: | --: | --: | -- |
| `qwen3.5-4b-awq` | 131,072 | 2 | 274,432 | 1 x 122,861 in 43.56s at 2,820.6 tok/s; 2 x in 87.77s at 2,799.6 tok/s |
| `gemma4-e2b-awq` | 131,072 | 2 | 450,444 | 1 x 122,896 in 62.49s at 1,966.7 tok/s; 2 x in 124.89s at 1,968.0 tok/s |

Performance cells are median tok/s followed by `[min-max]`. Prefill output is
one token; decode output is exactly 1,024 tokens per stream.

| Model | 32k prefill | 64k prefill | Decode 1x | Decode 2x |
| -- | --: | --: | --: | --: |
| `qwen3.5-4b-awq` | 4,686.9 [3,760.1-4,691.2] @ 32,780 | 3,774.3 [3,757.3-3,788.7] @ 65,547 | 87.41 [87.29-87.67] | 176.12 [158.21-176.38] (2.01x) |
| `gemma4-e2b-awq` | 4,835.1 [4,800.7-4,846.9] @ 32,772 | 3,168.8 [3,152.6-3,174.0] @ 65,528 | 145.44 [145.34-148.63] | 303.54 [275.09-304.18] (2.09x) |

Audit cells are median calls/hour followed by `[min-max] / median output
tok/s`. The 32k and half-context phases generate 1,024 tokens; deep generates
256.

| Model | Audit 32k 1x | Audit 32k 2x | Audit half 1x | Audit deep 1x | Audit deep 2x |
| -- | --: | --: | --: | --: | --: |
| `qwen3.5-4b-awq` | 180.18 [178.97-183.54] / 51.25 | 250.94 [248.33-251.66] / 71.38 | 113.76 [113.67-113.92] / 32.36 | 83.20 [82.83-83.24] / 5.92 | 85.82 [85.37-85.97] / 6.10 |
| `gemma4-e2b-awq` | 215.06 [206.74-218.29] / 61.17 | 289.55 [287.69-306.29] / 82.36 | 113.31 [106.53-113.38] / 32.23 | 56.22 [55.54-56.29] / 4.00 | 56.89 [56.80-57.13] / 4.05 |

Gemma is the decode and cold-32k leader. Qwen is slightly faster at common
64k prefill and substantially faster near the end of a 128k audit, reaching
85.82 deep calls/hour against Gemma's 56.89. Both operating points are capped
at two admitted streams; canonical 4x and 8x candidates are omitted rather
than queued.

### 80 GB A100

A100-SXM4-80GB (sm_80), 81,920 MiB VRAM. Canonical AuditBench v1 ran with
three measured samples, vLLM 0.27.1, Transformers 5.14.1, and the full
profile. The scheduler admitted eight
sequences; each phase automatically omitted stream counts that did not fit the
raw KV pool.

Capacity is one proof sample at 15/16 of configured context. No row submits
queued pseudo-concurrency.

| Model | Context | Raw KV pool | Pool/context | Near-context capacity proof |
| -- | --: | --: | --: | -- |
| `qwen3-coder-30b` | 262,144 | 512,864 | 1.96x | 2 x 245,762 in 290.58s |
| `glm4.7-flash-awq` | 202,752 | 1,050,624 | 5.18x | 4 x 190,092 in 421.70s |
| `qwen3.6-35b-a3b-awq` | 262,144 | 2,747,310 | 10.48x | 8 x 245,752 in 350.22s |
| `qwen3.8-27b` | 262,144 | 749,204 | 2.86x | 2 x 245,748 in 324.99s |
| `gemma4-26b-a4b-awq` | 262,144 | 1,868,129 | 7.13x | 4 x 245,774 in 624.84s |

Performance cells are median tok/s followed by `[min-max]`. Prefill generates
one token; decode generates exactly 1,024 tokens per stream.

| Model | 32k prefill | 64k prefill | 128k prefill | Decode 1x | Decode 2x | Decode 4x | Decode 8x |
| -- | --: | --: | --: | --: | --: | --: | --: |
| `qwen3-coder-30b` | 8,461.3 [8,449.2-8,486.8] | 5,241.8 [5,229.5-5,279.4] | 3,005.4 [3,000.4-3,012.2] | 149.37 [149.37-149.41] | 290.58 [268.17-290.67] | 521.85 [521.70-522.25] | 1,020.30 [1,019.76-1,021.12] |
| `glm4.7-flash-awq` | 7,239.0 [7,226.5-7,258.7] | 4,343.8 [4,323.1-4,345.0] | 2,525.1 [2,522.8-2,525.2] | 87.41 [87.33-87.50] | 149.00 [148.97-149.04] | 231.69 [230.84-232.14] | 363.08 [362.20-363.61] |
| `qwen3.6-35b-a3b-awq` | 16,103.9 [16,095.6-16,130.7] | 12,456.9 [12,428.3-12,461.1] | 8,628.8 [8,577.5-8,646.8] | 149.53 [136.07-149.58] | 273.07 [272.89-275.93] | 506.20 [505.68-507.01] | 880.31 [868.15-885.56] |
| `qwen3.8-27b` | 2,697.5 [2,689.6-2,707.5] | 2,404.8 [2,402.3-2,408.3] | 1,977.0 [1,976.8-1,978.5] | 48.43 [48.42-48.43] | 94.28 [94.25-94.30] | 182.55 [182.54-182.57] | 347.50 [347.38-347.53] |
| `gemma4-26b-a4b-awq` | 7,616.4 [7,612.2-7,621.9] | 4,823.5 [4,820.2-4,829.0] | 2,758.5 [2,756.1-2,760.2] | 167.90 [167.81-167.91] | 314.10 [314.09-314.17] | 584.63 [584.52-584.78] | 1,066.07 [1,065.87-1,066.96] |

Observed 32k/64k/128k prompt counts were respectively 32,762/65,543/131,068
for Qwen Coder, 32,766/65,547/131,060 for GLM, 32,780/65,547/131,071 for
Qwen3.6, 32,784/65,556/131,075 for Qwen3.8, and
32,776/65,532/131,055 for Gemma.

Audit cells are median calls/hour followed by `[min-max]`. The 32k and
half-context phases generate 1,024 tokens; deep generates 256.

| Model | Audit 32k 1x | Audit 32k 2x | Audit 32k 4x | Audit 32k 8x | Audit half 1x | Audit deep 1x | Audit deep max |
| -- | --: | --: | --: | --: | --: | --: | --: |
| `qwen3-coder-30b` | 283.63 [282.54-283.74] | 378.54 [377.25-379.08] | 461.15 [459.96-461.17] | 514.55 [513.75-515.22] | 61.66 [61.42-61.75] | 27.07 [27.02-27.28] | 2x: 26.62 [26.57-26.73] |
| `glm4.7-flash-awq` | 185.15 [185.11-185.26] | 242.25 [240.07-242.28] | 311.43 [311.23-312.38] | 367.03 [366.82-368.14] | 66.20 [65.99-66.28] | 36.26 [36.20-36.50] | 4x: 37.29 [37.15-37.29] |
| `qwen3.6-35b-a3b-awq` | 382.81 [382.23-383.06] | 587.68 [585.93-587.82] | 817.19 [815.92-818.40] | 1,003.11 [1,001.96-1,003.66] | 150.95 [150.85-151.25] | 86.33 [85.88-86.44] | 4x: 85.38 [85.25-85.43] |
| `qwen3.8-27b` | 103.59 [103.48-103.65] | 148.47 [148.31-148.63] | 190.10 [189.91-190.14] | 220.37 [220.28-220.42] | 38.90 [38.86-38.96] | 23.37 [23.33-23.38] | 2x: 23.61 [23.60-23.63] |
| `gemma4-26b-a4b-awq` | 258.31 [258.04-258.43] | 389.52 [388.81-390.12] | 510.58 [509.37-510.86] | 594.09 [593.82-594.35] | 58.59 [58.56-58.61] | 25.62 [25.61-25.62] | 4x: 26.32 [26.28-26.34] |

`qwen3.6-35b-a3b-awq` is the audit workhorse: 1,003.11 cold-32k calls/hour,
150.95 half-context calls/hour, 86.33 deep calls/hour, and eight simultaneous
near-full requests. Gemma is the pure decode leader at 1,066.07 tok/s, with
Qwen Coder close behind at 1,020.30. Those decode wins do not survive the
prompt-heavy audit phases.

These rankings describe serving performance only. They do not establish which
model gives better answers.

## Comparability and benchmark method

The RTX and A100 canonical rows use AuditBench v1 exactly as defined in the
shared protocol: three interleaved samples, common absolute prompts, relative
long-context prompts, fixed outputs, and only stream counts that fit both
admission and the raw KV pool. Compare models within one host. The common
protocol makes workload shapes consistent across hosts, but it does not erase
their different GPU generations, memory systems, or power envelopes.

The tables compare deployed operating points rather than forcing identical
backends or quantization. That is intentional: some architectures require
Triton, MLA, automatic KV selection, or a lower utilization cap. Across hosts,
GPU generation, memory, backend support, KV dtype, and power envelope differ,
so cross-host ranking is invalid.

Run the canonical local harness with `make vllm-bench MODEL=<config>` and the
remote harness with
`make vllm-remote-bench HOST=<host> MODEL=<config>`. AuditBench retains exact
prompt counts, raw samples, medians, ranges, and runtime metadata in its final
JSON. Memory figures here are larger than minimum model footprints because
vLLM expands the KV pool to fill its configured memory budget.

## Audit conversation profile: A100 fleet

The conversation profile (AuditBench protocol) is the production-shaped
workload: 32k evidence, a 16-file sequential tool chain resent in full
every turn, plain-text findings-ledger verdict at ~165k depth. All five
profiles ran at their serving-default cache pins on the finalized
control-free fixture, vLLM 0.27.1.

### The cache decides the workload, first

The motivating experiment, same server and digest `119886a1`, only
`VLLM_PREFIX_CACHING` differing (run on the pre-finalization fixture;
both sides identical, so the ratio stands):

| Cache mode | Conversation wall | Conversations/hour | Per-turn walls | Prompt tokens processed | Cached fraction |
| -- | --: | --: | -- | --: | --: |
| off | 197.8 s median | 18.2 | grows 3.8 -> 27.7 s | 1,687,914 | not reported |
| align APC on | 43.9 s median | 82.1 | flat ~1.3-3 s | ~10% of off | 0.897 measured |

The cache-off server re-processes 1,687,914 prompt tokens per
conversation -- 10.2x the 165,388-token final depth -- and per-turn wall
grows linearly with the prefix. With align-mode APC the engine's own
`cached_tokens` counters report 89.7% of prompt tokens served from
cache, per-turn wall goes flat, and the same conversation completes 4.5x
faster. This result flipped the conf pin to APC on.

### Fleet table, serving defaults

Medians over compliant samples; cached fraction from engine counters.

| Profile | Cache pin | Compliant | Conversations/hour | Cached | Recall |
| -- | -- | -- | --: | --: | -- |
| `qwen3.6-35b-a3b-awq` | APC on | yes | 85.9 | 0.898 | 16/16 |
| `qwen3-coder-30b` | APC on | yes | 45.2 | 0.902 | 16/16 |
| `gemma4-26b-a4b-awq` | APC on | yes | 43.8 | 0.906 | 16/16 |
| `qwen3.8-27b` | APC on | yes | 21.9 | 0.898 | 16/16 |
| `glm4.7-flash-awq` | APC on | NO | -- | 0.902 | 0/16 |

Findings:

- qwen3.6 at its APC serving default is the A100's audit workhorse:
  85.9 conversations/hour with perfect recall.
- qwen3.8 at its adopted align-APC default reaches 21.9
  conversations/hour (144-179 s conversations, 0.898 cached, perfect
  recall on all three samples) -- 5.3x the retired cache-off default,
  which measured 4.1/h with ~877 s conversations, each re-prefilling
  ~1.69M tokens. It now also beats its own Ollama GGUF artifact on the
  same host (14.5/h through llama.cpp's implicit slot cache). The pin
  flip came from the align-APC trial in the replay section below.
- GLM 4.7 Flash is the one profile that cannot execute the shape: one
  sample think-ran-away without a single tool call (16,384 reasoning
  tokens, `finish_reason: length`), and the sample that completed all
  17 turns recalled 0 of 16 findings -- it paraphrases the ledger
  instead of reproducing it. Recorded non-compliant, not padded.
- Gemma 4 26B completes with perfect recall but needed 18-20 turns for
  16 files: it occasionally calls hallucinated file names, recovers on
  the "no such file" reply, and finishes within the turn budget.

## Audit replay profile: A100

The replay profile (AuditBench protocol) scripts every
turn of the same audit-shaped conversation, so the server is measured
with zero dependence on the model holding the tool-loop protocol.
Harness commit `03b9b2c`, vLLM 0.27.1, serving-default cache pins unless
stated. Replays/hour is not comparable to conversations/hour: probe
turns decode almost nothing and the verdict decode is forced toward the
full 16,384-token cap.

### qwen3.8 align-APC trial

Same server and weights, only `VLLM_PREFIX_CACHING` differing. Both legs
process 1,676,647 prompt tokens per replay (10.2x the 164,175-token
final depth); the APC leg serves 89.9% of them from cache.

| Cache mode | Turn walls (16 turns) | Matched-verdict wall | Cached | Verdict turn (matched sample) |
| -- | -- | --: | --: | -- |
| off | grows 12.8 -> 84.8 s | 845.0 s | -- | 1,076 tok in 119.4 s |
| align APC on | 12.8 s cold, then flat 4.3-7.4 s | 137.6 s | 0.899 | 1,063 tok in 36.0 s |

Matched on near-identical verdict lengths, align-APC is 6.1x end to end;
the final-turn prefill alone is 11.5x cheaper (84.8 s -> 7.4 s). The
per-turn walls are byte-consistent across samples in both modes.

Two caveats before trusting the summary medians (6.58 vs 4.24
replays/hour): qwen3.8 ignored the never-conclude verdict control in
three of five samples across the two legs (~1.1k-token verdicts,
`finish_reason: stop`), and the same fixture variants that stopped short
cache-off filled ~16k tokens under APC -- align mode's documented
output-changing behavior showing up as different verdict lengths. The
medians therefore mix verdict lengths; the matched-sample comparison
above is the honest ratio.

The correctness gate ran the same day (four server cycles: cold/hit in
both orders across an APC-on restart, plus a cache-off control pair):
conversation A byte-identical cold-vs-hit and identical to cache-off;
conversation B diverged, but diverged identically in the cache-off
control, so it is CUDA baseline nondeterminism, not a cache defect;
semantic needles 8/8 across all legs; shared-prefix TTFT 5.29 s cold vs
0.15 s hit. Measured align pool cost -0.88% (742,613 vs 749,204
tokens). On this evidence the conf pin flipped to
`VLLM_PREFIX_CACHING=1`. The adopted operating point has since run its
own conversation canonical -- the 21.9 conv/h fleet-table row above;
the retired cache-off default measured 4.1 conv/h.

### First GLM serving data, and the qwen3.6 anchor

| Profile | Cache pin | Replays/h | Turn walls | Cached | Verdict decode |
| -- | -- | --: | -- | --: | -- |
| `qwen3.6-35b-a3b-awq` | APC on | 18.3 | flat 2.3-2.5 s | 0.824 | 16,384 tok @ 98.0 tok/s |
| `glm4.7-flash-awq` | APC on | 6.43 | 5.2 -> 9.2 s | 0.902 | 16,384 tok @ 35.3 tok/s |

- GLM 4.7 Flash finally has serving numbers: the server side is healthy
  (0.902 cached, clean 16k verdict decode). Its conversation-profile
  non-compliance is model protocol behavior, not a serving defect.
- The qwen3.6 anchor shows what a cache-friendly MoE looks like under
  replay: turns are nearly free and 85% of the 196.7 s wall is the
  forced verdict decode itself (167.0 s).

## Concurrent audit replay profile: A100

Canonical replay-concurrent run (AuditBench protocol) on the audit
workhorse at its align-APC serving default, vLLM 0.27.1. The profile is
the multi-agent audit shape: N scripted replays at once share the 32k
evidence prefix (same repository, distinct per-agent file chains), every
probe turn decodes a full 1,024-token agent turn, and the verdict decode
is forced toward the 16,384-token cap. Replays/hour here is not
comparable to the 1x replay profile above (32-token probes there).

### qwen3.6-35b-a3b-awq APC -- concurrent replay canonical

Context 262,144, APC-on pool 2,714,989 tokens, seqs 8; the 184,320-token
per-stream demand fits all three candidate stream counts.

| Streams | Batch wall | Replays/h | Scaling | Turn walls first -> final | Verdict decode | Cached |
| --: | --: | --: | --: | -- | --: | --: |
| 1 | 308 s | 11.70 | 1.00 | 9.6 -> 11.3 s | 109.9 tok/s | 0.897 |
| 2 | 388 s | 18.57 | 1.59 | 10.3 -> 15.2 s | 87.6 tok/s | 0.906 |
| 4 | 540 s | 26.67 | 2.28 | 11.6 -> 22.8 s | 63.1 tok/s | 0.915 |

- The A100 is still scaling at four concurrent agents (2.28x aggregate,
  per-agent latency 1.75x), where the same profile on the M5 vLLM-Metal
  host knees at two. Every turn cap-filled its 1,024 tokens and every
  verdict its 16,384 in all batches, so the rates buy full work.
- Batch walls are byte-consistent across samples (ranges under one
  second at every stream count) -- the fixture and scheduler are
  deterministic at this operating point.
- Shared-prefix seeding is visible per stream: in each batch one stream
  prefills the 32k evidence cold and the others start with 32,736
  cached tokens; cached fraction rises with streams (0.897 -> 0.915)
  but stays minor against a ~167k final conversation, same as on the
  M5.

Raw artifacts are retained outside the repository.

## Audit conversation and replay: RTX PRO 3000

Canonical clean-fixture runs (finalized fixture, both profiles, both
cache modes, conversation and replay; 9-step chain at the 131,072
context, ~107k final depth). The earlier overnight runs at `bf27151`
predate fixture finalization and are superseded: their qwen3.5
collapses were the planted decode-control, since fixed; those JSONs
remain retained only as fixture-bug evidence.

Conversation (model-usability smoke):

- `qwen3.5-4b-awq`, APC off: **2/2 compliant**, 9/9 files and 9/9
  recall per sample, 279.8 s median, 12.9 conversations/hour.
- `qwen3.5-4b-awq`, align APC on: 0/2. It drives the chain correctly
  (one read per turn, cached fractions 0.81-0.83) and then reliably
  derails on a late turn into a 16,384-token `finish_reason: length`
  runaway that regurgitates evidence text. Same fixture, same
  temperature 0; the only variable is the cache mode. Align mode's
  documented output-changing numerics break this checkpoint's
  compliance.
- `gemma4-e2b-awq`, both modes: 0/2. It calls `read_file` on a
  filename appearing inside the evidence text instead of the
  instructed `file_001`, then gives up (9-18 s). Deterministic in both
  cache modes; the A100 26B became compliant on the clean corpus, the
  E2B did not -- a genuine capability limit of the edge variant.

Replay (scripted server benchmark, same fixture; verdict decode forced
toward the 16,384-token cap):

| Profile | Cache | Replays/h | Turn walls | Cached | Verdict decode |
| -- | -- | --: | -- | --: | --: |
| `qwen3.5-4b-awq` | align on | 7.35 | flat ~6 s | 0.700 | 37 tok/s |
| `qwen3.5-4b-awq` | off | 5.56 | 9.5 -> 39.5 s | -- | 37 tok/s |
| `gemma4-e2b-awq` | on | 10.17 | flat ~8 s | 0.847 | 55 tok/s |
| `gemma4-e2b-awq` | off | 5.89 | 8.8 -> 52.6 s | -- | 46 tok/s |

APC is worth 1.32x (qwen) and 1.73x (gemma) end to end on the resent
shape, and verdict decode is cache-neutral once the final-turn prefill
is separated out. Align-mode costs on the GDN hybrid, measured the same
day: KV pool 274,432 -> 268,147 tokens (-2.3%), decode -0.4% at 1x and
-0.3% at 2x (non-canonical decode-profile pair).

Pin decision, `qwen3.5-4b-awq`: 0 -> 1 on the morning cost math, then
**back to 0** the same day on the conversation evidence above. The
1.32x scripted-replay win does not outweigh the model reliably breaking
its own tool loop under align mode; compliance is a capability gate no
throughput number overrides. `gemma4-e2b-awq` keeps APC 1: regular
attention, no align numerics, identical (non-)compliance in both modes,
and a 1.73x replay win. Run JSONs: `~/tmp/auditbench-conv-rtx/`.

## Small-card model notes

### `qwen3.5-4b-awq`

This 4B hybrid decodes quickly because 24 of 32 layers are GatedDeltaNet
linear attention. At the retained 131,072-token point, fp8 KV and the
utilization 0.916 host profile produced a 274,432-token pool, enough for two
full audit streams. The native 262,144-token context remains an explicit
single-stream experiment rather than the serving baseline.

### `gemma4-e2b-awq`

Gemma's multimodal PrefixLM path requires vLLM-selected Triton attention and
automatic 16-bit KV. Its 450,444-token pool is ample for two 131,072-token
requests. It leads decode and cold 32k audit throughput, while Qwen overtakes
it on late-audit calls. Structured tool calling remains verified through the
bundled `gemma4` parser.

## Retired A100 harness notes

The measurements below predate AuditBench v1. They remain only as historical
architecture and failure evidence; none of their rates feed the canonical
tables above or the cross-runtime overview.

### `qwen3-coder-30b`

The process used 29.53 GiB for weights and 47.01 GiB for KV. Its four-stream
decode result was 505 tok/s aggregate, or 3.44x the single-stream rate.

Concurrency behaves differently by phase. Aggregate prefill stayed flat:
2,745 tok/s for one stream, 2,795 for two, and 2,764 for four. Prefill was
already compute-saturated, while decode still benefited from batching and
phase overlap.

Because 513,408 is less than two times 262,144, two absolute-maximum requests
cannot coexist. At the earlier 0.90 utilization, four concurrent 140k prompts
requested 563k tokens against a 444k pool and all completed through staged
admission. Exceeding the pool queued rather than failed.

fp8 KV would double the pool but is unavailable on sm_80.

### `glm4.7-flash-awq`

Three samples agreed within 0.1%. Decode was about 40% slower than
Qwen3-Coder. AWQ weights are dequantized through Marlin on sm_80, which has no
native 4-bit path, and Triton MLA is the only legal attention backend:

```text
out of potential backends: ['TRITON_MLA']
```

The MLA workspace requires utilization 0.92 rather than 0.98, but the remaining
KV pool still holds 5.28 configured contexts. The cap costs no request capacity.

### `qwen3.6-35b-a3b-awq`

Three samples kept prefill and decode within 1.6%. This is the fastest A100 row
because only 3B of its 36B parameters are active per token and only 10 of its
40 layers keep a growing cache. Long prefill is 1.36x the next-best row and
roughly twice the other 30B-class rows. The KV pool holds 10.48 configured
contexts.

The first four-stream benchmark after startup measured 2.33x, while the next
two both measured 3.28x. Use the warm concurrency result rather than averaging
the cold run into it.

vLLM reconciles the hybrid cache explicitly:

```text
Setting attention block size to 1056 tokens to ensure that attention page
size is >= mamba page size.
Padding mamba page size by 0.76% to ensure that mamba page size and
attention page size are exactly equal.
```

This checkpoint loads as `torch.float16`, not bfloat16, because its AWQ
configuration requests it.

### `qwen3.8-27b`

Three samples kept prefill within 1.2% and decode and concurrency within 0.1%.
Every one of its 27B dense parameters participates in each token. The A100 has
no native FP8 compute, so vLLM selects
`MarlinFP8ScaledMMLinearKernel` and warns that weight-only FP8 can degrade
compute-heavy workloads. The result is 48 tok/s decode and 2.45k tok/s long
prefill, versus 145 and 12.36k for Qwen3.6.

Its useful property is cache capacity. A 46.26 GiB pool holds 749,204 tokens,
or 2.86 native contexts. Two 262,144-token sequences fit with 224,916 tokens
left. Startup used 78,027 MiB; after the benchmark workload the process reached
80,163 MiB, still below the 81,920 MiB card total.

Two context profiles were also started and benchmarked:

| Config | Max context | KV pool | Full contexts | YaRN |
| -- | --: | --: | --: | -- |
| `qwen3.8-27b-160k` | 163,840 | 746,553 | 4.56x | no |
| `qwen3.8-27b-320k` | 327,680 | 751,873 | 2.29x | 1.25 |

vLLM logged the complete nested RoPE override for the 320k profile. Both
profiles matched the native short-workload results: about 2.98k/2.45k tok/s
short/long prefill, 48.1 tok/s decode, and 3.72x at four streams. YaRN factor
1.25 therefore had no measurable short-context throughput cost.

The pool ratios establish capacity, but concurrent full-length requests have
not been timed. One 512 Ki-token sequence would fit the same pool; two would
not. Live requests confirmed `message.reasoning` and structured tool calls.

### `gemma4-26b-a4b-awq`

Three cold samples kept prefill within 1%. Gemma has the fastest decode and the
slowest long prefill apart from Qwen3.8. Both results follow from Triton
attention, which its multimodal prefix attention requires. For a
prompt-dominated workload, this is the wrong side of the trade.

Prefix caching is enabled, so only the first prefill after a start is valid.
The second run measures cache hits. Its concurrency result has the opposite
rule and should come from the second run.

### Full-context comparison

The standard harness tops out around 66k prompt tokens. These separate tests
measure the long-context workload the model configurations actually advertise.
Prompt text and token counts are identical where the tokenizer permits it.

| Model | Prompt | 1 request | 2 concurrent | Aggregate |
| -- | --: | --: | --: | --: |
| `qwen3.6-35b-a3b-awq` | 249,684 | 48.6 s | 96.9 s | 5,156 tok/s |
| `glm4.7-flash-awq` | 192,718 | 116.2 s | 229.2 s | 1,681 tok/s |
| `gemma4-26b-a4b-awq` | 249,684 | 164.1 s | 326.1 s | 1,531 tok/s |

Qwen3.6 is the clear full-context throughput leader. At approximately 250k it
is 3.4x Gemma's aggregate rate. GLM cannot run the same token count because its
native maximum is 202,752.

Two concurrent requests took 1.00-1.01x as long as running them sequentially
for all three models. Neither queued and neither was preempted; both shared an
already saturated GPU. Concurrency buys nothing at full context.

That is the endpoint of a curve rather than a universal rule. On Qwen3.6,
speedup over sequential execution decays as prompts grow:

| Prompt | N=1 | N=2 | N=4 | Latency at N=4 |
| --: | --: | --: | --: | -- |
| 8,424 | 1.00x | 1.27x | 2.29x | 1.9 s to 3.3 s |
| 33,664 | 1.00x | 1.23x | 1.40x | 3.6 s to 10.2 s |
| 134,584 | 1.00x | 1.03x | 1.04x | 17.7 s to 68.1 s |
| 249,684 | 1.00x | 1.00x | - | - |

By about 128k, four concurrent requests buy 4% throughput while costing 3.8x
per-request latency. Below about 32k, batching still pays.

`--max-num-seqs` is an admission ceiling, not a target. Leaving the large-card
default at 8 lets small jobs batch deeply while a 250k job effectively runs
alone. Clients should choose actual concurrency from workload size.

### The KV pool controls admission

The default of eight sequences exceeds what most pools hold at full context:

| Model | Full configured contexts in pool |
| -- | --: |
| `qwen3-coder-30b` | 1.96x |
| `qwen3.8-27b` | 2.86x |
| `glm4.7-flash-awq` | 5.28x |
| `gemma4-26b-a4b-awq` | 7.15x |
| `qwen3.6-35b-a3b-awq` | 10.48x |

That is not a misconfiguration. vLLM admits only sequences for which it can
allocate blocks.

The worst case was Qwen3-Coder with four concurrent 249,787-token requests:
999,148 tokens of demand against a 513,408-token pool.

```text
Running: 2 reqs
Waiting: 1..3
```

The scheduler never ran more than two requests and queued the rest. The log
showed zero preemptions, so no work was recomputed. Oversubscription increased
tail latency from 323 to 659 seconds but did not thrash.

It also added no separate throughput loss. Four requests measured 0.91x
sequential throughput and two measured 0.92x. The loss belongs to concurrent
full-context attention on this model, not to queueing.

KV cost explains why full-context concurrency is free for one model and not
another:

| Model | KV per token | N=2 at ~250k |
| -- | --: | --: |
| `qwen3.6-35b-a3b-awq` | 20 KiB | 1.00x |
| `qwen3-coder-30b` | 96 KiB | 0.92x |

Two Qwen3-Coder sequences put about 48 GiB of cache under the attention kernel,
while Qwen3.6's cheap hybrid cache breaks even.

Short-prompt prefill does not extrapolate. Qwen3.6 falls from 12,355 tok/s at
about 66k to 5,137 at 250k; Gemma falls from 5,067 to 1,522. Attention cost
grows with sequence length, preserving the ranking but widening the gap from
2.4x to 3.4x.

The practical full-context conclusions are:

- `qwen3.6-35b-a3b-awq` has served two concurrent requests at about 250k and
  has memory for roughly ten configured contexts.
- `qwen3.8-27b` has measured cache capacity for two 256k requests, but that
  exact concurrent full-context load has not been timed.
- `glm4.7-flash-awq` stops at 202,752 tokens.
- `qwen3-coder-30b` cannot hold two 256k requests; the second queues.

## Benchmark pitfalls

These errors produced plausible but meaningless numbers:

- Repetitive filler sent a small model into a repetition loop at temperature
  zero. `bench.py` generates varied lines instead.
- Letting the model choose when to stop produced a 35-token decode sample.
  `ignore_eos` now forces exactly `max_tokens`.
- Comparing durations across tokenizers treated different token counts as the
  same work. Compare tok/s and retain each prompt's actual token count.

AuditBench prevents the two run-order artifacts seen here: every sample differs
from its first token so prefix caching cannot collapse the prompt, and stream
counts are interleaved across samples rather than copied from separate runs.

### A power-capped laptop invalidates the small-card results

One historical small-card measurement set was about 10x too slow because the
GPU was held at 35 W against a 60 W default and an 85 W maximum. Those results
were discarded. The canonical AuditBench campaign used the proper adapter.

The failure looked healthy: temperature was 56 C, GPU utilization was 100%,
and repeated samples agreed within 1%. It also survived
`powerprofilesctl set performance`.

The useful signals are `clocks_throttle_reasons.active = 0x4` (`SwPowerCap`)
and an enforced limit below the default:

```bash
nvidia-smi --query-gpu=enforced.power.limit,power.default_limit,power.max_limit,\
clocks_throttle_reasons.active --format=csv
```

The machine was on a USB-C power contract of about 39 W for the whole laptop,
so `nvidia-powerd` had no power to allocate. The proper adapter raised the GPU
limit to its normal dynamic range.

The platform profile is not the fix. With the adapter connected, three samples
each under `performance` and `balanced` overlapped, and one balanced run
received a higher GPU limit. The launcher therefore does not mutate
machine-wide power settings.

Dynamic Boost still makes valid small-card results noisy. AuditBench therefore
interleaves stream counts and reports three-sample medians with retained
ranges instead of relying on one favorable run.
