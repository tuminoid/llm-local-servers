# vLLM benchmark results

Measured throughput, memory, context, and concurrency baselines for the two GPU
generations this tree is verified against. Results are grouped by host because
models are comparable only when they ran on the same hardware with the same
harness.

Use the tables at the top to choose an operating point. The later sections
preserve the measurements, architectural explanations, full-context tests, and
failure modes behind those summaries.

The A100 rows at the top use canonical [AuditBench
v2](https://github.com/tuminoid/llm-audit-bench); every later section is
AuditBench v1 or older history, never comparable with v2. The RTX PRO 3000
vLLM profiles were dropped on 2026-10-12 (two failed Capability Check v2,
Nemotron Nano was in no inventory); their rows are in git history. Retired
A100 measurements remain clearly separated later in this file and must not be
combined with canonical rates. Their top-level retained JSON on the M5 and
A100 was removed on 2026-09-30; trial-directory copies remain, and the figures
stay here and in git history.

## AuditBench v2: A100-SXM4-80GB

sm_80, 81,920 MiB VRAM, vLLM 0.31.0, Transformers 5.15.1, serving-default
cache pins. Canonical AuditBench v2 `session` profile (llm-audit-bench
2.1.0; each JSON records its harness hash), run 2026-10-10/11 from fleet
commit `ad06c70` at each conf's declared sampling. The harness measured 1
stream and the largest of 2/4/8 that fits admission and the KV pool: 16 tool
steps from 32k evidence, report at about 165k. Sessions/h is the median over
2-3 samples; complete counts sessions whose report ended on its own and
named at least 7/8 of its findings. pp512/tg128 is the llama-bench-method
reference (one stream, greedy, depth ~0), not a serving result. JSON files
are retained under `auditbench-trials/2026-10-10-v2-canonical/` on the host.
The 2026-09-27 rows on vLLM 0.30.0 (fleet `d9ad1a7`) are in git history.
`nanbeige4.3-33b-w4a16` ran 2026-10-26 on llm-audit-bench 2.4.0 from
`852441d`, its profile before a rebase onto main, under
`auditbench-trials/2026-10-26-nanbeige-hunt/` on the host.

| Runtime and profile | Context | Slots | KV pool | Sessions/h by streams | Out tok/session 1x | Prefill tok/s 1x | Report decode 1x | Complete | pp512 / tg128 | Capability v2 | Publishable | JSON |
| -- | --: | --: | --: | -- | --: | --: | --: | -- | -- | -- | -- | -- |
| vLLM `mimo-v2.6-9b-awq` | 262,144 | 8 | 2,229,526 | 1x 58.97 / 8x 93.99 | 3,263 | 5,032.5 | 109.1 | 16/27 | 7,663 / 175.5 | fail | no | `20261011T051029.048101+0000_vllm-cuda_mimo-v2-6-9b-awq_session.json` |
| vLLM `qwen3.6-35b-a3b-awq` | 262,144 | 8 | 2,797,230 | 1x 38.49 / 8x 58.67 | 5,328 | 6,219.1 | 111.4 | 27/27 | 4,591 / 152.2 | pass | yes | `20261011T053833.661461+0000_vllm-cuda_qwen3-6-35b-a3b-awq_session.json` |
| vLLM `gemma4-26b-a4b-awq` | 262,144 | 8 | 1,909,862 | 1x 37.20 / 8x 45.99 | 1,388 | 2,116.0 | 63.6 | 27/27 | 9,441 / 176.1 | pass | yes | `20261011T003536.264070+0000_vllm-cuda_gemma4-26b-a4b-awq_session.json` |
| vLLM `qwen3.8-27b-512k` | 524,288 | 8 | 779,829 | 1x 14.49 / 4x 19.55 | 5,654 | 1,718.9 | 36.7 | 15/15 | 2,519 / 49.3 | pass | yes | `20261011T014610.294573+0000_vllm-cuda_qwen3-8-27b-512k_session.json` |
| vLLM `qwen3.8-27b` | 262,144 | 8 | 954,019 | 1x 11.83 / 4x 21.48 | 10,860 | 1,827.6 | 49.8 | 15/15 | 2,870 / 75.4 | pass | yes | `20261010T220419.237789+0000_vllm-cuda_qwen3-8-27b_session.json` |
| vLLM `qwen3.8-27b-dflash2` | 262,144 | 8 | 522,956 | 1x 8.40 / 2x 13.04 | 7,744 | 1,736.4 | 22.8 | 9/9 | 2,561 / 110.0 | pass | yes | `20261010T231305.575650+0000_vllm-cuda_qwen3-8-27b-dflash2_session.json` |
| vLLM `nanbeige4.3-33b-w4a16` | 262,144 | 8 | 284,704 | 1x 7.19 | 10,566 | 918.2 | 27.7 | 2/2 | 2,836 / 71.4 | pass | yes | `20261026T160414.161697+0000_vllm-cuda_nanbeige4-3-33b-w4a16_session.json` |

- Five of eight profiles pass Capability Check v2, against three on
  0.30.0: `gemma4-26b-a4b-awq` and `qwen3.8-27b-512k` failed only on
  json_schema `whitespace_runaway` and now pass with grammar whitespace
  forbidden in their confs.
- `qwen3.6-35b-a3b-awq` is the fastest profile that passes: 38.49
  sessions/h at one stream and 58.67 at eight, every session complete.
  The campaign's first run measured 41.50 / 59.00 but left one 8x session
  incomplete (26/27, unpublishable); the row is the rerun. On 0.30.0 it
  ran 41.19 / 59.99.
- `qwen3.8-27b` now serves W4A16 (`dbirks/Qwen3.8-27B-W4A16-AutoRound`).
  Against the FP8 0.30.0 row (12.35 / 17.26) it is 4% slower at one stream
  and 24% faster at four (21.48); report decode rises from 36.7 to 49.8
  tok/s and the KV pool from 774,131 to 954,019 tokens.
  `qwen3.8-27b-512k` keeps FP8; its one-stream 14.49 is a single run
  (10.62 to 11.92 in the same week's trials).
- `nanbeige4.3-33b-w4a16` (Nanbeige4.3-33B, dense, AutoRound INT4) passes
  Capability Check v2 11 of 12 (one workflow runaway) only under 2.4.0's
  context-scaled answer cap: at the old 32,768 it deliberates selection past
  the cap on topic, failing 8 of 12 on this build and 9 of 12 on the FP8 one,
  and passes 12 of 12 twice at 65,536. One session fits the 284,704-token
  pool, so it measures one stream: 7.19 sessions/h, about 10.6k output tokens
  per session with preserved reasoning. The schema check, advisory, ran into a
  whitespace runaway.
- DFlash 2 still loses at the declared sampling: 8.40 / 13.04 sessions/h,
  report decode 22.8 tok/s. A fixed-depth decode probe of the two profiles
  as configured (2026-10-22, the vLLM 0.32.0 trial tree, not the pin; 2,048
  generated tokens per stream, no shared prefix) puts the DFlash 2 profile
  level with plain at 8k and below it from 32k at the declared sampling:
  per-stream decode x0.93 / x1.02 / x1.00 at 8k and one, two and four
  streams, then x0.70, x0.53 and x0.35 at one stream at 32k, 64k and 128k.
  Its target is still FP8, plain's is now W4A16 and decodes faster (71.0
  tok/s at 8k against 47.5 for FP8 on 0.31.0), and the drafter's sampled
  acceptance of about 2.3 tokens does not make up the difference. Greedy,
  it leads at 8k (x1.28 to x1.31) and ties at 32k with four streams
  (x1.01). The profile stays for greedy short-context use; serve plain for
  audits.
- MiMo is the fastest profile (58.97 / 93.99) but 11 of 27 sessions did
  not finish their report's findings and it fails audit fitness, so
  neither its rate nor the model is usable.
- `qwen3-coder-30b` (36.77 / 38.83 @2x, fails both tool-call checks and
  fitness) and `glm4.7-flash-awq` (11.17 / 11.09 @4x, 9 of 15 sessions
  incomplete, fails fitness) were also measured; both models were dropped
  from the A100 on 2026-10-12, and their rows here and below are in git
  history.

## TL;DR: same-hardware comparisons

All throughput figures are observed rates, not model-quality scores. Compare
rows within one host table; do not compare a Blackwell row with an A100 row.

### 80 GB A100

A100-SXM4-80GB (sm_80), 81,920 MiB VRAM. Canonical AuditBench v1 ran with
three measured samples (two, with a third only on disagreement, for the
0.30.0 rows) and the full profile at each conf's serving-default
cache pin, Transformers 5.15.1: `qwen3.6-35b-a3b-awq` and `mimo-v2.6-9b-awq`
on vLLM 0.30.0 (2026-09-25), `qwen3.8-27b` and `qwen3.8-27b-dflash2` on
0.29.0, the other profiles on 0.28.0 (each pin move re-baselined the
plain profiles within ~2%, so rows across pins compare).
`qwen3.8-27b-dflash2` is the same
weights and revision as `qwen3.8-27b` plus the pinned z-lab DFlash 2
drafter at K=7 (see the model conf); the plain profile remains the
control. The scheduler admitted eight sequences; each phase automatically
omitted stream counts that did not fit the raw KV pool.

Capacity is one proof sample at 15/16 of configured context. No row submits
queued pseudo-concurrency.

| Model | Context | Raw KV pool | Pool/context | Near-context capacity proof |
| -- | --: | --: | --: | -- |
| `qwen3.6-35b-a3b-awq` | 262,144 | 2,798,258 | 10.67x | 8 x 245,752 in 359.53s |
| `mimo-v2.6-9b-awq` | 262,144 | 2,229,526 | 8.50x | 8 x 245,751 in 389.62s |
| `qwen3.8-27b` | 262,144 | 746,456 | 2.85x | 2 x 245,748 in 326.04s |
| `qwen3.8-27b-dflash2` | 262,144 | 507,737 | 1.94x | 2 x 245,748 in 323.42s |
| `gemma4-26b-a4b-awq` | 262,144 | 1,867,456 | 7.12x | 4 x 245,774 in 625.92s |

Performance cells are median tok/s followed by `[min-max]`. Prefill generates
one token; decode generates exactly 1,024 tokens per stream.

| Model | 32k prefill | 64k prefill | 128k prefill | Decode 1x | Decode 2x | Decode 4x | Decode 8x |
| -- | --: | --: | --: | --: | --: | --: | --: |
| `qwen3.6-35b-a3b-awq` | 15,733.8 [15,731.3-15,736.4] | 12,213.1 [12,162.5-12,263.7] | 8,388.9 [8,361.9-8,415.9] | 148.49 [148.45-148.53] | 275.57 [275.27-275.87] | 511.03 [510.14-511.93] | 879.80 [876.74-882.86] |
| `mimo-v2.6-9b-awq` | 9,612.6 [9,612.0-9,613.3] | 8,424.6 [8,416.6-8,432.6] | 6,758.3 [6,738.1-6,778.6] | 172.62 [172.51-172.73] | 326.96 [326.93-327.00] | 628.27 [628.18-628.35] | 1,172.99 [1,172.96-1,173.02] |
| `qwen3.8-27b` | 2,700.3 [2,693.4-2,707.1] | 2,407.7 [2,402.0-2,413.4] | 1,978.8 [1,978.7-1,978.9] | 48.88 [48.88-48.89] | 93.90 [93.90-93.91] | 181.88 [181.87-181.89] | 344.97 [344.86-345.09] |
| `qwen3.8-27b-dflash2` | 2,702.5 [2,702.1-2,703.0] | 2,414.6 [2,414.4-2,414.8] | 1,991.6 [1,988.6-1,994.6] | 124.16 [122.44-125.88] | 243.83 [241.10-246.56] | 404.89 [402.96-406.82] | 597.01 [596.79-597.24] |
| `gemma4-26b-a4b-awq` | 7,603.9 [7,601.4-7,606.4] | 4,820.9 [4,819.5-4,822.3] | 2,760.6 [2,759.3-2,761.8] | 169.40 [169.30-169.50] | 320.94 [315.21-326.66] | 589.79 [589.65-589.94] | 1,072.38 [1,072.06-1,072.71] |

Observed 32k/64k/128k prompt counts were respectively 32,780/65,547/131,071
for Qwen3.6, 32,779/65,546/131,070 for MiMo, 32,784/65,556/131,075 for Qwen3.8
(both profiles), and 32,776/65,532/131,055 for Gemma.

Audit cells are median calls/hour followed by `[min-max]`. The 32k and
half-context phases generate 1,024 tokens; deep generates 256.

| Model | Audit 32k 1x | Audit 32k 2x | Audit 32k 4x | Audit 32k 8x | Audit half 1x | Audit deep 1x | Audit deep max |
| -- | --: | --: | --: | --: | --: | --: | --: |
| `qwen3.6-35b-a3b-awq` | 379.64 [379.58-379.71] | 586.44 [584.23-588.64] | 820.55 [818.95-822.14] | 1,001.46 [1,000.17-1,002.76] | 148.35 [148.10-148.59] | 84.17 [84.01-84.33] | 4x: 84.80 [84.62-84.98] |
| `mimo-v2.6-9b-awq` | 357.21 [357.05-357.37] | 504.21 [503.60-504.82] | 641.04 [640.65-641.42] | 736.33 [735.60-737.05] | 128.51 [128.33-128.69] | 76.11 [75.65-76.56] | 4x: 77.20 [77.07-77.34] |
| `qwen3.8-27b` | 103.80 | 147.72 | 188.50 | 218.65 | 38.94 | 23.25 | 2x: 23.49 |
| `qwen3.8-27b-dflash2` | 132.74 | 179.58 | 217.45 | 228.51 | 35.48 | 22.82 | 2x: 22.88 |
| `gemma4-26b-a4b-awq` | 259.69 [259.59-259.79] | 390.23 [389.56-390.91] | 512.35 [511.59-513.11] | 595.22 [594.83-595.60] | 58.53 [58.51-58.55] | 25.65 [25.60-25.69] | 4x: 26.22 [26.22-26.22] |

`qwen3.6-35b-a3b-awq` is the audit workhorse: 1,001.46 cold-32k calls/hour,
148.35 half-context calls/hour, 84.17 deep calls/hour, and eight
simultaneous near-full requests; on 0.30.0 its audit rates reproduce the
0.28.0 row within 1.5% (decode +0.5-2.3%). `mimo-v2.6-9b-awq` (Xiaomi's
cyber and agentic fine-tune of Qwen3.5-9B) is the decode leader at 1,172.99
tok/s but trails qwen3.6 on every audit phase: 736.33 cold-32k at eight
streams (-26%), 128.51 half-context (-13%), 77.20 deep (-9%). Gemma's
1,072.38 decode win likewise does not survive the prompt-heavy phases.

The DFlash 2 profile's gain is depth-dependent: 2.5x decode and +28%
cold-32k calls at one stream, fading to +5% at eight, and a 9% audit_half
loss where the 1,024-token generation over 131k resident KV costs more
speculated than plain. At full audit depth the greedy verdict decode leads
about 1.25x at equal verdict length (the 1.45x first published here divided
verdicts of different lengths), so the deep single-shot penalty measured on
0.28.0 is confined to the mid-depth 1,024-token shape on 0.29.0. Superseded
for serving by AuditBench v2 at the declared sampling, where plain qwen3.8
wins (top of this file).

These rankings describe serving performance only. They do not establish which
model gives better answers.

## Comparability and benchmark method

The A100 canonical v1 rows use AuditBench v1 exactly as defined in the
shared protocol: interleaved samples per its sample rule, common absolute
prompts, relative long-context prompts, fixed outputs, and only stream counts
that fit both admission and the raw KV pool. Compare models within one host.
The common protocol makes workload shapes consistent across hosts, but it does
not erase their different GPU generations, memory systems, or power envelopes.

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
every turn, plain-text findings-ledger verdict at ~165k depth. All
profiles ran at their serving-default cache pins on the finalized
control-free fixture; `qwen3.6-35b-a3b-awq` and `mimo-v2.6-9b-awq` are
measured on vLLM 0.30.0, the qwen3.8 rows on 0.29.0, the rest on 0.27.1
(re-baselined rate-neutral on later pins in the full profile).

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
| `mimo-v2.6-9b-awq` | APC on | yes | 88.5 | 0.900 | 16/16 |
| `qwen3.6-35b-a3b-awq` | APC on | 1/2 | 89.1 | 0.898 | 16/16 |
| `gemma4-26b-a4b-awq` | APC on | yes | 43.8 | 0.906 | 16/16 |
| `qwen3.8-27b-dflash2` | APC on | yes | 23.3 | 0.890 | 16/16 |
| `qwen3.8-27b` | APC on | yes | 21.5 | 0.899 | 16/16 |

Findings:

- `mimo-v2.6-9b-awq` completes both samples with perfect recall at 88.5
  conversations/hour, with its fixed chat template (see its conf).
- qwen3.6 on 0.30.0 completed one of two samples: sample 1 stopped after
  14 of 16 files (15 turns, ~148k final prompt). The compliant sample ran
  at 89.1/h with perfect recall; on 0.27.1 both samples complied at
  85.9/h. The rate is the compliant sample's, not a median.
- qwen3.8 at its align-APC default reaches 21.5 conversations/hour
  (samples 20.2-24.4; 20.2 on 0.28.0 and 21.9 on 0.27.1 sit inside that
  range), roughly 5x the retired cache-off default's 4.1/h (~877 s
  conversations, each re-prefilling ~1.69M tokens) and past its own
  Ollama GGUF artifact on the same host (15.3/h through llama.cpp's
  implicit slot cache). The pin flip came from the align-APC trial in
  the replay section below.
