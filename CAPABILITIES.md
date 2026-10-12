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

The M5 and A100 tables are Capability Check v2 campaigns; the RTX table
below is v1 until its v2 campaign lands. A v1 pass is not a v2 pass:
re-check a model at v2 before promoting it.

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
- vLLM-Metal: `qwen3.6-35b-a3b-4bit`, `qwen3.8-27b-4bit`,
  `gemma4-31b-4bit`,
  `granite4.2-30b-4bit`, `ornith1.5-35b-a3b-4bit`
- vLLM-Metal: `nemotron-3.5-lightning-30b-4bit`, `mimo-v2.6-9b-4bit`
- Ollama MLX: `muse-glimmer-30b-mlx`, `nemotron-3.5-lightning-30b-mlx`

### RTX PRO 3000 Blackwell

- vLLM: `qwen3.5-4b-awq`, `gemma4-e2b-awq`
- Ollama retained profiles: `qwen3.5-4b`, `gemma4-e2b`, `qwen3.5-9b`,
  `gemma4-12b`, `qwen3.6-35b-a3b`, `qwen3.8-27b`
- Ollama candidate outside the canonical throughput table:
  `muse-glimmer-30b`

### A100-SXM4-80GB

- vLLM: `qwen3-coder-30b`, `glm4.7-flash-awq`,
  `qwen3.6-35b-a3b-awq`, `qwen3.8-27b`, `qwen3.8-27b-dflash2`,
  `gemma4-26b-a4b-awq`, `qwen3.8-27b-512k`, `mimo-v2.6-9b-awq`
- Ollama: `qwen3-coder-30b`, `glm4.7-flash`, `qwen3.6-35b-a3b`,
  `qwen3.8-27b-native`, `gemma4-26b`, `qwen3.8-flash-next-gguf-iq4xs`,
  `ornith1.5-35b-a3b` (the two qwen3.8 profiles need
  `OLLAMA_VERSION=0.34.2` and Ornith `OLLAMA_VERSION=0.40.1` on every
  remote lifecycle target)

## Apple M5 Max campaign

Host: MacBook Pro `Mac17,6`, Apple M5 Max, 128 GB unified memory, macOS
27.0. Capability Check v2 (llm-audit-bench v2.0.0, `capability-v2`,
SCHEMA_VERSION 5), run 2026-09-27/28 from fleet commit `bee4a24`:
vLLM-Metal 0.30.0, Splash 1.0, LM Studio 0.4.25+1 (Splash engine 0.0.5,
mlx-llm 1.11.0), Ollama 0.32.14 for MLX. Audit fitness ran 4 samples per
task at each conf's declared sampling and fails at 2 failed samples of 12.
The Splash rows are the Splash 1.3.1 rerun on 2026-10-11 from fleet commit
`036bfd0` (llm-audit-bench v2.1.0 plus the triage amendment `c0dc34a`),
serving the mlx-community targets that replaced the packages. Splash 1.0
passed both on 2026-09-27, but same-day 1.0 qwen3.6 reruns on 2026-10-12
failed 3/12 and 2/12: that profile sits at the fitness limit on either
release.

| Runtime | Profile | Identity | Reasoning | Thinking off | Tool call | Streaming tool call | Tool loop | JSON | Unaided document | Schema enforced | Audit fitness (failed of 12) | Result |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| Splash | `qwen3.6-35b-a3b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 1/12 (invented 1) | pass |
| Splash | `qwen3.8-27b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 0/12 | pass |
| LM Studio | `qwen3.6-35b-a3b-mlx` | pass | pass | unsupported | pass | pass | pass | pass | valid | ignored | pass 1/12 (format 1) | fail |
| LM Studio | `qwen3.6-35b-a3b-splash` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | fail 3/12 (instruction 1, invented 1, missed_findings 1) | fail |
| LM Studio | `qwen3.8-27b-mlx` | pass | pass | unsupported | pass | pass | pass | pass | valid | ignored | pass 1/12 (format 1) | fail |
| LM Studio | `qwen3.8-27b-splash` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 0/12 | pass |
| vLLM-Metal | `gemma4-31b-4bit` | pass | pass | pass | pass | pass | pass | pass | valid | timeout (600 s) | pass 0/12 | fail |
| vLLM-Metal | `granite4.2-30b-4bit` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 0/12 | pass |
| vLLM-Metal | `mimo-v2.6-9b-4bit` | pass | pass | pass | pass | pass | pass | pass | ignored | enforced | fail 12/12 (missed_findings 1, no_reasoning 10, runaway 1) | fail |
| vLLM-Metal | `nemotron-3.5-lightning-30b-4bit` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | fail 2/12 (missed_findings 2) | fail |
| vLLM-Metal | `ornith1.5-35b-a3b-4bit` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 1/12 (runaway 1) | pass |
| vLLM-Metal | `qwen3.6-35b-a3b-4bit` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | fail 2/12 (invented 1, missed_findings 1) | fail |
| vLLM-Metal | `qwen3.8-27b-4bit` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | fail 3/12 (format 1, runaway 2) | fail |
| Ollama | `muse-glimmer-30b-mlx` | pass | pass | pass | pass | pass | pass | pass | valid | ignored | pass 0/12 | fail |
| Ollama | `nemotron-3.5-lightning-30b-mlx` | pass | pass | pass | pass | pass | pass | pass | json_only | ignored | fail 5/12 (invented 1, leak 1, missed_findings 2, runaway 1) | fail |

