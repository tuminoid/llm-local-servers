# Capability Check results

Capability Check is the pass/fail gate for models in the serving inventory.
Its API checks prove the response semantics coding agents need; since v2 its
audit fitness check also proves the model finishes audit-shaped work at its
declared sampling. AuditBench
separately measures serving performance and capacity. The protocol -- fixed
checks, model expectations, and the mapping from the retained JSON report to
the tables below -- is defined in
[llm-audit-bench](https://github.com/tuminoid/llm-audit-bench)
(`docs/CAPABILITY.md`); this file holds the fleet's campaign inventory and
retained results.

Every host table is a Capability Check v2 campaign. A v1 pass is not a v2
pass: re-check a model at v2 before promoting it.

Capability results never rank model quality or serving performance.

The ds4 runtime's interactive-only models are checked too but not
inventoried here; their results are in [ds4/BENCHMARKS.md](ds4/BENCHMARKS.md).

Schema enforcement is gated because audit tooling consumes structured
verdicts: an endpoint that accepts a JSON schema and returns prose
corrupts them silently, with no error to catch, so the gate requires
enforcement or an honest refusal of the parameter.

## Running a campaign

Follow the campaign procedure in the protocol document, driving the servers
with this repository's targets. Use only the profiles listed for that host in
the inventory below; model configs for another host are not an implied
campaign. Update the host row mechanically from the retained JSON report per
the protocol's mapping, never from the verdict the check prints; record
failures as failures, and never convert manual evidence into a Capability
Check pass. `uv run capability-check --list` (in the llm-audit-bench
checkout) names every retained report and
`uv run capability-check --show FILE` re-prints one.

Audit fitness samples at the model config's `<PREFIX>_SAMPLING`, so the
config must declare it. A check takes about 10 to 80 minutes per model on
the M5, most of it the selection task; `CAPABILITY_FITNESS_SAMPLES=0` makes
an API-only run, which cannot promote a model. A v2 host row adds the audit
fitness column from `checks.audit_fitness.status`.

Local lifecycle:

```bash
make vllm-start MODEL=<profile>
make vllm-capability MODEL=<profile>
make vllm-stop

make ollama-start MODEL=<profile>
make ollama-pull MODEL=<profile>
make ollama-capability MODEL=<profile>
make ollama-stop

make vllm-metal-start MODEL=<profile>
make vllm-metal-capability MODEL=<profile>
make vllm-metal-stop

make splash-start MODEL=<profile>
make splash-capability MODEL=<profile>
make splash-stop

make lmstudio-start MODEL=<profile>
make lmstudio-capability MODEL=<profile>
make lmstudio-stop
```

Remote lifecycle:

```bash
make vllm-remote-status HOST=<host>
make vllm-remote-start HOST=<host> MODEL=<profile>
make vllm-remote-capability HOST=<host> MODEL=<profile>
make vllm-remote-stop HOST=<host>

make ollama-remote-status HOST=<host>
make ollama-remote-start HOST=<host> MODEL=<profile>
make ollama-remote-pull HOST=<host> MODEL=<profile>
make ollama-remote-capability HOST=<host> MODEL=<profile>
make ollama-remote-stop HOST=<host>
```

Always stop the server afterward and confirm resource release, including
after a failed check.

### Identity drift

A digest mismatch distinguishes two cases, and only one is drift. The
Ollama adapters consult the registry's manifest header (a few KB, no
download) before deciding:

- **Stale local store**: the registry still serves the pinned digest --
  the local tag simply predates an upstream tag move. The adapter pulls
  through the managed server automatically, landing exactly the
  already-reviewed artifact, and validates again. No pin changes, no
  human decision consumed. (This recovered the A100 store twice
  and blocked the RTX campaign, all manually, before it was
  automated.)
