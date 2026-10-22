# vLLM-Metal benchmark results

Measured baselines for the script-managed vLLM-Metal server on Apple
Silicon. The cross-runtime summary is [../README.md](../README.md). The
qwen3.6, qwen3.8 and nemotron profiles left this runtime on 2026-10-12
(Splash serves both Qwen models on the M5 and passes the gate, Ollama MLX
serves nemotron faster); their records are in this file at commit
`a7e8f3f`.

The AuditBench v1 sections below (operating-point, conversation and
replay profiles) are
canonical under the finalized output-control prompt; each states its
plugin pin and cache condition. The other sections use the retired
vLLM-Metal bring-up harness or the earlier prompt. Do not combine those
legacy rates with canonical results.

## AuditBench v2: Apple M5 Max

Plugin 0.31.0 with core vLLM 0.31.0, serving-default cache pins (align APC
on the hybrids). Canonical AuditBench v2 `session`
profile (llm-audit-bench v2.1.0 plus the triage amendment `c0dc34a`; each
JSON records its harness hash), run 2026-10-16 to 2026-10-17 on the M5 Max
(128 GB, macOS 27.0) from fleet commit `2e990d6` at each conf's declared
sampling. The harness measured 1 stream and the largest of 2/4/8 that fits
admission and the KV pool: tool steps from 32k evidence, 16 at 262,144
configured context and 9 at 131,072, report at depth. Sessions/h is the
median over 2-3 samples; complete counts sessions whose report ended on its
own and named at least 7/8 of its findings. pp512/tg128 is the
llama-bench-method reference (one stream, greedy, depth ~0), not a serving
result. JSON files are retained under
`~/.local/state/auditbench/trials/2026-10-16-m5-canonical/results/`; the
plugin 0.30.0 rows they replace are in git history. Every later
section of this file is AuditBench v1 or older, never comparable with v2.
Their top-level retained JSON on the M5 and A100 was removed on 2026-09-30;
trial-directory copies remain, and the figures stay here and in git history.

| Runtime and profile | Context | Slots | KV pool | Sessions/h by streams | Out tok/session 1x | Prefill tok/s 1x | Report decode 1x | Complete | pp512 / tg128 | Capability v2 | Publishable | JSON |
| -- | --: | --: | --: | -- | --: | --: | --: | -- | -- | -- | -- | -- |
| vLLM-Metal `ornith1.5-35b-a3b-4bit` | 262,144 | 5 | 1,398,101 | 1x 9.15 / 4x 10.52 | 7,042 | 883.0 | 33.9 | 11/15 | 2,966 / 98.3 | pass | yes, 1x | `20261016T180845.140792+0000_vllm-metal_ornith1-5-35b-a3b-4bit_session.json` |
| vLLM-Metal `ornith1.5-122b-a10b-4bit` | 262,144 | 5 | 1,108,154 | 1x 2.31 / 4x 2.77 | 8,154 | 321.3 | 7.0 | 10/10 | 1,037 / 53.1 | pass | no | `20261020T180509.984422+0000_vllm-metal_ornith1-5-122b-a10b-4bit_session.json` |
| vLLM-Metal `granite4.2-30b-4bit` | 131,072 | 5 | 331,584 | 1x 2.14 / 2x 3.18 | 17,456 | 330.0 | 10.5 | 9/9 | 759 / 30.9 | pass | yes | `20261016T205227.908811+0000_vllm-metal_granite4-2-30b-4bit_session.json` |
| vLLM-Metal `gemma4-31b-4bit` | 262,144 | 5 | 585,801 | 1x 1.80 / 2x 1.89 | 1,557 | 110.3 | 2.8 | 9/9 | 661 / 27.8 | pass | yes | `20261017T004920.426416+0000_vllm-metal_gemma4-31b-4bit_session.json` |
| vLLM-Metal `mimo-v2.6-9b-4bit` | 262,144 | 5 | 1,378,992 | 1x 1.56 / 4x 2.25 | 43,097 | 891.7 | 16.9 | 0/15 | 2,429 / 69.0 | fail | no | `20261017T083034.292323+0000_vllm-metal_mimo-v2-6-9b-4bit_session.json` |

- `granite4.2-30b-4bit` and `gemma4-31b-4bit` pass Capability Check v2
  and are publishable but slow: granite 2.14 sessions/h (3.18 at two
  streams) with 17,456 output tokens per session at 131k, gemma4 1.80
  with 2.8 tok/s report decode at depth.
- `ornith1.5-35b-a3b-4bit` passes Capability Check v2 at this pin (11 of
  12 fitness samples, one selection runaway) and is the fastest profile at
  9.15 sessions/h at one stream, its optimal operating point: 4 of its 12
  four-stream reports hit the output cap or missed findings, so the 10.52
  at four streams is not a serving rate. The JSON records `publishable:
  false` under llm-audit-bench 2.2.0; under the 2.3.0 rule its complete 1x
  leg publishes.