Every checked row's live identity matched the revision or digest pinned
in its model config.

### Findings

- Five profiles pass: Splash `qwen3.6-35b-a3b` (1/12) and `qwen3.8-27b`
  (0/12), LM Studio `qwen3.8-27b-splash` (0/12), and vLLM-Metal
  `granite4.2-30b-4bit` (0/12) and `ornith1.5-35b-a3b-4bit` (1/12).
- On vLLM-Metal both Qwen profiles fail audit fitness where Splash and the
  A100 pass the same models: `qwen3.6-35b-a3b-4bit` 2/12 (an invented path
  and a finding filed against the wrong file), `qwen3.8-27b-4bit` 3/12
  (two selection runaways at 32,768 tokens). Their 0.29.0 trial runs
  failed the same way (qwen3.8 two runaways) or at 1/12 (qwen3.6), and a
  qwen3.6 sample replayed token for token across the plugin bump, so this
  is the 4-bit MLX models at sampling, not the 0.30.0 pin.
- MiMo on vLLM-Metal fails 12 of 12: ten samples answered without
  reasoning. Its API checks pass.
- Every MLX-format profile outside vLLM-Metal fails schema enforcement
  (`ignored`): both Ollama MLX rows and both LM Studio MLX rows. Their
  audit fitness passes except nemotron (5/12).
- LM Studio `qwen3.6-35b-a3b-splash` fails audit fitness (3/12); Splash
  1.0's own server ranged from 1/12 to 3/12 on the same package, so this
  shows no engine difference.
- `gemma4-31b-4bit` passes audit fitness (0/12) and fails only schema
  enforcement, whose check hit the 600 s request timeout: the
  whitespace runaway v1 recorded.

## A100-SXM4-80GB campaign

Host: shared A100 test host, reached over ssh through the `HOST` alias
supplied by `.envrc`. Capability Check v2 (`capability-v2`,
SCHEMA_VERSION 5). The vLLM rows and Ollama `ornith1.5-35b-a3b` ran
2026-10-10/11 from fleet commit `ad06c70` (llm-audit-bench 2.1.0): vLLM
0.31.0 with Transformers 5.15.1, Ollama 0.40.1 for Ornith; reports under
`auditbench-trials/2026-10-10-v2-canonical/` on the host. The other Ollama
rows ran 2026-09-27 from `d9ad1a7` (llm-audit-bench v2.0.0) on Ollama
0.34.2 for `qwen3.8-27b-native` and `qwen3.8-flash-next-gguf-iq4xs` and
0.32.14 for the rest, pins unchanged since; reports under
`auditbench-trials/2026-09-27-v2-canonical/`. Audit fitness ran 4 samples
per task at each conf's declared sampling and fails at 2 failed samples
of 12.