- **True drift**: the registry serves something other than the pin. The
  refusal stands and names all three digests (registry, pin, local).
  Drift is never permission to update a pin: retain the failed
  artifact, inspect the replacement manifest or Hugging Face revision,
  verify format, quantization, architecture, native context, and
  capabilities, then run one explicit identity override. Repin only
  after that artifact passes. If a benchmarked artifact changed, keep
  its performance numbers historical until the replacement is
  benchmarked -- and remember depth proofs are per digest.

An unreachable registry keeps the plain refusal: recovery is only
automatic when it is provably safe.

### Promotion rule

A model intended for agent workloads must pass identity, streaming, the
non-streaming and streaming tool calls, tool round trip, structured JSON, and
audit fitness at the default sample count.
Its reasoning result must match the model-config expectation. A throughput
result cannot override a capability failure.

Both tool-call checks offer the tools with automatic choice, so they exercise
the model's own tool syntax and the server's configured parser. A named choice
can satisfy the fixture through guided decoding without either being correct,
which is why tool-call evidence recorded before protocol SCHEMA_VERSION 4
proves nothing about parser compatibility.

## Host campaign inventory

### Apple M5 Max

- Splash: `qwen3.6-35b-a3b`, `qwen3.8-27b`
- LM Studio: `qwen3.6-35b-a3b-splash`, `qwen3.8-27b-splash`,
  `qwen3.6-35b-a3b-mlx`, `qwen3.8-27b-mlx`
- vLLM-Metal: `gemma4-31b-4bit`, `granite4.2-30b-4bit`,
  `ornith1.5-35b-a3b-4bit`, `mimo-v2.6-9b-4bit`
- Ollama MLX: `muse-glimmer-30b-mlx`, `nemotron-3.5-lightning-30b-mlx`,
  `nemotron-3.5-super-mlx`

### RTX PRO 3000 Blackwell

- Ollama: `qwen3.6-35b-a3b-reap48`, `saluki-27b`, `lfm2.5-24b-a2b`

### A100-SXM4-80GB

- vLLM: `qwen3.6-35b-a3b-awq`, `qwen3.8-27b`, `qwen3.8-27b-dflash2`,
  `gemma4-26b-a4b-awq`, `qwen3.8-27b-512k`, `mimo-v2.6-9b-awq`
- Ollama: `qwen3.8-flash-next-gguf-iq4xs`, `ornith1.5-35b-a3b`

## Apple M5 Max campaign

Host: MacBook Pro `Mac17,6`, Apple M5 Max, 128 GB unified memory, macOS
27.0.1 except where noted. Capability Check v2 (llm-audit-bench v2.1.0
plus the triage amendment `c0dc34a`), rerun 2026-10-12 from fleet commit
`4c5f585` (the JSON records `2bd6885`, the same change before a rebase):
LM Studio 0.4.25+1 with its Splash engine 0.0.5. JSON files are retained under
`~/.local/state/auditbench/trials/2026-10-12-m5-night/results/`. Audit
fitness ran 4 samples per task at each conf's declared sampling and passes
with at least 11 of 12 samples passed. Four groups differ:

- The Splash rows are Splash 1.3.2 runs from clean trees of its pin
  branch: `qwen3.8-27b` on 2026-10-19 (same harness), `qwen3.6-35b-a3b` on
  2026-10-20 (llm-audit-bench v2.2.0), under
  `~/.local/state/auditbench/trials/2026-10-19-m5-night/splash/` and
  `.../2026-10-20-m5-night/splash/`. A 2026-10-19 qwen3.6 run passed only
  10 of 12, as did a 1.3.1 trial run and same-day 1.0 reruns (9 and 10):
  that profile sits at the fitness limit on every release.
- The LM Studio MLX rows are the 2026-10-14 runs from fleet commit
  `eec6b44` on mlx-llm 1.13.1, which LM Studio installed itself on
  2026-10-12, under
  `~/.local/state/auditbench/trials/2026-10-14-m5-day/results/`.
- The vLLM-Metal rows are the canonical runs of 2026-10-16 and 2026-10-17
  from fleet commit `2e990d6` on vLLM-Metal 0.31.0, under
  `~/.local/state/auditbench/trials/2026-10-16-m5-canonical/results/`.