- MiMo fails Capability Check v2 (tool arguments `{}`, 0 of 12 fitness
  samples) and completes no session: its reports run to the output cap.
- `ornith1.5-122b-a10b-4bit` ran 2026-10-20 on llm-audit-bench v2.2.0 from
  an uncommitted conf (`publishable: false`, `repository_dirty`), under
  `~/.local/state/auditbench/trials/2026-10-20-m5-night/ornith/`. It passes
  Capability Check v2 outright, 12 of 12 fitness samples, but is slow at
  depth: report decode 7.0 tok/s at one stream and 2.3 at four, and a
  245,772-token cold prompt prefills at 240 tok/s at one stream and 243 in
  aggregate at four. Every session completed. At about 2.3 sessions/h it
  is an interactive profile, not an audit one.

## Audit conversation profile

The conversation profile (AuditBench protocol) is the production-shaped
workload: 32k evidence, a sequential 16-file tool chain resent in full
every turn, findings-ledger verdict at ~164k depth. All rows run at
their serving-default cache pins on the finalized control-free
fixture at plugin 0.29.0 (repo commit `705c493`). Medians over
compliant samples; cached fraction from the engine's own counters.

| Profile | Cache pin | Compliant | Conversations/hour | Cached | Recall |
| -- | -- | -- | --: | --: | -- |
| `gemma4-31b-4bit` | APC on | yes | 2.4 | 0.902 | 16/16 |
| `ornith1.5-35b-a3b-4bit` | APC on | 1/2 | 7.6 | 0.896 | 16/16 |
| `granite4.2-30b-4bit` (131k fixture) | APC on | no | -- | 0.525 | 2/9 files |
| `mimo-v2.6-9b-4bit` | APC on | yes | 15.7 | 0.900 | 16/16 |

Findings:

- MiMo 9B (repo commit `aa84c5b`) is the fastest compliant conversation
  server among these profiles: 230 s per conversation, 90.0% cached,
  perfect recall on both samples.
- gemma4 completes with perfect recall but at 1,500 s per conversation
  (decode-bound); it stays a capability point, not an audit choice.
- ornith completes a conversation in 471 s with 89.6% cached and
  perfect recall when it completes, but one of two samples stopped at
  15/16 files, so the row stays unranked in the cross-runtime table.
- granite stopped after one or two of its 131k fixture's nine files in
  both samples: not a conversation server on this host.

## Audit replay profile: M5 Max

Canonical replay runs (AuditBench protocol) at the
serving-default cache pins (align APC on the hybrids), repo commit
`705c493`, plugin 0.29.0, Dell brick at the 140 W contract,
dedicated server lifecycle per model. Replays/hour is never comparable
to conversations/hour, and here it is not even comparable across
models: granite, gemma4 and MiMo (two of three samples) filled the
forced 16,384-token verdict (`finish_reason: length`) while ornith
ignored the never-conclude control in both samples and stopped at 0.9k
tokens, so its replays/h ride on about 18x less verdict decode. The
server-comparable columns are the turn walls and the verdict decode rate.

| Profile | Replays/h | Turn walls (16 turns) | Cached | Verdict decode at ~164k depth |
| -- | --: | -- | --: | -- |
| `ornith1.5-35b-a3b-4bit` | 12.6* | 13.2 s cold, 6.1 -> 18.6 s | 0.897 | 0.9k tok @ 10.5 tok/s (stopped early) |
| `granite4.2-30b-4bit` (131k fixture, 9 turns) | 0.95 | 58.8 s cold, 22.3 -> 38.9 s | 0.848 | 16,384 tok @ 4.7 tok/s (107k depth) |
| `gemma4-31b-4bit` | 0.42 | 96.8 s cold, 40.5 -> 121.3 s | 0.902 | 16,384 tok @ 2.3 tok/s |
| `mimo-v2.6-9b-4bit` | 3.28 | 17.5 s cold, 7.0 -> 17.6 s | 0.899 | 16,384 tok @ 18.2 tok/s (2 of 3 samples) |

- MiMo 9B: flat 7-18 s turns at 89.9% cached. The verdict is not
  deterministic across samples at temperature 0: the first sample
  stopped at 951 tokens, the next two filled the 16,384-token budget at
  18.2 tok/s, so the harness extended to three samples and the median
  is the forced-decode case. Every sample was a cache hit on different
  blocks, and align mode resumes from the hit boundary, so greedy
  decoding can flip at 164k depth; ornith's 931 vs 881 tokens is the
  same effect.
- ornith: 12.6 replays/h with turn walls of 6-19 s at 89.7% cached;
  the verdict stopped at 0.9k tokens (never-conclude control ignored)
  decoding at 10.5 tok/s at 165k depth.
- granite: 0.95 replays/h on the 9-turn 131k fixture; 92% of the
  3,783 s wall is the forced verdict at 4.7 tok/s.