- The DFlash 2 profile lifts the same model to 23.3 conversations/hour
  (+8% over plain, perfect recall on both samples): conversation
  token mass sits mostly at shallow-to-mid depth in short per-turn
  bursts, where speculation pays 1.5-2.4x, while the depth-negative
  zone (see the operating-point section) only touches the verdict
  turn. This is the recommended qwen3.8 audit serving profile; plain
  stays the control and the choice for deep single-shots.
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

### qwen3.8 DFlash 2 replay leg

Same fixture as the plain profile, vLLM 0.29.0 canonical. Replays/hour
rides on mixed verdict lengths (some samples fill the 16,384 cap, others
stop at 1.1-1.2k), so compare the server-side columns.

| Profile | Replays/h | Turn walls | Cached | Verdict decode at ~164k |
| -- | --: | -- | --: | --: |
| plain APC | 25.5 | 13.1 s cold, 4.4 -> 7.6 s | 0.899 | 30.1 tok/s |
| dflash2 | 8.4 | 12.7 s cold, 4.8 -> 8.5 s | 0.890 | 43.6 tok/s |

DFlash 2 holds about 1.25x over plain at full depth and equal verdict
length, greedy (the 1.45x first published here compared verdicts of
different lengths; v2 at sampling reverses it). On 0.28.0 the same legs
measured 30.5 vs ~29.5 tok/s (depth-neutral); the difference is the
0.29.0 core, not the drafter or the fixture.

