# llm-local-servers

Measured, Makefile-driven local LLM serving. Three managed runtimes --
vLLM (CUDA), Ollama, and vLLM-Metal (Apple Silicon) -- with one portable
config per model, host-adaptive launchers, isolated remote-host
operation, and the retained benchmark and capability results for every
host in the fleet. The workload everything is tuned for is deep-context
security-audit calls; [AGENTS.md](AGENTS.md) states the mission and the
invariants.

Serving performance is measured with AuditBench v1 and API compatibility
is gated with Capability Check v1. Both live in the sibling
[llm-audit-bench](https://github.com/tuminoid/llm-audit-bench)
repository (`docs/PROTOCOL.md` and `docs/CAPABILITY.md` are the
canonical protocol documents); this repository holds the runtime
adapters, model configs, and results.

## Setup

1. Clone [llm-audit-bench](https://github.com/tuminoid/llm-audit-bench)
   beside this repository, or point `AUDIT_BENCH_DIR` at an existing
   checkout. The harness is standard-library Python; there is nothing to
   install.
2. Copy `.envrc.example` to `.envrc`, fill in the personal values (the
   remote GPU host alias), and `direnv allow` -- or export the same
   variables from your shell. Committed files carry no personal values.
3. Install the runtime you intend to serve with; prerequisites and
   host-tuning rationale are per runtime in
   [vllm/README.md](vllm/README.md),
   [ollama/README.md](ollama/README.md), and
   [vllm-metal/README.md](vllm-metal/README.md).

Development needs `shellcheck`, `markdownlint-cli2`, and Python 3.10 or
newer for `make lint` and `make test`.

## Running

Everything runs from the repository root through make; `make help`
prints the full list. The lifecycle verbs are uniform across runtimes:

| Verb | Does |
| -- | -- |
| `make <runtime>-start MODEL=<name>` | Start detached, wait until serving |
| `make <runtime>-stop` | Stop by pidfile, verify the GPU or process group was released |
| `make <runtime>-status` | Process, memory split, context allocation, KV sizing |
| `make <runtime>-logs` | Follow the server log |
| `make <runtime>-bench MODEL=<name>` | Run AuditBench v1 |
| `make <runtime>-capability MODEL=<name>` | Run Capability Check v1 |

where `<runtime>` is `vllm`, `ollama`, or `vllm-metal` (plus
`ollama-install`, `vllm-metal-install`, and `vllm-metal-pull` for
runtime and model installation). `MODEL` names a config file in that
runtime's `models/` directory, never a served model ID or registry tag;
there is deliberately no default model.

The vLLM and Ollama runtimes also run on a remote GPU host over ssh:
`make vllm-remote-{bootstrap,start,stop,status,logs,bench,capability}`
and the matching `ollama-remote-*` set, with `HOST=<ssh-host>` supplied
by `.envrc` or the command line. Remote Ollama is fully isolated from
the host's own Ollama (own binary, model cache, state, and port), and
the guards are causal: a target refuses when the live server state
contradicts it, from start on a busy GPU or claimed port to bootstrap
under a running server. Servers bind loopback only; reach a remote one
through `make vllm-remote-tunnel` (localhost:8001) or
`make ollama-remote-tunnel` (localhost:11436).

## Measured overview

Decision-oriented summary of the measured vLLM, Ollama, and vLLM-Metal
operating points -- a compact projection of
[vllm/BENCHMARKS.md](vllm/BENCHMARKS.md),
[ollama/BENCHMARKS.md](ollama/BENCHMARKS.md), and
[vllm-metal/BENCHMARKS.md](vllm-metal/BENCHMARKS.md), which hold the
detailed evidence, memory analysis, ranges, and caveats per runtime and
host. Capability campaign records and the retained pass/fail matrix are
in [CAPABILITIES.md](CAPABILITIES.md); those results are not throughput
metrics. Raw benchmark and capability JSON stays outside the repository
under `${XDG_STATE_HOME:-~/.local/state}/`.

Canonical tables copy medians from the benchmark documents; ranges and
raw samples stay in the source, legacy rows use the upper endpoint of a
measured range, and missing values are never derived. The RTX and A100
tables and the Apple AuditBench table are canonical AuditBench v1; the
Apple operating-point rows above its AuditBench table remain historical
bring-up measurements until rerun, and legacy and canonical rates must
not be mixed. Prefill and decode are aggregate tok/s; audit columns are
calls/hour. A stream suffix names the measured concurrency.
`GPU KV / allocation` is the raw vLLM pool or Ollama's measured CPU/GPU
model allocation; Ollama exposes no fungible pool.

### Audit conversations per hour, fleet-wide

The conversation profile is the mission workload: a growing tool-loop
conversation resent every turn, findings verdict at depth (see the
AuditBench protocol). Serving-default cache modes; only compliant
profiles ranked. Contexts differ per operating point (the qwen3.6 NVFP4
rows run a shallower 131k shape), so compare within a tier. These are
interactive-profile numbers, so each row also certifies the model held
the tool-loop protocol end to end; a "non-compliant" entry below means
the model deviated from the fixture, not that the server is slow -- the
scripted replay profile measures server performance for those models
too.

| Rank | Host / runtime / profile | Cache | Conv/hour |
| --: | -- | -- | --: |
| 1 | A100 vLLM `qwen3.6-35b-a3b-awq` | align APC | 85.9 |
| 2 | M5 Ollama `qwen3.6 coding NVFP4` (131k shape) | MLX trie | 50.9 |
| 3 | M5 Ollama `qwen3.6 base NVFP4` (131k shape) | MLX trie | 48.1 |
| 4 | A100 vLLM `qwen3-coder-30b` | APC | 45.2 |
| 5 | A100 vLLM `gemma4-26b-a4b-awq` | APC | 43.8 |
| 6 | M5 Ollama `nemotron-3.5-lightning` | MLX trie | 34.4 |
| 7 | A100 Ollama `qwen3.6-35b-a3b` GGUF | slot cache | 32.0 |
| 8 | A100 Ollama `qwen3-coder-30b` | slot cache | 26.0 |
| 9 | RTX Ollama `qwen3.5:4b` (131k shape, 1-of-2) | slot cache | 22.6 |
| 10 | A100 Ollama `qwen3.8-27b-native` | slot cache | 14.5 |
| 11 | RTX vLLM `qwen3.5-4b-awq` (131k shape) | off | 12.9 |
| 12 | M5 vLLM-Metal `qwen3.6-35b-a3b-4bit` | align APC | 12.5 |
| 13 | RTX Ollama `qwen3.5:9b` | slot cache | 9.8 |
| 14 | RTX Ollama `qwen3.6-35b-a3b` GGUF (1-of-2, CPU-assisted) | slot cache | 4.4 |
| 15 | A100 vLLM `qwen3.8-27b` | off | 4.1 |
| 16 | M5 vLLM-Metal `gemma4-31b-4bit` | APC | 2.4 |
| 17 | M5 vLLM-Metal `qwen3.8-27b-4bit` | off | 0.70 |

The RTX rows are clean-fixture reruns; the pre-finalization RTX numbers
(29.5/14.6) are retired with the poisoned corpus, whose planted
decode-control has since been fixed in the harness. Non-compliant at
this fixture: GLM 4.7 Flash
on both A100 runtimes (think-runaway or ledger paraphrase), A100 Ollama
gemma4-26b (mixed), M5 Ollama qwen3.8 NVFP4 (first conversation clean
at ~7.7/h, second on the same process reproducibly 500s -- the
trie-retention limit), RTX vLLM `qwen3.5-4b-awq` under align APC (its
compliant row above is cache-off; align numerics reliably tip it into a
16k runaway, which set that conf's pin back to 0), RTX gemma E2B on
both stacks (reads evidence-embedded filenames), and RTX Ollama gemma
12B (premature completion). Cache policy, not model speed, dominates:
the same qwen3.8 weights span 4.1 to 14.5 conv/hour on one host purely
by cache mode.

### Audit replay: server performance without model cooperation

First replay-profile results on the A100 (details in each runtime's
BENCHMARKS.md): the qwen3.8 align-APC trial measured 6.1x end to end on
matched verdicts (137.6 s vs 845.0 s, final-turn prefill 11.5x cheaper,
0.899 cached) -- the correctness gate passed the same day (semantic
needles 8/8, divergence reproduced cache-off, pool cost -0.88%) and the
qwen3.8 conf now pins align APC on. GLM 4.7 Flash, unmeasurable by the
conversation profile everywhere, turns out to serve the shape well on
vLLM (0.902 cached, clean 16k verdict decode); on Ollama it exposes a
reproducible /v1 hard failure at exactly 128Ki prompt tokens. Ollama
gemma4-26b's flat turn walls prove the slot cache engages despite the
API reporting no cached-token counters.

The RTX GPU-resident set ran both profiles (details in each runtime's
BENCHMARKS.md): replay prices APC at 1.32x (qwen3.5-4b) and 1.73x
(gemma4-e2b) end to end with cache-neutral verdict decode, but align
APC also reliably tips qwen3.5-4b's own tool loop into a 16k runaway
that cache-off never shows, so that conf pins APC 0 and gemma keeps
APC 1. Verdict decode at depth is the RTX replay ceiling: 37 tok/s
(vLLM 4B) down to 11.7 tok/s (Ollama 9B at 165k). The CPU-offloaded
profiles (qwen3.6 GGUF replay, qwen3.8) remain unrun pending a
separately approved batch.

The M5 Max vLLM-Metal set ran canonically (details in
vllm-metal/BENCHMARKS.md): qwen3.6 anchors at 2.13 replays/h with 88%
of the wall in the forced 16k verdict at 11.0 tok/s -- against the
A100's 18.3 replays/h at 98 tok/s on the same fixture, the M5 audit gap
is single-stream decode bandwidth at depth, not caching (cached
fraction identical, 0.824). qwen3.8 confirms its quality-reserve role
(verdict decode 5.5 tok/s at 164k even with 0.899 cached, turn walls
growing despite the cache), and gemma4-31b cannot finish a replay
inside the 7,200 s request timeout at all: its 2.1 tok/s depth decode
puts the verdict alone at ~2.1 h. Server-side health was clean on all
three; the ceilings are model decode physics.

### Concurrent audit replay: multi-agent contention

The M5 Max vLLM-Metal set ran the replay-concurrent profile
canonically (details in vllm-metal/BENCHMARKS.md): N agents share the
32k evidence prefix and every turn decodes a full 1,024-token agent
turn. Two concurrent agents are the knee on both hybrids -- qwen3.6
goes 1.56 -> 1.98 replays/h at 2x while 4x adds nothing (1.95) at
quadruple per-agent latency, and qwen3.8 (pool-limited to 2x) goes
1.83 -> 2.19. Shared-prefix caching is real but minor at audit depth
(cached fraction 0.897 -> 0.916 with stream count); the binding
constraint is aggregate decode bandwidth at depth.

### RTX PRO 3000 Blackwell laptop GPU

Local host: sm_120, 12,227 MiB VRAM, 62 GiB RAM.

| Runtime and profile | Context | Slots | GPU KV / allocation | 32k prefill | Peak decode | Audit 32k | Audit half | Audit deep | Near-context proof |
| -- | --: | --: | -- | --: | --: | --: | --: | --: | -- |
| vLLM `qwen3.5-4b-awq` | 131,072 | 2 | 274,432 KV | 4,686.9 | 176.12 @2x | 250.94 @2x | 113.76 | 85.82 @2x | 2 x 122,861 in 87.77s |
| vLLM `gemma4-e2b-awq` | 131,072 | 2 | 450,444 KV | 4,835.1 | 303.54 @2x | 289.55 @2x | 113.31 | 56.89 @2x | 2 x 122,896 in 124.89s |
| Ollama `qwen3.5:4b` | 131,072 | 1 | 0.00 / 6.04 GiB | 2,057.6 | 67.43 | 100.55 | 59.19 | 41.92 | 122,861 in 84.87s |
| Ollama `gemma4:e2b` | 131,072 | 4 | 0.00 / 2.66 GiB | 3,582.5 | 247.40 @4x | 184.88 @4x | 99.42 | 67.33 @1x | 4 x 122,903 in 217.03s |
| Ollama `qwen3.5:9b` | 262,144 | 1 | 0.00 / 10.21 GiB | 1,654.8 | 37.83 | 70.34 | 22.10 | 12.26 | 245,752 in 311.57s |
| Ollama `gemma4:12b` | 262,144 | 1 | 0.00 / 7.96 GiB | 1,242.8 | 32.36 | 59.82 | 16.67 | 8.31 | 245,777 in 462.12s |
| Ollama `qwen3.6:35b-a3b` | 262,144 | 1 | 14.53 / 10.21 GiB | 303.4 | 30.99 | 25.09 | 7.00 | 4.00 | 245,752 in 927.94s |
| Ollama `qwen3.8:27b` | 131,072 | 1 | 12.49 / 7.64 GiB | 188.3 | 2.93 | 2.70 | 1.83 | 2.15 | 122,861 in 745.62s |

The practical RTX choices are vLLM Gemma for peak decode and cold-32k audit
throughput, vLLM Qwen for stronger late-audit throughput, Ollama Gemma E2B for
four-slot capacity, and Ollama Qwen3.5 9B for a fully resident 262k model.
Qwen3.6 and Qwen3.8 are CPU-assisted capability profiles rather than
throughput choices.

### A100-SXM4-80GB

Remote host: sm_80, 81,920 MiB VRAM. Comparable Ollama profiles were measured
with isolated Ollama 0.32.14, Flash Attention, and q8 KV. Canonical AuditBench
v1 rows use three measured samples.

| Runtime and profile | Context | Slots | GPU KV / allocation | 32k prefill | Peak decode | Audit 32k | Audit half | Audit deep | Near-context proof |
| -- | --: | --: | -- | --: | --: | --: | --: | --: | -- |
| vLLM `qwen3.6-35b-a3b-awq` | 262,144 | 8 | 2,747,310 KV | 16,103.9 | 880.31 @8x | 1,003.11 @8x | 150.95 | 86.33 @1x | 8 x 245,752 in 350.22s |
| Ollama `qwen3.6:35b-a3b` | 262,144 | 1 | 0.00 / 25.34 GiB | 4,165.7 | 84.58 | 176.52 | 64.82 | 42.81 | 245,752 in 85.26s |
| vLLM `gemma4-26b-a4b-awq` | 262,144 | 8 | 1,868,129 KV | 7,616.4 | 1,066.07 @8x | 594.09 @8x | 58.59 | 26.32 @4x | 4 x 245,774 in 624.84s |
| Ollama `gemma4:26b` | 262,144 | 8 | 0.00 / 25.32 GiB | 3,246.7 | 231.48 @8x | 222.32 @8x | 53.51 | 27.68 @4x | 8 x 245,777 in 1,030.85s |
| vLLM `qwen3-coder-30b` | 262,144 | 8 | 512,864 KV | 8,461.3 | 1,020.30 @8x | 514.55 @8x | 61.66 | 27.07 @1x | 2 x 245,762 in 290.58s |
| Ollama `qwen3-coder:30b` | 262,144 | 4 | 0.00 / 70.39 GiB | 2,729.4 | 186.96 @4x | 132.09 @4x | 26.45 | 14.82 @1x | 4 x 245,762 in 1,016.28s |
| vLLM `glm4.7-flash-awq` | 202,752 | 8 | 1,050,624 KV | 7,239.0 | 363.08 @8x | 367.03 @8x | 66.20 | 37.29 @4x | 4 x 190,092 in 421.70s |
| Ollama `glm-4.7-flash` | 202,752 | 8 | 0.00 / 63.01 GiB | 1,457.8 | 268.75 @8x | 112.63 @8x | 21.23 | 8.39 @1x | 8 x 190,092 in 3,703.26s |
| vLLM `qwen3.8-27b` | 262,144 | 8 | 749,204 KV | 2,697.5 | 347.50 @8x | 220.37 @8x | 38.90 | 23.61 @2x | 2 x 245,748 in 324.99s |
| Ollama `qwen3.8:27b` | 262,144 | 1 | 0.00 / 17.27 GiB | 1,081.5 | 57.80 | 74.48 | 21.62 | 11.28 | 245,752 in 340.97s |

The A100 audit workhorse is vLLM Qwen3.6: it leads every prompt-heavy phase,
reaches 1,003.11 cold-32k calls/hour, and proves eight simultaneous near-full
contexts. vLLM Gemma and Qwen Coder lead pure aggregate decode, but their
32k audit rates are only 59% and 51% of Qwen3.6. Gemma is the best Ollama
audit profile; GLM's higher Ollama decode rate does not survive long prompts.

### Apple M5 Max (128 GB unified memory)

Local host: MacBook Pro `Mac17,6`, 40 GPU cores, macOS 26.6.2. Ollama rows:
managed official Ollama 0.32.14 with the MLX runner on the `mlx_metal_v4`
backend, safetensors NVFP4 artifacts; the runner serializes requests to
one slot, so 2x and 4x are unsupported, not unmeasured. vLLM-Metal rows:
measured at plugin 0.3.0.dev20260819180958 on vLLM 0.27.1, paged KV, NAX
prefill active, utilization as noted per row; the pin has since moved to
0.3.0.dev20260826100011 (APC decay fix), and these cache-off rates
remain authoritative for cache-off serving until rerun.
`1x CPU / GPU` is Ollama's `/api/ps` allocation on unified memory; the
vLLM-Metal pool is the planned paged-KV size.

| Runtime | Model or profile | Context/request | GPU KV pool | 1x CPU / GPU | Prefill prompt | Prefill | Decode 1x | Decode 2x | Decode 4x |
| -- | -- | --: | --: | -- | --: | --: | --: | --: | --: |
| Ollama | `qwen3.6:35b-a3b-coding-nvfp4` (historical MLX manifest) | 262,144 | - | 0.00 / 20.51 GiB | 130,920 | 1,384.7 | 122.58 | - | - |
| Ollama | `qwen3.8:27b-nvfp4` (MLX) | 184,320 | - | 0.00 / 17.22 GiB | 92,058 | 496.0 | 72.26 | - | - |
| vLLM-Metal | `qwen3.8-27b-8bit` | 262,144 | 521,185 | GPU only | 66,173 | 414 | 18.1 | 35.4 (1.96x) | 65.7 (3.64x) |
| vLLM-Metal | `qwen3.8-27b-8bit` util 0.80, seqs 8 | 262,144 | 870,193 | GPU only | 66,173 | 424 | 18.1 | 35.5 (1.96x) | 65.9 (3.65x) |
| vLLM-Metal | `qwen3.8-27b-4bit` util 0.91, seqs 8 | 262,144 | 1,264,961 | GPU only | 66,173 | 433 | 32.5 | 59.1 (1.87x) | 93.6 (2.96x) |
| vLLM-Metal | `qwen3.6-35b-a3b-4bit` util 0.91, seqs 5 | 262,144 | 3,908,234 | GPU only | 66,131 | 1,842 | 118.2 | 197.2 (1.67x) | 314.5 (2.66x) |

The Ollama contexts are measured per-model maxima from supervised watchdog
runs: Qwen3.6 completed its native ceiling (246,096-token proof), while
Qwen3.8 at native 262,144 exhausted unified memory during a 246k prefill
and hard-reset the host; its 184,320 maximum peaked at 92.78 GiB MLX
memory with no headroom above. vLLM-Metal serves the same checkpoint
family at the full native 262,144 inside a bounded footprint (66 GB at
util 0.60, 89 GB at 0.80), including completed 245,478-token prefills at
both budgets. Its 4-bit checkpoint decodes 32.5 tok/s single-stream and
passes the Ollama runner's single-stream ceiling from three concurrent
streams up (100-104 aggregate at 5 streams, 105.7 at 8); the 8-bit
trails it at any measured concurrency. The Qwen3.6 MoE 4-bit profile
saturates at four streams (~315 tok/s aggregate ceiling; 8 and 16
admitted streams add nothing) with a 3,908,234-token pool from its
20 KiB/token hybrid KV as measured at util 0.91, and completed a
246,143-token prefill at
631 tok/s bounded. Its serving default is now computed from that KV cost
(util 0.46, 1,410,584-token pool, five full native contexts outright);
the budget buys KV capacity only, so the rates carry over. NVFP4
safetensors do not load
under mlx-lm at this pin, so the Ollama registry remains the only NVFP4
path. See
[ollama/BENCHMARKS.md](ollama/BENCHMARKS.md) and
[vllm-metal/BENCHMARKS.md](vllm-metal/BENCHMARKS.md).

The Qwen3.6 Ollama registry tag has moved since the row above was
measured. It remains the historical performance baseline for the
earlier manifest; the replacement digest passed capability checks, and
its canonical attempt at the old 262,144 operating point hard-reset the
host during a 131k prefill (watchdog panic, unified memory exhausted).
Both qwen3.6 NVFP4 profiles now launch at 131,072, and the current
canonicals below depth-prove that point on both digests (122,861-token
capacity passes); see [ollama/BENCHMARKS.md](ollama/BENCHMARKS.md).

#### AuditBench v1 canonical

Measured with the finalized output-control prompt, comparable with the
RTX and A100 canonical tables. Calls/hour includes prefill; admission
at five slots omitted the 8x points. Peak-stream medians; each profile
passed its near-context proof at 1x and its maximum fitting concurrency
(qwen3.6: 245,752 x4 in 1,499 s; qwen3.8: 245,748 x4 in 4,707.3 s,
APC x2 in 2,353 s;
gemma4: 245,774 x2 in 5,528.4 s -- its pool holds 2.35 near-full
contexts; lightning: 245,773 x1 in 127.4 s on the one-slot MLX runner).

| Runtime | Model or profile | Context | KV pool | Prefill 32k/64k/128k tok/s | Decode 1/2/4 tok/s | audit_32k /h | audit_half /h | audit_deep /h |
| -- | -- | --: | --: | --: | --: | --: | --: | --: |
| vLLM-Metal | `qwen3.6-35b-a3b-4bit` cache-off, util 0.46, seqs 5 | 262,144 | 1,407,463 | 2,943 / 1,686 / 1,084 | 121.1 / 205.3 / 320.0 | 124.2 @1x | 19.6 | 10.1 @1x |
| vLLM-Metal | `qwen3.6-35b-a3b-4bit` APC (serving), util 0.71, seqs 5 | 262,144 | 1,324,084 | 2,824 / 1,574 / 1,063 | 98.4 / 168.6 / 258.1 | 112.6 @4x | 18.8 | 9.9 @1x |
| vLLM-Metal | `qwen3.8-27b-4bit` cache-off, util 0.91, seqs 5 | 262,144 | 1,264,961 | 496 / 429 / 304 | 33.1 / 59.3 / 92.3 | 40.1 @4x | 6.7 | 3.3 @1x |
| vLLM-Metal | `qwen3.8-27b-4bit` APC (serving), util 0.91, seqs 5 | 262,144 | 611,156 | 570 / 458 / 318 | 28.6 / 53.4 / 83.3 | 39.4 @4x | 6.7 | 3.3 @1x |
| vLLM-Metal | `gemma4-31b-4bit` util 0.91, seqs 5 | 262,144 | 617,308 | 364 / 247 / 150 | 26.5 / 47.8 / 71.8 | 14.3 @1x | 2.4 | 1.3 @2x |
| Ollama | `nemotron-3.5-lightning:30b-a3b-mlx` | 262,144 | one slot | 4,040 / 3,072 / 2,628 | 141.7 / - / - | 212.8 @1x | 58.3 | 31.1 @1x |
| Ollama | `qwen3.6:35b-a3b-nvfp4` (base MLX) | 131,072 | one slot | 3,190 / 2,224 / - | 140.8 / - / - | 188.7 @1x | 91.2 (65k) | 47.7 (114.7k) |
| Ollama | `qwen3.6:35b-a3b-coding-nvfp4` (MLX) | 131,072 | one slot | 3,242 / 2,305 / - | 126.7 / - / - | 180.4 @1x | 88.5 (65k) | 48.7 (114.7k) |

The MoE holds a ~3x calls/hour advantage over qwen3.8 at every audit depth;
the dense qwen3.8 batches better (audit_32k +10% at 4x, decode still scaling
at 4 streams) and is the quality profile, not the throughput profile.
Gemma 4 31B trails both on every measured axis -- 7.4x fewer cold-32k
calls/hour than the MoE at 2.5x qwen3.8's KV rent -- and stays a measured
capability point rather than a serving choice.

Nemotron 3.5 Lightning rewrites the audit-cadence column: a single stream
on the one-slot Ollama MLX runner delivers 1.9-3.2x the calls/hour of
qwen3.6's best concurrency at every depth, because its Mamba/attention
hybrid (6 of 52 layers attend) holds prefill nearly flat with depth. Its
throughput ceiling is that one slot -- the vLLM-Metal path that would give
it concurrent streams loads but is blocked on a plugin mask bug (see the
model conf). Serving-quality caveat: these are protocol rates; the model
has no secaudit quality record yet.

The two qwen3.6 NVFP4 rows run the 131,072 operating point, so their
half and deep targets are 65k and 114.7k -- shallower than the 262,144
profiles' 131k and 229k; the parenthesized depths keep the columns
honest. Both digests are rate-identical within a few percent. At the
shared 32k depth one NVFP4 MLX stream (188.7/h) beats the vLLM-Metal
4-bit profile's best rate (124.2/h) by 1.5x; at matched ~115-131k
depth Lightning stays the host's depth leader (58.3 at 131k vs 47.7 at
114.7k).
