# vLLM-Metal benchmark results

Measured baselines for the script-managed vLLM-Metal server on Apple
Silicon. The cross-runtime summary is [../README.md](../README.md). The
qwen3.6, qwen3.8 and nemotron profiles left this runtime on 2026-10-12
(Splash serves both Qwen models on the M5 and passes the gate, Ollama MLX
serves nemotron faster); their records are in this file at commit
`a7e8f3f`. `ornith1.5-35b-a3b-4bit` left on 2026-11-16 (Splash serves
Ornith 1.5 35B at 30.72 sessions/h against its 9.15), and so did
`gemma4-31b-4bit` (1.89 sessions/h; Gemma 4 stays on the M5 as Ollama's
interactive 26B-A4B MLX profile) and `mimo-v2.6-9b-4bit` (fails Capability
Check v2); their records are in this file at commit `3daa808`.

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
| vLLM-Metal `granite4.2-30b-4bit` | 131,072 | 5 | 331,584 | 1x 2.14 / 2x 3.18 | 17,456 | 330.0 | 10.5 | 9/9 | 759 / 30.9 | pass | yes | `20261016T205227.908811+0000_vllm-metal_granite4-2-30b-4bit_session.json` |

- `granite4.2-30b-4bit` passes Capability Check v2 and is publishable but
  slow: 2.14 sessions/h (3.18 at two streams) with 17,456 output tokens per
  session at 131k. It stays on this runtime as the proof that the plugin
  path works: on Ollama 0.40.16 it passes Capability Check v2 12 of 12, but
  its session fails on an intermittent stream that ends without a usage
  chunk or `[DONE]` (2026-11-15/16). Retest on the next Ollama release.
- The `ornith1.5-122b-a10b-4bit` profile (2.31 / 2.77 @4x sessions/h, 12
  of 12 fitness, an interactive profile) was dropped: Splash serves Ornith
  1.5 122B at 11.87 sessions/h. Its row is in git history.

## Audit conversation profile

The conversation profile (AuditBench protocol) is the production-shaped
workload: 32k evidence, a sequential 16-file tool chain resent in full
every turn, findings-ledger verdict at ~164k depth. All rows run at
their serving-default cache pins on the finalized control-free
fixture at plugin 0.29.0 (repo commit `705c493`). Medians over
compliant samples; cached fraction from the engine's own counters.

| Profile | Cache pin | Compliant | Conversations/hour | Cached | Recall |
| -- | -- | -- | --: | --: | -- |
| `granite4.2-30b-4bit` (131k fixture) | APC on | no | -- | 0.525 | 2/9 files |

Findings:

- granite stopped after one or two of its 131k fixture's nine files in
  both samples: not a conversation server on this host.

## Audit replay profile: M5 Max

Canonical replay runs (AuditBench protocol) at the
serving-default cache pins (align APC on the hybrids), repo commit
`705c493`, plugin 0.29.0, Dell brick at the 140 W contract,
dedicated server lifecycle per model. Replays/hour is never comparable
to conversations/hour: granite filled the forced 16,384-token verdict
(`finish_reason: length`). The server-comparable columns are the turn
walls and the verdict decode rate.

| Profile | Replays/h | Turn walls (16 turns) | Cached | Verdict decode at ~164k depth |
| -- | --: | -- | --: | -- |
| `granite4.2-30b-4bit` (131k fixture, 9 turns) | 0.95 | 58.8 s cold, 22.3 -> 38.9 s | 0.848 | 16,384 tok @ 4.7 tok/s (107k depth) |

- granite: 0.95 replays/h on the 9-turn 131k fixture; 92% of the
  3,783 s wall is the forced verdict at 4.7 tok/s.

## Apple M5 Max operating points

Host: MacBook Pro `Mac17,6`, Apple M5 Max, 40 GPU cores, 128 GB unified
memory, macOS 26.6.2 (25G83), on external power. Each table names its
plugin pin.

### granite -- AuditBench v1 canonical

Plugin 0.29.0, repo commit `705c493`, serving-default cache pins,
`max-num-seqs` 5, Dell brick at the 140 W contract, dedicated server
lifecycle per model (2026-09-21/22). Medians; the audit columns name
the best stream count.

| Profile | Cache pin | Context | KV pool | Prefill 32k/64k/128k tok/s | Decode 1/2/4 tok/s | audit_32k /h | audit_half /h | audit_deep /h | Near-context proof |
| -- | -- | --: | --: | --: | --: | --: | --: | --: | -- |
| `granite4.2-30b-4bit` | APC, util 0.91 | 131,072 | 331,584 | 558 / 446 / - | 30.8 / 55.6 / 88.6 | 31.0 @2x | 13.8 (65k) | 9.3 @1x (114.7k) | 2 x 122,876 in 753.08s |

- granite is decode bound: 31 audit_32k calls/h and single-digit deep
  calls/h.

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
  budget, `gemma4` parsers produced a structured call, teardown clean. Its
  profile served until 2026-11-16.
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
