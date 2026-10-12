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
- vLLM-Metal: `qwen3.6-35b-a3b-4bit`, `qwen3.8-27b-4bit`,
  `gemma4-31b-4bit`,
  `granite4.2-30b-4bit`, `ornith1.5-35b-a3b-4bit`
- vLLM-Metal: `nemotron-3.5-lightning-30b-4bit`, `mimo-v2.6-9b-4bit`
- Ollama MLX: `muse-glimmer-30b-mlx`, `nemotron-3.5-lightning-30b-mlx`

### RTX PRO 3000 Blackwell

- Ollama: `saluki-27b`

### A100-SXM4-80GB

- vLLM: `qwen3-coder-30b`, `glm4.7-flash-awq`,
  `qwen3.6-35b-a3b-awq`, `qwen3.8-27b`, `qwen3.8-27b-dflash2`,
  `gemma4-26b-a4b-awq`, `qwen3.8-27b-512k`, `mimo-v2.6-9b-awq`
- Ollama: `qwen3-coder-30b`, `glm4.7-flash`, `qwen3.6-35b-a3b`,
  `qwen3.8-27b-native`, `gemma4-26b`, `qwen3.8-flash-next-gguf-iq4xs`,
  `ornith1.5-35b-a3b` (`qwen3-coder-30b` needs `OLLAMA_VERSION=0.32.14`
  on every remote lifecycle target)

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
SCHEMA_VERSION 5), llm-audit-bench 2.1.0. The vLLM rows ran 2026-10-10/11
from fleet commit `ad06c70` on vLLM 0.31.0 with Transformers 5.15.1;
reports under `auditbench-trials/2026-10-10-v2-canonical/` on the host. The
Ollama rows ran 2026-10-11 from `98e4052` on Ollama 0.40.3, 0.32.14 for
`qwen3-coder-30b`; reports under
`auditbench-trials/2026-10-11-ollama-canonical/`. Audit fitness ran 4 samples
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
| Ollama | `gemma4-26b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 1/12 (invented 1) | pass |
| Ollama | `glm4.7-flash` | pass | pass | pass | pass | pass | pass | pass | ignored | enforced | fail 5/12 (incomplete 1, instruction 1, invented 1, wrong_verdicts 2) | fail |
| Ollama | `ornith1.5-35b-a3b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 0/12 | pass |
| Ollama | `qwen3-coder-30b` | pass | pass | unsupported | pass | pass | pass | pass | valid | enforced | fail 7/12 (invented 2, loop 1, missed_findings 3, missed_required 1) | fail |
| Ollama | `qwen3.6-35b-a3b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 0/12 | pass |
| Ollama | `qwen3.8-27b-native` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 1/12 (format 1) | pass |
| Ollama | `qwen3.8-flash-next-gguf-iq4xs` | pass | pass | pass | pass | pass | pass | pass | error | enforced | pass 0/12 | pass |

Every row's live identity matched the revision or digest pinned in its
model config.

### Findings

- Ten profiles pass: vLLM `qwen3.6-35b-a3b-awq`, `qwen3.8-27b` (now the
  W4A16 checkpoint), `qwen3.8-27b-dflash2`, `qwen3.8-27b-512k` (0/12 each)
  and `gemma4-26b-a4b-awq` (1/12), and Ollama `ornith1.5-35b-a3b`,
  `qwen3.6-35b-a3b`, `qwen3.8-flash-next-gguf-iq4xs` (0/12 each),
  `qwen3.8-27b-native` and `gemma4-26b` (1/12 each).
- Audit fitness is what v1 could not see. GLM 4.7 Flash (4/12 on vLLM
  0.31.0, 5/12 on Ollama), Qwen3 Coder (8/12 on vLLM, 7/12 on Ollama) and MiMo
  (7/12 on 0.31.0: no reasoning, invented findings, wrong triage verdicts)
  passed every v1 check and fail here; Coder's failures are loops,
  runaways and missed findings. Gemma 4 26B on Ollama, which failed at
  the limit (2/12) and schema enforcement (`truncated`) on 0.32.14, passes
  both on 0.40.3.
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
RAM.

### Capability Check v2, Ollama 0.40.3

Run 2026-10-12 (`capability-v2`, SCHEMA_VERSION 5, llm-audit-bench 2.1.0)
from fleet commit `1e7318d` on Ollama 0.40.3; the report is retained with
the trial evidence on the host.

| Runtime | Profile | Identity | Reasoning | Thinking off | Tool call | Streaming tool call | Tool loop | JSON | Unaided document | Schema enforced | Audit fitness (failed of 12) | Result |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| Ollama | `saluki-27b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 1/12 (format 1) | pass |

Its live identity matched the pinned digest. Saluki's exploratory runs at
65,536 (q8_0 KV) and 131,072 (q4_0) gave 2/12, 1/12 and 1/12.

Every other RTX profile was dropped on 2026-10-12. The four that did not fit
the GPU went first; the small models that passed v1 (Ollama `qwen3.5-4b`,
`qwen3.5-9b`, `gemma4-e2b`, `gemma4-12b`, vLLM `qwen3.5-4b-awq`,
`gemma4-e2b-awq`) then failed audit fitness on v2 on every runtime, in every
run but one 1/12 of `gemma4-12b`'s five (2026-10-08 to 2026-10-12), and the
vLLM `nemotron-nano-9b-awq` was in no inventory. Their v1 and v2 rows are in
git history.