- `gemma4-31b-4bit`: 8,497 s per replay, 85% of it the forced
  16,384-token verdict at 2.3 tok/s (7,196 s, four seconds inside the
  7,200 s request timeout). Turn walls grow 40 -> 121 s with depth at
  90.2% cached. This is the dense-31B depth-decode wall, consistent
  with its 1.4 deep audit calls/h; a capability point, not an audit
  server.

## Apple M5 Max operating points

Host: MacBook Pro `Mac17,6`, Apple M5 Max, 40 GPU cores, 128 GB unified
memory, macOS 26.6.2 (25G83), on external power. Each table names its
plugin pin.

### ornith, granite, gemma4 -- AuditBench v1 canonical

Plugin 0.29.0, repo commit `705c493`, serving-default cache pins,
`max-num-seqs` 5, Dell brick at the 140 W contract, dedicated server
lifecycle per model (2026-09-21/22). Medians; the audit columns name
the best stream count.

| Profile | Cache pin | Context | KV pool | Prefill 32k/64k/128k tok/s | Decode 1/2/4 tok/s | audit_32k /h | audit_half /h | audit_deep /h | Near-context proof |
| -- | -- | --: | --: | --: | --: | --: | --: | --: | -- |
| `ornith1.5-35b-a3b-4bit` | align APC, util 0.70 | 262,144 | 1,300,439 | 2,623 / 1,664 / 1,075 | 101.5 / 173.5 / 264.3 | 117.5 @4x | 19.0 | 9.9 @4x | 4 x 245,752 in 1,539.43s |
| `granite4.2-30b-4bit` | APC, util 0.91 | 131,072 | 331,584 | 558 / 446 / - | 30.8 / 55.6 / 88.6 | 31.0 @2x | 13.8 (65k) | 9.3 @1x (114.7k) | 2 x 122,876 in 753.08s |
| `gemma4-31b-4bit` | APC, util 0.91 | 262,144 | 617,308 | 355 / 243 / 148 | 26.6 / 47.9 / 72.0 | 17.3 @4x | 2.6 | 1.4 @2x | 2 x 245,774 in 5,601.60s |

- granite and gemma4 are dense-decode bound: 31 and 17 audit_32k
  calls/h and single-digit deep calls/h.

### mimo-v2.6-9b-4bit APC -- AuditBench v1 canonical

Plugin 0.29.0, repo commit `aa84c5b`, align APC, util 0.90 computed
from the conf, `max-num-seqs` 5, text-only serving, dedicated server
lifecycle (2026-09-22). Medians; the audit columns name the best
stream count.

| Context | KV pool | Prefill 32k/64k/128k tok/s | Decode 1/2/4 tok/s | audit_32k /h | audit_half /h | audit_deep /h | Near-context proof |
| --: | --: | --: | --: | --: | --: | --: | -- |
| 262,144 | 1,323,749 | 1,666 / 1,420 / 989 | 69.6 / 129.8 / 218.0 | 118.0 @4x | 20.1 | 9.9 @1x | 4 x 245,749 in 1,530.12s |

- MiMo decides for itself whether to think: its template acts only on
  `enable_thinking=false`, so short questions get direct answers without
  reasoning.

### NVFP4 checkpoints do not load

`unsloth/Qwen3.8-27B-NVFP4` (revision 7d6f8d4d) failed engine init loudly
with an mlx-lm no newer than plugin 0.28.0's (0.31.3): `ValueError:
Received 937 parameters not in model` -- mlx-lm had no weight mapping for
NVFP4 block-scale safetensors of this architecture. The verdict transfers
to `nvidia/Qwen3.6-35B-A3B-NVFP4` (same quantization format), so no NVFP4
profile exists here and the Ollama registry remains the only NVFP4 path on
this host. Plugin 0.30.0's mlx-lm (`9e6acca`) still cannot load it, by
code reading on 2026-10-12: it maps compressed-tensors
`nvfp4-pack-quantized` checkpoints, but this one declares
`mixed-precision` (FP8 attention, `lm_head` and the last eight layers' MLP;
NVFP4 MLP elsewhere), which falls to the affine path, and its `qwen3_5`
model has no `weight_packed` mapping. Retest when the plugin's mlx-lm pin
maps that format.

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
  boundary. It served from plugin 0.29.0 until the profile was dropped
  on 2026-10-12.
- `gemma-4-12b-coder-fable5-composer2.5-4bit` is an incomplete artifact:
  every mlx-community gemma4-12B conversion (plain and OptiQ) lacks the
  processor files vLLM's gemma4 path requires; the 31B conversion has
  them. Needs a re-uploaded conversion, not a code bump.

Failing configs were removed per the fail-loudly convention; their
weights are no longer kept.

### TurboQuant KV compression (2026-09-04): measured, not adopted

q8_0 keys / q3_0 values (the plugin defaults) on the since-dropped
`qwen3.8-27b-4bit` profile at
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