- The Ollama rows are the canonical runs of 2026-10-17 from fleet commit
  `7fd982d` on Ollama 0.40.6, under
  `~/.local/state/auditbench/trials/2026-10-17-ollama-0406-canonical/results/`.

| Runtime | Profile | Identity | Reasoning | Thinking off | Tool call | Streaming tool call | Tool loop | JSON | Unaided document | Schema enforced | Audit fitness (passed of 12) | Result |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| Splash | `qwen3.6-35b-a3b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| Splash | `qwen3.8-27b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 11/12 (failed: runaway 1) | pass |
| LM Studio | `qwen3.6-35b-a3b-mlx` | pass | pass | unsupported | pass | pass | pass | pass | valid | ignored | pass 11/12 (failed: runaway 1) | fail |
| LM Studio | `qwen3.6-35b-a3b-splash` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | fail 9/12 (failed: instruction 1, missed_findings 1, runaway 1) | fail |
| LM Studio | `qwen3.8-27b-mlx` | pass | pass | unsupported | pass | pass | pass | pass | valid | ignored | pass 12/12 | fail |
| LM Studio | `qwen3.8-27b-splash` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| vLLM-Metal | `gemma4-31b-4bit` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| vLLM-Metal | `granite4.2-30b-4bit` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 11/12 (failed: runaway 1) | pass |
| vLLM-Metal | `mimo-v2.6-9b-4bit` | pass | pass | pass | fail | fail | skipped | pass | valid | enforced | fail 0/12 (failed: no_reasoning 10, runaway 2) | fail |
| vLLM-Metal | `ornith1.5-35b-a3b-4bit` | pass | pass | pass | pass | pass | pass | pass | ignored | enforced | pass 11/12 (failed: runaway 1) | pass |
| Ollama | `muse-glimmer-30b-mlx` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| Ollama | `nemotron-3.5-lightning-30b-mlx` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | fail 8/12 (failed: invented 1, missed_findings 2, missed_required 1) | fail |
| Ollama | `nemotron-3.5-super-mlx` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |

Every checked row's live identity matched the revision or digest pinned
in its model config.

### Findings

- Nine profiles pass: Splash `qwen3.6-35b-a3b` (12 of 12) and
  `qwen3.8-27b` (11 of 12), LM Studio `qwen3.8-27b-splash` (12 of 12),
  vLLM-Metal `gemma4-31b-4bit` (12 of 12), `granite4.2-30b-4bit` and
  `ornith1.5-35b-a3b-4bit` (11 of 12 each), and Ollama
  `nemotron-3.5-super-mlx` and `muse-glimmer-30b-mlx` (12 of 12 each).
- `gemma4-31b-4bit` now enforces the schema: its conf forbids grammar
  whitespace (xgrammar `disable_any_whitespace`, as the A100 Gemma 4 conf
  does). On 2026-09-27 the check hit the 600 s request timeout in the
  whitespace runaway.