### The qwen3.6 anchor

| Profile | Cache pin | Replays/h | Turn walls | Cached | Verdict decode |
| -- | -- | --: | -- | --: | -- |
| `qwen3.6-35b-a3b-awq` | APC on | 18.3 | flat 2.3-2.5 s | 0.824 | 16,384 tok @ 98.0 tok/s |

- The qwen3.6 anchor shows what a cache-friendly MoE looks like under
  replay: turns are nearly free and 85% of the 196.7 s wall is the
  forced verdict decode itself (167.0 s).

### vLLM 0.30.0: qwen3.6 and MiMo

Canonical, 2026-09-25, both at their align-APC serving defaults. Every
verdict filled the 16,384-token cap, so these replays/hour compare.

| Profile | Replays/h | Turn walls | Cached | Verdict decode at ~164k |
| -- | --: | -- | --: | --: |
| `mimo-v2.6-9b-awq` | 19.62 [19.58-19.66] | 3.7 s cold, 1.3-2.7 s | 0.899 | 16,384 tok @ 109.1 tok/s |
| `qwen3.6-35b-a3b-awq` | 18.30 [18.28-18.31] | 2.3 s cold, 1.1-2.6 s | 0.824 | 16,384 tok @ 98.2 tok/s |

qwen3.6 reproduces its 0.27.1 anchor (18.3/h, 98.0 tok/s). MiMo's lead is
the single-stream verdict decode, 150 s against 167 s of the ~184-197 s
replay.

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