| Runtime | Profile | Identity | Reasoning | Thinking off | Tool call | Streaming tool call | Tool loop | JSON | Unaided document | Schema enforced | Audit fitness (failed of 12) | Result |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| vLLM | `gemma4-26b-a4b-awq` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 1/12 (missed_findings 1) | pass |
| vLLM | `glm4.7-flash-awq` | pass | pass | pass | pass | pass | pass | pass | ignored | enforced | fail 4/12 (instruction 1, invented 1, missed_findings 2) | fail |
| vLLM | `mimo-v2.6-9b-awq` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | fail 7/12 (invented 2, no_reasoning 3, wrong_verdicts 2) | fail |
| vLLM | `qwen3-coder-30b` | pass | pass | unsupported | fail | fail | not run | pass | valid | whitespace_runaway | fail 8/12 (invented 1, loop 1, missed_findings 4, runaway 2) | fail |
| vLLM | `qwen3.6-35b-a3b-awq` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 0/12 | pass |
| vLLM | `qwen3.8-27b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 0/12 | pass |
| vLLM | `qwen3.8-27b-512k` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 0/12 | pass |
| vLLM | `qwen3.8-27b-dflash2` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 0/12 | pass |
| Ollama | `gemma4-26b` | pass | pass | pass | pass | pass | pass | pass | valid | truncated | fail 2/12 (incomplete 1, invented 1) | fail |
| Ollama | `glm4.7-flash` | pass | pass | pass | pass | pass | pass | pass | ignored | enforced | fail 6/12 (incomplete 1, invented 2, missed_findings 2, wrong_verdicts 1) | fail |
| Ollama | `ornith1.5-35b-a3b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 0/12 | pass |
| Ollama | `qwen3-coder-30b` | pass | pass | unsupported | pass | pass | pass | pass | valid | enforced | fail 8/12 (invented 1, loop 2, missed_findings 4, missed_required 1) | fail |
| Ollama | `qwen3.6-35b-a3b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 1/12 (invented 1) | pass |
| Ollama | `qwen3.8-27b-native` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 0/12 | pass |
| Ollama | `qwen3.8-flash-next-gguf-iq4xs` | pass | pass | pass | pass | pass | pass | pass | error | enforced | pass 0/12 | pass |

Every row's live identity matched the revision or digest pinned in its
model config.

### Findings

- Nine profiles pass: vLLM `qwen3.6-35b-a3b-awq`, `qwen3.8-27b` (now the
  W4A16 checkpoint), `qwen3.8-27b-dflash2`, `qwen3.8-27b-512k` (0/12 each)
  and `gemma4-26b-a4b-awq` (1/12), and Ollama `ornith1.5-35b-a3b` (0/12),
  `qwen3.6-35b-a3b` (1/12), `qwen3.8-27b-native` (0/12) and
  `qwen3.8-flash-next-gguf-iq4xs` (0/12).
- Audit fitness is what v1 could not see. GLM 4.7 Flash (4/12 on vLLM
  0.31.0, 6/12 on Ollama), Qwen3 Coder (8/12 on both runtimes) and MiMo
  (7/12 on 0.31.0: no reasoning, invented findings, wrong triage verdicts)
  passed every v1 check and fail here; Coder's failures are loops,
  runaways and missed findings. Gemma 4 26B on Ollama fails at the limit
  (2/12).
- `gemma4-26b-a4b-awq` and `qwen3.8-27b-512k` failed only schema
  enforcement (`whitespace_runaway`) through the 2026-09-27 campaign.
  Their confs now forbid grammar whitespace
  (`VLLM_STRUCTURED_OUTPUTS_CONFIG`, xgrammar), and both enforce the
  schema and pass. The 512k profile keeps the FP8 weights and differs from
  the former FP8 `qwen3.8-27b` only by static YaRN at factor 2.0.
- Qwen3 Coder on vLLM still returns two calls for the one-call tool
  fixture under automatic tool choice; the same checkpoint passes both
  tool checks on Ollama.
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
RAM. Run date: 2026-09-10, protocol SCHEMA_VERSION 4, all nine managed
operating points, vLLM 0.27.1 and Ollama 0.32.14. This is the host's
first Capability Check v1 record; the partial manual parser and
tool-call notes in the benchmark documents are superseded and were not
promoted into it.

Both vLLM rows were re-run on 2026-09-11 after the host's local vLLM
pin was aligned to the fleet default, 0.28.0 with Transformers 5.15.1,
and the table carries those results. `qwen3.5-4b-awq` is unchanged;
`gemma4-e2b-awq` changed failure shape, which is the finding below. The
Ollama rows are untouched by that bump, and the AuditBench rows in
`vllm/BENCHMARKS.md` remain 0.27.1 measurements until re-canonicalized,
so capability and throughput provenance differ on this host for now.

| Runtime | Profile | Identity | Reasoning | Thinking off | Tool call | Streaming tool call | Tool loop | JSON | Unaided document | Schema enforced | Result |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| vLLM | `qwen3.5-4b-awq` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| vLLM | `gemma4-e2b-awq` | pass | pass | pass | pass | pass | pass | pass | valid | ignored | fail |
| Ollama | `qwen3.5-4b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| Ollama | `gemma4-e2b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| Ollama | `qwen3.5-9b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| Ollama | `gemma4-12b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| Ollama | `qwen3.6-35b-a3b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| Ollama | `qwen3.8-27b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| Ollama | `muse-glimmer-30b` | pass | pass | pass | pass | pass | pass | pass | valid | ignored | fail |

Every row verified live model identity against its config's pinned
revision or digest, and every row produced a valid unaided document.
Both failures are enforcement failures after seven passing checks.

### Findings

- Seven of nine profiles pass. Every profile on both runtimes passes
  both tool-call checks under automatic tool choice, the tool-result
  continuation, and its configured reasoning semantics, so this host's
  vLLM parsers and Ollama's llama.cpp runner handle every dialect in
  its inventory. No profile is demoted for tool behavior.
- `gemma4-e2b-awq` on vLLM fails schema enforcement on both engine
  versions this host has run, but by different mechanisms, and the pin
  bump made it worse. On 0.27.1 with Transformers 5.14.1 it was
  `whitespace_runaway`: the grammar was applied and the model emitted
  structural whitespace until the protocol's 16,384-token budget ended,
  123 s in. On 0.28.0 with Transformers 5.15.1 the schema is simply
  `ignored` -- the endpoint accepts it, returns HTTP 200 and a 5.9k-character
  Markdown audit report in about 10 s, `finish_reason` `stop`.
  Reproducible 3/3, and the server logs nothing about a grammar
  fallback: startup reports `structured_outputs_config` with
  `backend='auto'`, and the failing request produces no grammar-related
  line at any level. `qwen3.5-4b-awq` enforced correctly on the same
  0.28.0 engine minutes earlier, so grammars work in general here and
  this is specific to the Gemma 4 path.
- That is a regression in kind, not just in verdict. A loud failure that
  burns the budget is visible; silent non-enforcement is the exact shape
  this gate exists to catch, because a caller receives prose while
  believing a schema was applied. It is also the first time a vLLM CUDA
  profile has produced the `ignored` outcome anywhere in the fleet --
  previously only Ollama's MLX runner did. Neither engine version is
  usable for schema-constrained work with this checkpoint; 0.28.0 is
  kept for the Gemma 4 per-layer head-dim fix and fleet alignment, since
  the gate result is a failure either way.
- Gemma 4's Ollama pairings are unaffected and pass: `gemma4-e2b` and
  `gemma4-12b` both report `enforced`, where the A100's larger
  `gemma4-26b` under the same llama.cpp runner fails as plain
  `truncated`. Bounded grammar whitespace is enough for the small and
  mid Gemma 4 tiers to finish the document in budget. Gemma 4 remains
  usable for structured work on this host only through Ollama.
- `muse-glimmer-30b` fails `json_schema` as `ignored`, reproducibly
  (2/2, 183.0 s and 183.8 s). The retained document shows the recorded
  classification understates it: the schema-constrained response is
  complete, structurally valid JSON of 1,905 characters, but the raw
  `<|eot|>` end-of-turn marker is left in `content`, so the payload does
  not parse. `finish_reason` is `stop`, not `length`, so this is neither
  budget truncation nor the vLLM whitespace runaway. Its MLX sibling
  leaks raw channel markers on the same family, so this is a
  muse-glimmer template/parser mismatch in Ollama rather than a
  property of either runner. The diagnosis and retest condition are in
  the model config.
- `muse-glimmer-30b` was absent from the local store and was pulled
  through the managed server for this campaign. Its identity matched the
  pinned digest `de878ce3` on the first pull -- no drift, unlike the two
  tag moves its MLX sibling has consumed on the M5.
- That conf declared no thinking-disable control, with a note to try
  `think-false` on this host first. It works: `think: false` returns
  correct content with an empty reasoning field, so the conf is repinned
  from `none` and the row records a real result instead of
  `unsupported`. The recorded run is the conf-declared one, not the
  override that established the control.
- The default 600 s request timeout does not fit this host's
  CPU-offloaded profiles. `qwen3.8-27b`, at 2.93 tok/s decode, spent
  430 s on `json_schema` and 353 s on `structured_json`; it was checked
  at `CAPABILITY_TIMEOUT=5400`, `qwen3.6-35b-a3b` at 1800, and
  `muse-glimmer-30b` at 3600, with the protocol token budget untouched.
  Both CPU-offloaded profiles pass every check, so partial GPU residency
  costs latency here and nothing else.
- Capability residency is not the benchmark allocation, and two rows
  differ from their retained bench cells at the same digest:
  `qwen3.6-35b-a3b` loaded 15.39 GiB CPU + 6.31 GiB GPU against a bench
  row of 14.53/10.21, and `gemma4-e2b` loaded 1.90 GiB against 2.66 GiB
  measured at four slots. Capability loads one slot and proves response
  semantics; it establishes neither an operating point nor a survivable
  context depth.
- Every teardown released the GPU to the host's 14 MiB baseline,
  including after both failed checks.