- `ornith1.5-35b-a3b-4bit` passes 11 of 12 on 0.31.0 (one selection
  runaway), after 10 of 12 on 0.30.0 (2026-10-12) and 11 on 2026-09-27: it
  sits at the fitness limit. vLLM-Metal replays its sampled draws after a
  restart, so a rerun is not a second result. An exploratory 0.30.0 run at
  12 samples per task passed 31 of 36 (86%, against the gate's 11 of 12):
  all five failures were selection samples (3 runaways, 2 invented).
- MiMo on vLLM-Metal 0.31.0 fails both tool calls with arguments `{}` and
  passes 0 of 12 fitness samples (10 without reasoning). The tool-call
  regression against 0.30.0 is in what the model generates, not in
  parsing: the prompt tokens are identical and greedy decoding diverges
  right after `<function=lookup_issue>`, where 0.31.0 writes a JSON body
  that the `qwen3_xml` parser does not read instead of
  `<parameter=issue_number>`. Retest on the next plugin or mlx-lm bump.
- Both LM Studio MLX rows ignore the schema. The Ollama MLX runner
  enforces it on 0.40.6 for all three profiles; 0.32.14 ignored it, and an
  exploratory 0.40.5 Super VL run from an uncommitted tree ran away in
  structural whitespace. Lightning fails audit fitness (8 of 12).
- Ollama `nemotron-3.5-super-mlx` is the M5 route for Nemotron 3.5 Super VL
  (11.39 sessions/h at 524,288, [ollama/BENCHMARKS.md](ollama/BENCHMARKS.md)).
- LM Studio `qwen3.6-35b-a3b-splash` sits at the fitness limit: two draws
  on 2026-10-12 passed 11 and 9 of 12, after 9 on 2026-09-28. The row is
  the later draw; two of the three draws fail. Splash 1.0's own server
  ranged from 11 to 9 of 12 on the same package, so this shows no engine
  difference.
- On mlx-llm 1.13.1 both MLX profiles still return empty content for the
  schema request. `qwen3.6-35b-a3b-mlx` sits at the fitness limit: an
  exploratory 2026-10-12 draw with the pin overridden failed at 10 of 12
  (instruction 1, invented 1); `qwen3.8-27b-mlx` passed 12 of 12 both
  times. On 1.11.0 (2026-09-28, `bee4a24`) both passed 11 of 12.

## A100-SXM4-80GB campaign

Host: shared A100 test host, reached over ssh through the `HOST` alias
supplied by `.envrc`. Capability Check v2 (`capability-v2`,
SCHEMA_VERSION 5), llm-audit-bench 2.1.0. The vLLM rows ran 2026-10-10/11
from fleet commit `ad06c70` on vLLM 0.31.0 with Transformers 5.15.1;
reports under `auditbench-trials/2026-10-10-v2-canonical/` on the host. The
Ollama rows ran 2026-10-11 from `98e4052` on Ollama 0.40.3; reports under
`auditbench-trials/2026-10-11-ollama-canonical/`. Audit fitness ran 4 samples
per task at each conf's declared sampling and passes with at least 11 of
12 samples passed.

| Runtime | Profile | Identity | Reasoning | Thinking off | Tool call | Streaming tool call | Tool loop | JSON | Unaided document | Schema enforced | Audit fitness (passed of 12) | Result |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| vLLM | `gemma4-26b-a4b-awq` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 11/12 (failed: missed_findings 1) | pass |
| vLLM | `mimo-v2.6-9b-awq` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | fail 5/12 (failed: invented 2, no_reasoning 3, wrong_verdicts 2) | fail |
| vLLM | `qwen3.6-35b-a3b-awq` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| vLLM | `qwen3.8-27b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| vLLM | `qwen3.8-27b-512k` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| vLLM | `qwen3.8-27b-dflash2` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| Ollama | `ornith1.5-35b-a3b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| Ollama | `qwen3.8-flash-next-gguf-iq4xs` | pass | pass | pass | pass | pass | pass | pass | error | enforced | pass 12/12 | pass |

Every row's live identity matched the revision or digest pinned in its
model config.

### Findings

- Seven profiles pass: vLLM `qwen3.6-35b-a3b-awq`, `qwen3.8-27b` (now the
  W4A16 checkpoint), `qwen3.8-27b-dflash2`, `qwen3.8-27b-512k` (12 of 12 each)
  and `gemma4-26b-a4b-awq` (11 of 12), and Ollama `ornith1.5-35b-a3b` and
  `qwen3.8-flash-next-gguf-iq4xs` (12 of 12 each).
- Audit fitness is what v1 could not see. MiMo (5 of 12 on 0.31.0: no
  reasoning, invented findings, wrong triage verdicts) passed every v1
  check and fails here. So did GLM 4.7 Flash (8 of 12 on vLLM, 7 on
  Ollama) and Qwen3 Coder (4 of 12 on vLLM, 5 on Ollama, loops, runaways
  and missed findings); both were dropped from the A100 on 2026-10-12, as
  were the Ollama copies of Qwen3.6, Qwen3.8 27B and Gemma 4 26B, which
  passed but lose to their vLLM profiles. Their rows are in git history.
- `gemma4-26b-a4b-awq` and `qwen3.8-27b-512k` failed only schema
  enforcement (`whitespace_runaway`) through the 2026-09-27 campaign.
  Their confs now forbid grammar whitespace
  (`VLLM_STRUCTURED_OUTPUTS_CONFIG`, xgrammar), and both enforce the
  schema and pass. The 512k profile keeps the FP8 weights and differs from
  the former FP8 `qwen3.8-27b` only by static YaRN at factor 2.0.
- `qwen3.8-flash-next-gguf-iq4xs`'s unaided document is `error`: that
  request kills the CUDA llama.cpp path with an illegal memory access and
  an HTTP 500 (reproducible since 0.33.3; diagnosis and retest condition
  in its conf). `unaided` never gates.
- `mimo-v2.6-9b-awq` runs on its fixed chat template
  (`VLLM_CHAT_TEMPLATE`); the API checks pass, audit fitness does not.
- `qwen3.8-27b-dflash2` (FP8 target) passes check for check like the plain
  profiles, so the drafter changes no response semantics.

## RTX PRO 3000 Blackwell campaign

Host: local laptop, RTX PRO 3000 Blackwell Generation
Laptop GPU, sm_120, 12,227 MiB VRAM, Intel Core Ultra 9 285H, 62 GiB
RAM.

### Capability Check v2, Ollama 0.40.6

Run 2026-10-17 (`capability-v2`, llm-audit-bench 2.1.0 plus `c0dc34a`) on
Ollama 0.40.6 from fleet commit `7fd982d`; the reports are retained with
the trial evidence on the host and copied under the M5 trial's `rtx/`. The
0.40.3 rows they replace (2026-10-12/14) are in git history.

| Runtime | Profile | Identity | Reasoning | Thinking off | Tool call | Streaming tool call | Tool loop | JSON | Unaided document | Schema enforced | Audit fitness (passed of 12) | Result |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| Ollama | `lfm2.5-24b-a2b` | pass | pass | unsupported | pass | pass | pass | pass | valid | enforced | fail 2/12 (failed: format 3, invented 4, wrong_verdicts 3) | fail |
| Ollama | `qwen3.6-35b-a3b-reap48` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 11/12 (failed: instruction 1) | pass |
| Ollama | `saluki-27b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 11/12 (failed: invented 1) | pass |

Every live identity matched its pinned digest. `lfm2.5-24b-a2b` fails
audit fitness (2 of 12; 4 of 12 on 0.40.3) and has no thinking-off check,
since its card documents no control; it is kept for interactive use, not
for audit work. REAP-48 passed 11, 12 and 11 of 12 on 0.40.3 and 11 on
0.40.6; Saluki 11 of 12 on both. Saluki's exploratory 0.40.3 runs at
65,536 (q8_0 KV) and 131,072 (q4_0) passed 10, 11 and 11 of 12. Two
other candidates fit the GPU and failed audit fitness and were not
committed: the byteshape IQ2_S Qwen3.6 35B-A3B (10 of 12) and Ornith 1.5
9B (9 of 12).

Every other RTX profile was dropped on 2026-10-12. The four that did not fit
the GPU went first; the small models that passed v1 (Ollama `qwen3.5-4b`,
`qwen3.5-9b`, `gemma4-e2b`, `gemma4-12b`, vLLM `qwen3.5-4b-awq`,
`gemma4-e2b-awq`) then failed audit fitness on v2 on every runtime, in every
run but one 11-of-12 pass among `gemma4-12b`'s five (2026-10-08 to
2026-10-12), and the vLLM `nemotron-nano-9b-awq` was in no inventory. Their v1
and v2 rows are in git history.