### vLLM 0.30.0 canonical: qwen3.6 and MiMo

2026-09-25, serving defaults (align APC, seqs 8). Both pools fit all three
candidate stream counts.

`qwen3.6-35b-a3b-awq`, pool 2,798,258 tokens:

| Streams | Batch wall | Replays/h | Scaling | Turn walls first -> final | Verdict decode | Cached |
| --: | --: | --: | --: | -- | --: | --: |
| 1 | 307 s | 11.73 | 1.00 | 9.6 -> 11.3 s | 110.7 tok/s | 0.892 |
| 2 | 384 s | 18.74 | 1.60 | 10.2 -> 15.0 s | 89.0 tok/s | 0.902 |
| 4 | 538 s | 26.78 | 2.28 | 11.2 -> 22.6 s | 63.8 tok/s | 0.912 |

`mimo-v2.6-9b-awq`, pool 2,229,526 tokens:

| Streams | Batch wall | Replays/h | Scaling | Turn walls first -> final | Verdict decode | Cached |
| --: | --: | --: | --: | -- | --: | --: |
| 1 | 237 s | 15.16 | 1.00 | 10.1 -> 13.0 s | 109.1 tok/s | 0.885 |
| 2 | 338 s | 21.29 | 1.40 | 10.9 -> 20.0 s | 79.7 tok/s | 0.894 |
| 4 | 505 s | 28.49 | 1.88 | 12.1 -> 36.9 s | 54.2 tok/s | 0.904 |

