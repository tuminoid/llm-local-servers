# Local model serving: an introduction

A from-scratch reference for how local inference actually works and why the
servers in this tree are configured the way they are. The numbers used as
anchors are real measurements from this repository's hosts; the current
values live in the per-runtime `BENCHMARKS.md` files and the benchmark
protocol in [the AuditBench protocol](https://github.com/tuminoid/llm-audit-bench).

## The three currencies

Every local model spends three things:

- **Memory** -- does it fit at all, and with how much context?
- **Bandwidth and compute** -- how fast does it read prompts and generate?
- **Bits** -- quantization trades a little correctness for a lot of the
  other two.

Every architecture trick and every config knob in this tree is a way of
spending less of one currency, usually by paying in another.

## Memory: weights plus KV cache

**Weights** are the easy part: parameters times bits. At 4-bit, one
parameter costs half a byte, so a 27B model is ~15.5 GiB and a 123B model
is ~65 GiB. This cost is fixed the moment the model loads.

**KV cache** is the sneaky part. A transformer generating token 50,000
attends over the 49,999 tokens before it. Rather than recompute them every
step, each attention layer stores a key/value pair per token -- the KV
cache. It grows with every token of every active request:

```text
bytes per token = attending layers x KV heads x head dim x 2 (K+V) x 2 B
```

This is rent paid per token of context, and the architecture sets the
rate. Examples from models served or evaluated on this repo's hosts, all
at 4-bit weights:

| Model | Attention layout | KV rate | One 262k context |
| -- | -- | --: | --: |
| Devstral 2 123B | 88 layers, all full | 352 KiB/tok | 88 GiB |
| Devstral Small 2 24B | 40 layers, all full | 160 KiB/tok | 40 GiB |
| Gemma 4 31B | 10 of 60 full, rest sliding | 160 KiB/tok | 40 GiB |
| Qwen3.8 27B | 16 of 48 full | 64 KiB/tok | 16 GiB |
| Qwen3.6 35B A3B | 10 of 40 full, rest GDN | 20 KiB/tok | 5 GiB |

Same context, an 17x spread in rent. This is why "does model X fit" has no
answer without also asking "at what context, and how many at once".

## Attention architectures: the rent-reduction tricks

- **Full attention**: every layer sees every token. Best possible recall
  of far-away context, maximum KV rent. Both Devstrals pay full rate on
  every floor.
- **Sliding window** (Gemma 4): most layers only attend to the last ~1,024
  tokens -- like remembering only the current page. Their cache is a small
  fixed buffer; only the few global layers pay per-token rent. The
  sliding layers add a bounded per-request cost (a few GiB), never a
  per-token one.
- **Linear attention / state space** (Qwen3.6's GatedDeltaNet, Nemotron's
  Mamba2): these layers keep a fixed-size running summary regardless of
  context length -- a notebook that gets rewritten, not a pile that grows.
  Zero growing rent; only the few true attention layers grow. This is how
  a 35B model fits five whole 262k conversations in ~53 GiB.
- **Mixture of Experts** (MoE, the `A3B` suffix: ~3B active): the MLP
  weights are split into many experts and each token routes through a few.
  MoE does not reduce KV rent or resident memory -- all experts must sit
  in RAM -- it reduces *bandwidth* per token, which is a speed trick
  (below).

A caution that follows: architectural recall is not free either way.
Sliding-window and state-space layers compress far-away context; whether
that hurts a given workload is an empirical question, not a spec-sheet
one.

## Speed: prefill and decode hit different walls

**Prefill (reading the prompt) is compute-bound.** All prompt tokens are
processed in parallel, so the GPU's arithmetic is the limit. Two measured
consequences:

- Concurrent prefills do not overlap: four 246k-token prefills take
  exactly four times the wall time of one.
- Prefill slows as context grows, because attention work scales with what
  is already resident: Qwen3.6 measured 2,807 tok/s at a 32k prompt,
  1,087 at 128k, 660 at 246k.

**Decode (generating) is bandwidth-bound.** Every new token reads all
*active* weight bytes once. Single-stream decode is roughly memory
bandwidth divided by active bytes:

- Qwen3.6 MoE, ~3B active (~2 GiB/token): 122.8 tok/s measured.
- Qwen3.8 dense 4-bit (~15.5 GiB/token): 32.5 tok/s measured.
- A dense 123B at 4-bit (~65 GiB/token): single digits, on any runtime,
  because the silicon's bandwidth is the wall.

Three corollaries that spec sheets hide:

- **Bits buy decode, never prefill.** Halving weight bits roughly doubles
  decode (Qwen3.8 went 18.1 -> 32.5 tok/s from 8-bit to 4-bit) while
  prefill stays identical, because the multiply happens after dequant.
- **Decode slows as resident context grows**, because each token also
  re-reads the KV cache: Qwen3.6 decodes 122.8 tok/s with a short prompt,
  ~59 with 32k resident, ~16 with 131k resident. A "decode ceiling"
  benchmark flatters every real long-context workload -- which is why the
  audit benchmark's production metric is calls/hour, not tok/s.
- **Speculation buys decode, never prefill.** During bandwidth-bound
  decode the arithmetic units are mostly idle, so a small draft model
  can propose several tokens and the target verifies them all in the
  same weight sweep -- measured 2.4x on A100 qwen3.8 with its DFlash 2
  drafter at one stream. The gain shrinks as batching or resident
  context consume the idle margin (neutral by ~131k resident), prefill
  is untouched, and greedy output stays byte-identical because the
  target vetoes every wrong guess. Beware: some runtimes enable a
  packaged draft head silently, so a published decode rate is not
  always a plain rate.

**Batching is where dense and MoE trade places.** Concurrent dense streams
share one weight read per step, so concurrency is nearly free until the
scheduler saturates (Qwen3.8 scaled 3.65x at 4 streams). MoE streams route
to different experts, so there is less sharing: Qwen3.6 saturates at 4
streams (~315 tok/s aggregate) and more streams only dilute per-stream
speed. Neither effect improves a prefill-dominated workload: for 32k-in /
1k-out audit calls, measured calls/hour is flat from 1 to 4 streams --
concurrency buys burst absorption, not throughput.

## Fitting math on a real host

macOS gives the GPU a recommended working-set limit below physical RAM
(~106 GiB on a 128 GB M5 Max). The vLLM-Metal launcher plans the whole
footprint up front:

```text
need = weights + ~5 GiB engine overhead + slots x context x KV rate
```

and refuses to start when it does not fit. Worked examples:

- **Qwen3.6 35B A3B**: 19.5 GiB weights + 5 GiB + 5 slots x 262k x
  20 KiB = ~53 GiB. Five full-context requests, comfortably.
- **Devstral 2 123B**: 65 GiB weights + 5 GiB + one 131k context at
  352 KiB = ~114 GiB. Over the limit before a single full request --
  the model is servable on this host only at reduced context (~64k).

The planned-up-front property matters as much as the number: a runtime
that grows memory with the request instead (the Ollama MLX runner) turns
the same arithmetic into a mid-request hard reset rather than a refused
start. That difference is why this tree treats bounded memory as a
selection criterion, not a nicety.

## Context length: RoPE, and stretching it with YaRN

The KV arithmetic above answers "how much context can I afford". A
separate limit answers "how much context is the model allowed to use",
and it is not a memory question at all: it is baked into the weights.

**RoPE (rotary position embedding)** is how nearly every current model
knows token order. Instead of adding a position vector, it *rotates*
each query and key vector by an angle proportional to the token's
position, across many frequency bands at once -- fast-rotating bands
resolve neighbours, slow-rotating bands separate the far past. Attention
compares two rotated vectors, so only their relative angle matters,
which is what lets the same mechanism work anywhere in the sequence.

The catch is that training only ever showed the model angles up to its
**native context** (`max_position_embeddings` in `config.json`; 262,144
for Qwen3.8-27B). Feed it token 400,000 and the rotations fall outside
everything it has seen, attention scores degrade into noise, and output
collapses -- not gracefully, and not always visibly at first. Serving
past the native length therefore requires rescaling the angles, never
just raising a limit.

### What YaRN does

YaRN (Yet another RoPE extensioN) *interpolates* positions so a longer
sequence still lands inside the trained angular range. Its refinement
over naive interpolation is that it treats frequency bands differently:
high-frequency (local) bands are left nearly alone so neighbouring
tokens stay distinguishable, while low-frequency (long-range) bands are
compressed to cover the new length, plus a small attention-temperature
correction for the entropy change at longer sequences.

The knob is **factor** -- target divided by native. It is arithmetic,
not a tuning dial:

| Profile | Target context | Native | Factor |
| -- | --: | --: | --: |
| `qwen3.8-27b` | 262,144 | 262,144 | none |
| retired 320k | 327,680 | 262,144 | 1.25 |
| `qwen3.8-27b-512k` | 524,288 | 262,144 | 2.0 |
| retired 720k | 737,280 | 262,144 | 2.8125 |

Scaling here is **static**: configured at startup and applied to every
request, including a 2,000-token one. That is the tax below -- some
models instead ship dynamic scaling that engages only past the native
length, but that is a model/engine property, not something to assume.

### Configuring it in this tree

Three settings, all in the model conf, because the extension is a
property of the weights and must travel with them:

```bash
VLLM_MAX_LEN="${VLLM_MAX_LEN:-524288}"
VLLM_ALLOW_LONG_MAX_MODEL_LEN="${VLLM_ALLOW_LONG_MAX_MODEL_LEN:-1}"
VLLM_HF_OVERRIDES='{"text_config":{"rope_parameters":{...,"rope_type":"yarn","factor":2.0,"original_max_position_embeddings":262144}}}'
```

`VLLM_MAX_LEN` alone is the classic mistake: it raises the ceiling
without rescaling anything, so the server accepts prompts it cannot
position-encode. The override JSON is what actually enables YaRN, and
`VLLM_ALLOW_LONG_MAX_MODEL_LEN` is the acknowledgement that the
requested length exceeds the checkpoint's own declaration.

The override must match the checkpoint's real config *shape*, which is
architecture-specific -- for Qwen3.8 the fields are nested under
`text_config.rope_parameters` (it is multimodal, with mrope sections and
a partial rotary factor to preserve), not the flat `rope_scaling` many
guides show. Read the model's `config.json`; a wrong shape is silently
ignored or subtly wrong rather than a loud failure. Confirm at startup
that the engine logged the override and resolved the intended
`max_seq_len`.

### Two things extension does not do

**It does not add capacity.** The KV pool is fixed by GPU utilization
minus weights -- roughly 742k-752k tokens for Qwen3.8 on the A100
regardless of `max_model_len`. Raising the limit only permits a *single*
sequence to grow past the native length; the aggregate stays put. At
512k that means one ~512k conversation plus ~218k for everything else,
not more total room. vLLM also requires KV for one whole `max_model_len`
sequence or it refuses to start, so an aggressive factor can cost
concurrency outright.

**It does not make depth fast.** Prefill is compute-bound and decode
slows as the cache grows: Qwen3.8 on the A100 prefills ~2.45k tok/s, so
filling 400k costs ~165 s before the first token. Extension buys reach,
never speed.

### Pros, cons, and when to reach for it

Good: no retraining, no new artifact, no extra memory for the mechanism
itself, one config file, and reversible -- the native conf stays the
control. Low factors are cheap; the retired 1.25 profile measured *no*
short-context throughput penalty (BENCHMARKS.md).

Bad: quality degrades as factor rises, and the degradation is in
long-range attention -- exactly the faculty a deep audit needs. Static
scaling taxes the whole early conversation, which is most tokens. Worst,
the failure is quiet: a 512k config that parses, serves, and reasons
slightly worse at depth looks fine on a throughput sweep. That is why
any extended profile here is exploratory until a deep AuditBench run
plus Capability Check v1 pass at the new depth, and why factor is kept
as low as the workload allows rather than as high as the pool permits.

Alternatives, roughly in order of preference for this fleet:

1. **Pick a natively-long model.** Trained length beats interpolated
   length at equal numbers, every time.
2. **Stop resending everything.** Compaction, summarizing closed
   threads, or retrieving evidence on demand attacks the cause. A
   conversation that needs 400k because it re-sends its own history is
   a client problem wearing a serving costume.
3. **Cut the cost of depth instead of raising the ceiling.** Automatic
   prefix caching does not extend context, but it makes a growing
   conversation affordable -- worth 6.1x end to end on qwen3.8 (see
   README).
4. **Choose a cheaper KV architecture.** A model at 20 KiB/token
   affords far more real depth than one at 64 KiB/token, with no
   scaling at all.
5. **Then** extend with YaRN, at the smallest factor that fits the job.

## Variants: same architecture, different upbringing

A model family page lists a dozen artifacts -- Base, Instruct, Chat,
Thinking, Coder, community tunes -- before any quantization enters the
picture. Variants are **different weights from different training**;
quantization (next section) merely compresses whichever one you picked. A
4-bit MLX file and a bf16 safetensors of Qwen3.8-Instruct are the same
model; Qwen3-Coder is a different model that shares an architecture.

The training pipeline creates them in stages, each stage adding machinery
the previous one lacked:

1. **Base**: pure next-token prediction over a trillions-of-tokens
   web/code mix. It *continues text* rather than answering -- ask it a
   question and it may continue with more interview questions. Released
   mostly as raw material for fine-tuning.
2. **Instruct / Chat / -it**: supervised fine-tuning on
   instruction-response pairs plus preference optimization. This stage
   bakes in the chat template and the **tool-call format** -- the exact
   token patterns that parsers like `qwen3_xml` and `gemma4` match are
   trained here, which is why structured tool calling is a variant
   property, not a server feature.
3. **Thinking**: reinforcement learning on verifiable tasks teaches the
   model to emit a private reasoning trace -- draft, check, backtrack --
   before the answer. It pays on multi-hop problems (tracing
   reachability, interacting constraints) and buys nothing on retrieval
   or formatting. The trace costs *decode tokens*, the expensive currency
   on every host in this tree, and is dropped from context between turns.
4. **Domain tunes** (Coder, cyber, medical): continued pretraining or
   extra SFT on a domain mix. The reflexes improve; the risk is that the
   tune *destroys* earlier-stage machinery. Both failure shapes have been
   measured here: cybersecurity tunes (Foundation-Sec, Antares) lost
   reliable tool calling, and Qwen3-Coder ships without the thinking
   mode. A domain tune is only useful if it keeps the stages beneath it.

**Thinking is sometimes a mode, sometimes a variant.** Hybrids train both
behaviors into one checkpoint and select per request -- Qwen3.8's
`reasoning_effort` (`low`/`medium`/`xhigh`) steers trace length at
serving time. Other vendors ship separate Instruct and Thinking weights.
The test: if turning thinking off is a request parameter, it is a mode;
if it is a different repository, it is a variant. Hybrids are strictly
more convenient to serve -- one pool, one profile, per-request
quality/throughput choice with no model swap.

**Not variants**: quantizations, context profiles (a YaRN 320k config is
the same weights with different RoPE scaling), and serving operating
points. QAT sits in between -- genuinely retrained weights, but trained
to survive quantization while behaving like the original.

**Picking a combination for a workload**, with the audit pipeline as the
worked example, ordered by how disqualifying the absence is:

1. **Schema-reliable structured output** -- the pipeline runs on
   structured verdicts; a model that fumbles them is out regardless of
   intelligence. Single-emission reliability, an instruct-stage property.
2. **Steerable thinking** -- cheap low-effort passes for high-recall
   triage, expensive high-effort adjudication for precision. The effort
   knob is a quality/calls-per-hour dial set per request.
3. **Code-heavy pretraining** -- table stakes; every modern family has
   it. Reading comprehension of code comes from pretraining, not from a
   Coder tune, whose extra training targets *generation* workflows.
4. **Long context with affordable KV** -- economics, not identity.
5. **A Coder or domain tune** -- only if it demonstrably keeps 1 and 2,
   which in practice it often does not.

"Agentic" tuning -- sustaining plans across many tool-call turns,
recovering from errors -- matters for interactive agent sessions, not for
one-shot pipeline calls. A single served model often does both duties, so
it still needs the competence, but a one-shot workload should not pay a
capability price (like losing thinking) to get it.

## Quantization: the quality axis

Training produces bf16 weights (2 bytes each). Quantization re-stores
them on a coarser grid; the model then runs with rounding noise in every
matrix. Quality is a question of where the noise lands.

| Bits | Reality |
| -- | -- |
| bf16 | Reference quality. For serving, mostly wasted bandwidth. |
| fp8 / int8 | Effectively lossless in practice. |
| 6 / 5-bit | Insurance tier; barely worse than 8, slimmer. |
| 4-bit | The sweet spot with a good method. Most of this fleet. |
| 3-bit | The cliff edge; visible brittleness begins. |
| 2-bit | Desperation. Loads, then fails subtly everywhere. |
| 1/1.58-bit | Not a conversion; such models are trained that way. |

**Why naive rounding fails**: weight matrices are mostly small values plus
rare, hugely important outlier channels. One shared grid stretches to fit
the outliers and crushes everything else. Every serious method protects
what matters:

- **Group scales** (plain MLX 4-bit affine, group size 64): every 64
  weights get their own grid; an outlier only ruins its own group.
- **AWQ** (activation-aware): calibration data reveals which channels get
  multiplied by large activations; those are rescaled into the fine part
  of the grid before rounding. Weights-only, so it speeds decode and
  leaves prefill unchanged.
- **GPTQ**: rounds column by column and nudges the remaining weights to
  cancel each rounding error.
- **K-quants** (GGUF `Q4_K_M`): mixed precision inside one file --
  sensitive tensors get more bits.
- **NVFP4 / MXFP4**: 4-bit floating point with per-block scales; float
  spacing is dense near zero, matching weight distributions, and the
  format is hardware-native on recent NVIDIA GPUs.
- **QAT** (quantization-aware training): the author simulates rounding
  *during* training so the network learns weights that sit comfortably on
  the coarse grid. 4-bit QAT typically measures near bf16 -- it moves the
  cliff down a bit-level or two. Only the model's author can do it; when
  an official QAT artifact exists at the same bits, prefer it.

Embeddings, layernorms, and the output head stay high precision in all of
these -- they are few bytes and disproportionately damaging to round.

**The KV cache can be quantized too**, independently of weights: q8 KV is
near-free; q4 KV specifically erodes long-range retrieval -- noise in the
memory rather than the brain. Long-context workloads should be
conservative here.

**Where quality loss actually shows up**: averaged metrics barely move at
4-bit; the damage lives in the tails. Exact-format output degrades first
(tool-call XML/JSON, code identifiers), long generations compound small
per-token error rates, and long-context retrieval suffers before short
chat does. This is why models here are gated on demonstrated tool-call
correctness and workload behavior, not on a perplexity chart -- and why
2-bit "it loads!" artifacts are stunts, not serving profiles.

## Formats: how the same weights get packaged

Quantization decides the bits; the file format decides which engine can
eat them. The same "4-bit class" model commonly exists in three or four
incompatible packagings:

- **HF safetensors**: the interchange format of the ecosystem. bf16, FP8,
  AWQ, and GPTQ checkpoints ship this way, and vLLM consumes them
  directly. Safe to memory-map, no code execution on load.
- **GGUF**: llama.cpp's single-file format -- weights (usually K-quants),
  tokenizer, and metadata in one blob. What the Ollama registry mostly
  serves and what runs anywhere llama.cpp runs.
- **MLX checkpoints**: safetensors arranged for Apple's MLX arrays plus a
  config, typically group-scale affine 4/8-bit from `mlx-community`.
  What vLLM-Metal and mlx-lm consume.
- **NVFP4 safetensors**: block-scaled 4-bit float artifacts. Hardware
  native on recent NVIDIA GPUs; on this Mac they exist only as the Ollama
  registry's special MLX-runner artifacts, and the plain mlx-lm loader
  cannot read the NVIDIA-published ones at all.

Format is not quality: a Q4_K_M GGUF, an MLX 4-bit, an AWQ, and an NVFP4
of the same model are all one quality tier. Format is *compatibility*,
and every conversion is a separate artifact that needs its own pinned
revision -- one model, four different sha-addressable things.

## Engines: same physics, different management

All engines obey the physics above. What they differ in is memory
*management* and request *scheduling*, which is where operational safety
and multi-request throughput come from:

| Engine | Eats | Scheduling and memory |
| -- | -- | -- |
| llama.cpp (inside Ollama) | GGUF | Static per-slot KV allocation; can split layers CPU/GPU when VRAM runs out; N parallel slots multiply the allocation |
| Ollama MLX runner | registry NVFP4 safetensors | Fast single stream on Apple Silicon; serializes requests to one slot; memory grows with the request, unbounded |
| vLLM (CUDA) | HF safetensors: bf16, FP8, AWQ, GPTQ | Paged KV pool shared across requests, continuous batching, chunked prefill; the production-server feature set |
| vLLM-Metal | MLX checkpoints | vLLM's scheduler and paged KV with MLX as the execution backend; whole footprint planned at startup |
| LM Studio / mlx-lm | MLX, GGUF | Interactive single-user serving |

The load-bearing distinctions:

- **Paged KV pool vs static slots.** vLLM allocates one shared pool and
  pages requests into it, so the pool can hold "4.8 full contexts" and
  admission is governed by actual demand. llama.cpp-style engines
  allocate each slot's full context up front, so parallelism multiplies
  memory whether or not the requests are long.
- **Bounded vs growing memory.** vLLM-Metal plans and verifies the whole
  footprint before serving; the same near-full-context workload that a
  growing-memory runner turned into a host reset completes inside a flat,
  pre-declared budget.
- **CPU offload** exists only on the llama.cpp path, and it is a cliff,
  not a slope: a 27B that fits 26 of 66 layers on a 12 GiB card decodes
  at ~5.7 tok/s -- it runs, but at CPU speed.

## Hardware: the three hosts in this tree

| | RTX PRO 3000 laptop | A100 80GB (remote) | M5 Max 128 GB |
| -- | -- | -- | -- |
| Memory | 12 GiB dedicated VRAM | 80 GiB HBM | ~106 GiB usable of 128 GiB unified |
| Bandwidth | modest GDDR | ~2 TB/s | 614 GB/s, shared with CPU |
| Sweet spot | 4-9B AWQ, full GPU | 30B-class FP8/AWQ, huge KV pools, real concurrency | big-capacity / low-bandwidth cases: MoE, long context |

The three hosts sample three different corners of the currency space:

- **The laptop GPU** is compute-rich but memory-poor: it prefills fast
  for its size, but everything -- weights plus KV -- must fit in 12 GiB,
  so it serves small dense models whole or big ones at offloaded-cliff
  speeds.
- **The A100** is rich in both: it holds a 30B-class model at FP8 with a
  multi-million-token KV pool, and its bandwidth keeps dense decode
  respectable at high concurrency. This is what datacenter serving looks
  like.
- **The M5 Max** inverts the laptop: enormous capacity, moderate
  bandwidth. It is the only host here that can even load a 65 GiB
  checkpoint, but bandwidth caps dense decode well below the A100. Its
  natural tenants are exactly the ones this tree converged on: MoE
  models (tiny active set, decode stays fast), state-space/sliding
  hybrids (tiny KV rent, huge contexts), and capacity experiments no
  12-80 GiB card can attempt. Unified memory also means no CPU/GPU copy
  and no "fits in RAM but not VRAM" gap -- the whole 106 GiB budget is
  the GPU's.

One rule of thumb ties it together: **memory size gates what loads,
bandwidth gates decode, compute gates prefill** -- and the engine decides
how gracefully you hit each limit.

## Putting it together

| You want | You spend | Example |
| -- | -- | -- |
| Fit at all | weight bits | 123B exists locally only because 4-bit halves 130 GiB |
| Faster decode | active-weight bytes | 8->4-bit doubled Qwen3.8 decode |
| More context / concurrency | KV rate (architecture) | Qwen3.6's 20 KiB/tok holds 5 full 262k contexts |
| Throughput on long prompts | nothing helps but compute | prefill-bound calls/hour is flat across streams |
| Quality at low bits | a smarter method, ideally QAT | prefer `-qat` artifacts at equal bits |
| Not resetting the host | bounded, planned memory | vLLM-Metal refuses at startup; unbounded runners reset mid-prefill |

The one-line policy this fleet follows: serve 4-bit-class weights with the
best method available, keep KV at fp16/q8, spend the savings on context
and concurrency, measure with
[AuditBench](https://github.com/tuminoid/llm-audit-bench),
and let the tool-call gate decide who stays.