- qwen3.6 reproduces its 0.27.1 canonical within 1% at every stream count.
- MiMo's higher replays/hour is less work, not a faster server: most of
  its probe turns end on their own at ~100-400 tokens (sample medians
  152-184), where qwen3.6 fills every 1,024-token turn, and one of its
  twelve 4-stream verdicts stopped at 435 tokens where qwen3.6 fills every
  16,384. Under contention qwen3.6 decodes the ~164k-deep verdict faster
  (63.8 vs 54.2 tok/s at four streams).

### Serving point: eight agents

Exploratory replay-concurrent sweeps on vLLM 0.30.0, 2026-09-25, two
samples each, find the multi-agent operating point above the canonical 4.
qwen3.6 ran on a trial copy of the scripts with admission raised to 16
(pool 2,677,980); MiMo on this tree's committed profile (8970ccc, seqs 8).

| Agents | qwen3.6 replays/h | qwen3.6 final turn | MiMo replays/h | MiMo final turn |
| --: | --: | --: | --: | --: |
| 1 | 11.71 | 11.3 s | 15.32 | 13.1 s |
| 4 | 26.72 | 22.7 s | 27.93 | 32.3 s |
| 8 | 33.88 | 38.2 s | 33.24 | 65.0 s |
| 12 | 33.02 | 59.2 s | -- | -- |

- Eight concurrent agents is the A100 serving point for both: +27% (qwen3.6)
  and +19% (MiMo) over four, and the launcher's 80 GB profile already
  admits eight sequences. MiMo's pool fits twelve such agents.
- Twelve buys nothing for qwen3.6, partly because vLLM captures CUDA graphs
  only at batch sizes 1, 2, 4, 8, 16 and up: 12 runs at the cost of 16. An
  INT4 MiMo sibling (letechlead W4A16, same trial) showed the same padding
  at 6 and 10 agents, both below its 8-agent rate, with no preemption. Pick
  agent counts on those sizes.
- MiMo's rates carry the short-turn caveat above (one of its sixteen
  8-agent verdicts also stopped early, at 337 tokens); its per-agent
  verdict decode at eight agents is 32.8 tok/s.

## Retired A100 harness notes

The measurements below predate AuditBench v1. They remain only as historical
architecture and failure evidence; none of their rates feed the canonical
tables above or the cross-runtime overview.

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
| `gemma4-26b-a4b-awq` | 249,684 | 164.1 s | 326.1 s | 1,531 tok/s |

Qwen3.6 is the clear full-context throughput leader. At approximately 250k it
is 3.4x Gemma's aggregate rate.

Two concurrent requests took 1.00-1.01x as long as running them sequentially
for both models. Neither queued and neither was preempted; both shared an
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
| `qwen3.8-27b` | 2.86x |
| `gemma4-26b-a4b-awq` | 7.15x |
| `qwen3.6-35b-a3b-awq` | 10.48x |

That is not a misconfiguration. vLLM admits only sequences for which it can
allocate blocks.

The worst case measured was Qwen3-Coder (since dropped) with four concurrent
249,787-token requests against a 513,408-token pool: the scheduler ran two,
queued the rest with zero preemptions, and tail latency rose from 323 to
659 seconds without thrashing.

KV cost explains why full-context concurrency is free here: Qwen3.6's hybrid
cache costs 20 KiB per token, and two ~250k sequences ran at 1.00x
sequential.

Short-prompt prefill does not extrapolate. Qwen3.6 falls from 12,355 tok/s at
about 66k to 5,137 at 250k; Gemma falls from 5,067 to 1,522. Attention cost
grows with sequence length, preserving the ranking but widening the gap from
2.4x to 3.4x.

The practical full-context conclusions are:

- `qwen3.6-35b-a3b-awq` has served two concurrent requests at about 250k and
  has memory for roughly ten configured contexts.
- `qwen3.8-27b` has measured cache capacity for two 256k requests, but that
  exact concurrent full-context load has not been timed.

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
