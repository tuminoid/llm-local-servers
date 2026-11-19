# Capability Check results

Capability Check is the gate for models in the serving inventory. Its
verdict is the compatibility of the engine and model combination: the
response semantics agents need, and audit-shaped work finished without engine
failures at the declared sampling. Audit aptitude is scored beside it, never
a verdict. AuditBench separately measures serving performance and
capacity. The protocol -- fixed checks, model expectations, and the mapping
from the retained JSON report to the tables below -- is defined in
[llm-audit-bench](https://github.com/tuminoid/llm-audit-bench)
(`docs/CAPABILITY.md`); this file holds the fleet's campaign inventory and
retained results.

Capability results never rank model quality or serving performance.

The ds4 runtime's interactive-only models are checked too but not
inventoried here; their results are in [ds4/BENCHMARKS.md](ds4/BENCHMARKS.md).

Schema enforcement is recorded but advisory (llm-audit-bench 2.3.0): no
audit client depends on constrained decoding yet, and its failures are
engine gaps, so a failed `json_schema` check never fails a row. Rows
recorded earlier that failed only on it are passes.

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

Fitness samples at the model config's `<PREFIX>_SAMPLING`, so the config
must declare it.
`CAPABILITY_FITNESS_SAMPLES=0` makes an API-only run, which cannot promote a
model. `CAPABILITY_TIME_LIMIT=<minutes>` stops starting samples on a slow
host; the report keeps what ran and, unless a check already failed, reads
`undecided`, as does a local run stopped with one SIGINT or SIGTERM (a
second aborts it). Remote targets run over ssh without a tty, so a Ctrl-C
there leaves the remote check running: bound remote runs with the time
limit, or stop the process on the host. A host row follows the protocol
document's projection table.

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

make kapitsa-start MODEL=<profile>
make kapitsa-capability MODEL=<profile>
make kapitsa-stop
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

make strata-remote-status HOST=<host>
make strata-remote-start HOST=<host> MODEL=<profile>
make strata-remote-capability HOST=<host> MODEL=<profile>
make strata-remote-stop HOST=<host>
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

A model intended for agent workloads is promoted by the protocol
document's promotion rule: compatibility `passed`, never `undecided`, at the
default sample count, with tools declared in its model config. Its
reasoning result must match the model-config expectation. A throughput
result cannot override a capability failure.

Both tool-call checks offer the tools with automatic choice, so they exercise
the model's own tool syntax and the server's configured parser. A named choice
can satisfy the fixture through guided decoding without either being correct,
which is why tool-call evidence recorded before protocol SCHEMA_VERSION 4
proves nothing about parser compatibility.

## Host campaign inventory

### Apple M5 Max

- Splash: `qwen3.6-35b-a3b`, `qwen3.8-27b`, `qwen3.8-flash-next-q2`,
  `qwen3.8-flash-next-iq3s`, `flint-gguf`, `ornith1.5-122b`,
  `ornith1.5-35b-a3b`, `bonsai2-27b-pq2`
- LM Studio: `qwen3.6-35b-a3b-splash`, `qwen3.8-27b-splash`,
  `qwen3.6-35b-a3b-mlx`, `qwen3.8-27b-mlx`
- vLLM-Metal: `granite4.2-30b-4bit`
- Ollama MLX: `muse-glimmer-30b-mlx`, `nemotron-3.5-lightning-30b-mlx`
  (interactive), `nemotron-3.5-super-mlx`, `gemma4-26b-mlx` (interactive)
- Ollama GGUF: `nemotron-3.5-bolt-74b-a9b-q3kxl`, `mimo-v2.6-flash-q2ks`,
  `nanbeige4.3-33b-q4km`
- ds4: `qwen3.8-flash-next-q4`
- Kapitsa: `clover-35b-a3b`

### RTX PRO 3000 Blackwell

- Ollama: `qwen3.6-35b-a3b-reap48`, `saluki-27b`, `lfm2.5-24b-a2b`

### A100-SXM4-80GB

- vLLM: `qwen3.6-35b-a3b-awq`, `qwen3.8-27b`, `qwen3.8-27b-dflash2`,
  `gemma4-26b-a4b-awq`, `qwen3.8-27b-512k`, `mimo-v2.6-9b-awq`
- Ollama: `ornith1.5-35b-a3b`, `nemotron-3.5-bolt-74b-a9b-iq2`,
  `flint-40b-a2b-nvfp4`
- Strata: `qwen3.8-flash-next-nvfp4`, `deepseek-v4.1-flash-coder-iq2xxs`
  and `deepseek-v4.1-flash-q2` (both fail audit fitness)

## Apple M5 Max campaign

Host: MacBook Pro `Mac17,6`, Apple M5 Max, 128 GB unified memory, macOS
27.0.1 except where noted. Capability Check v2 (llm-audit-bench v2.1.0
plus the triage amendment `c0dc34a`), rerun 2026-10-12 from fleet commit
`4c5f585` (the JSON records `2bd6885`, the same change before a rebase):
LM Studio 0.4.25+1 with its Splash engine 0.0.5. JSON files are retained under
`~/.local/state/auditbench/trials/2026-10-12-m5-night/results/`. Audit
fitness ran 4 samples per task at each conf's declared sampling and passes
with at least 11 of 12 samples passed. Six groups differ:

- The Splash rows are Splash 1.5.0 runs (llm-audit-bench 2.4.0) from clean
  trees: `qwen3.6-35b-a3b` and `qwen3.8-27b` of 2026-10-31 and Bonsai 2,
  Flint and Ornith of 2026-10-30 from the trial tree `18bf1a9`, Flash-Next
  IQ3_S of 2026-10-30 from `d5c9a46`, under
  `~/.local/state/auditbench/trials/2026-10-30-m5-night/splash/`, and
  Flash-Next Q2_0 of 2026-10-31 from `a815828`, under
  `.../2026-10-31-flash-next-q2-confirm/splash/`, and Ornith 1.5 35B of
  2026-11-15 (llm-audit-bench 2.5.0) from the trial commit `54822f2`, under
  `.../2026-11-15-m5/splash/`. On 1.3.2
  a 2026-10-19 qwen3.6 run passed only 10 of 12, as did a 1.3.1 trial run
  and same-day 1.0 reruns (9 and 10): that profile sits at the fitness
  limit on every release.
- The LM Studio MLX rows are the 2026-10-14 runs from fleet commit
  `eec6b44` on mlx-llm 1.13.1, which LM Studio installed itself on
  2026-10-12, under
  `~/.local/state/auditbench/trials/2026-10-14-m5-day/results/`.
- The vLLM-Metal rows are the canonical runs of 2026-10-16 and 2026-10-17
  from fleet commit `2e990d6` on vLLM-Metal 0.31.0, under
  `~/.local/state/auditbench/trials/2026-10-16-m5-canonical/results/`.
- The Ollama rows ran on Ollama 0.40.16 on 2026-11-15/16 (llm-audit-bench
  2.5.0) from the clean trial commit `54822f2` (this pin with the same
  profile files), and Gemma 4 26B-A4B's on 2026-11-16 from the trial
  commit `6a91a36`, under
  `~/.local/state/auditbench/trials/2026-11-15-m5/ollama/`.
- The ds4 row ran 2026-10-23 (llm-audit-bench 2.3.0) from fleet commit
  `3c3a5ab`, under `~/.local/state/auditbench/trials/2026-10-22-night/ds4/`.
- The Kapitsa row ran 2026-11-15 on Kapitsa 0.2.36 (llm-audit-bench 2.5.0)
  from the same trial commit, under
  `~/.local/state/auditbench/trials/2026-11-15-m5/kapitsa/`.

| Runtime | Profile | Identity | Reasoning | Thinking off | Tool call | Streaming tool call | Tool loop | JSON | Unaided document | Schema enforced | Audit fitness (passed of 12) | Result |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| Splash | `bonsai2-27b-pq2` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| Splash | `flint-gguf` | pass | pass | unsupported | pass | pass | pass | pass | valid | enforced | pass 11/12 (failed: wrong_verdicts 1) | pass |
| Splash | `ornith1.5-122b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| Splash | `ornith1.5-35b-a3b` | pass | pass | pass | pass | pass | pass | pass | json only | enforced | pass 12/12 | pass |
| Splash | `qwen3.8-flash-next-iq3s` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| Splash | `qwen3.8-flash-next-q2` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| Splash | `qwen3.6-35b-a3b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| Splash | `qwen3.8-27b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 11/12 (failed: format 1) | pass |
| LM Studio | `qwen3.6-35b-a3b-mlx` | pass | pass | unsupported | pass | pass | pass | pass | valid | ignored | pass 11/12 (failed: runaway 1) | pass |
| LM Studio | `qwen3.6-35b-a3b-splash` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | fail 9/12 (failed: instruction 1, missed_findings 1, runaway 1) | fail |
| LM Studio | `qwen3.8-27b-mlx` | pass | pass | unsupported | pass | pass | pass | pass | valid | ignored | pass 12/12 | pass |
| LM Studio | `qwen3.8-27b-splash` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| vLLM-Metal | `granite4.2-30b-4bit` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 11/12 (failed: runaway 1) | pass |
| Ollama | `gemma4-26b-mlx` | pass | pass | pass | pass | pass | pass | pass | valid | whitespace runaway | pass 12/12 | pass |
| Ollama | `mimo-v2.6-flash-q2ks` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| Ollama | `muse-glimmer-30b-mlx` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | fail 10/12 (failed: invented 2) | fail |
| Ollama | `nanbeige4.3-33b-q4km` | pass | pass | pass | pass | pass | pass | pass | valid | unsupported | fail 9/12 (failed: incomplete 1, runaway 2) | fail |
| Ollama | `nemotron-3.5-lightning-30b-mlx` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | fail 9/12 (failed: invented 1, missed_findings 1, leak 1) | fail |
| Ollama | `nemotron-3.5-bolt-74b-a9b-q3kxl` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| Ollama | `nemotron-3.5-super-mlx` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 11/12 (failed: invented 1) | pass |
| ds4 | `qwen3.8-flash-next-q4` | pass | pass | pass | pass | pass | pass | pass | valid | ignored | pass 12/12 | pass |
| Kapitsa | `clover-35b-a3b` | pass | pass | pass | pass | pass | pass | pass | valid | unsupported | pass 12/12 | pass |

Every checked row's live identity matched the revision or digest pinned
in its model config.

### Findings

- Eighteen profiles pass: Splash `qwen3.6-35b-a3b`, `qwen3.8-flash-next-q2`,
  `qwen3.8-flash-next-iq3s`, `ornith1.5-122b`, `ornith1.5-35b-a3b` and
  `bonsai2-27b-pq2` (12 of 12 each), `qwen3.8-27b` and `flint-gguf` (11 of 12
  each), LM Studio `qwen3.8-27b-splash` and `qwen3.8-27b-mlx` (12 of 12 each)
  and `qwen3.6-35b-a3b-mlx` (11 of 12), vLLM-Metal `granite4.2-30b-4bit` (11
  of 12), Ollama `nemotron-3.5-bolt-74b-a9b-q3kxl`, `mimo-v2.6-flash-q2ks` and
  `gemma4-26b-mlx` (12 of 12 each) and `nemotron-3.5-super-mlx` (11 of
  12), and ds4 `qwen3.8-flash-next-q4` and Kapitsa `clover-35b-a3b` (12 of 12
  each).
- On Ollama 0.40.16 `muse-glimmer-30b-mlx` (10 of 12, two invented findings)
  and `nanbeige4.3-33b-q4km` (9 of 12, two runaways and an incomplete
  answer) fail audit fitness on this draw, after 11 and 12 of 12 on 0.40.13
  and 0.40.8; both sit near the limit.
- Ollama `nemotron-3.5-lightning-30b-mlx` fails and serves interactive use.
  On 2026-11-15 it passed audit fitness 11 of 12 but failed the tool loop on
  a typeset hyphen in the status token, which llm-audit-bench now accepts.
  Rerun under that harness from main `6ecbf41` on 2026-11-16, it passed 1 of
  6 runs (fitness 9, 11, 10, 9, 7 and 9 of 12; the row is the last). The
  workflow task's planted admin export goes unreported and the selection
  task invents docs paths. The registry's mxfp8 (MLX) and q8_0 (GGUF,
  f16 KV) builds of the same weights passed 1 of 3 and 0 of 3, so neither
  quantization nor runner is the cause. Evidence:
  `~/.local/state/auditbench/trials/2026-11-16-lightning/`.
- Ollama `gemma4-26b-mlx` passes but serves interactive use, not audits: a
  generic model, and one of its three canonical sessions recalled no
  findings in its report (25.63 sessions/h, unpublishable,
  [ollama/BENCHMARKS.md](ollama/BENCHMARKS.md)). Its schema request runs away
  in structural whitespace on the MLX runner. Gemma 4 31B on the same
  runner passed 12 of 12 but cannot hold 262,144 on the M5, and vLLM-Metal
  `gemma4-31b-4bit` (12 of 12, 1.89 sessions/h) was dropped with it.
- vLLM-Metal `mimo-v2.6-9b-4bit` was dropped on 2026-11-16: it failed both
  tool calls with arguments `{}` and passed 0 of 12 fitness samples on
  0.31.0. Its row is in git history.
- Both LM Studio MLX rows ignore the schema, which no longer fails them
  (advisory since llm-audit-bench 2.3.0), and so does ds4, which has no
  `response_format`. The Ollama MLX runner enforces it on 0.40.6, 0.40.8,
  0.40.13 and 0.40.16 for every profile checked but Gemma 4; 0.32.14 ignored it,
  and an exploratory 0.40.5 Super VL run from an uncommitted tree ran away in
  structural whitespace.
- Ollama `nemotron-3.5-super-mlx` is the M5 route for Nemotron 3.5 Super VL
  (12.79 sessions/h at 524,288, [ollama/BENCHMARKS.md](ollama/BENCHMARKS.md)).
- Three profiles were dropped for faster Splash ones: Ollama
  `flint-40b-a2b-qat-int4-mlx`, which also fails audit fitness on 0.40.13 (10
  of 12, two wrong triage verdicts), and vLLM-Metal
  `ornith1.5-122b-a10b-4bit` (12 of 12) and `ornith1.5-35b-a3b-4bit` (11 of
  12 on 0.31.0, at the fitness limit). Their rows are in git history.
- Splash `ornith1.5-35b-a3b` returns a parseable unaided document that
  violates the schema (`json_only`); the check records it and never gates
  on it.
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

Host: shared A100 test host, reached over ssh through the `HOST` alias supplied
by `.envrc`. Capability Check v2 (`capability-v2`, SCHEMA_VERSION 5),
llm-audit-bench 2.1.0. The vLLM rows ran 2026-10-10/11 from fleet commit
`ad06c70` on vLLM 0.31.0 with Transformers 5.15.1; reports under
`auditbench-trials/2026-10-10-v2-canonical/` on the host. The Ollama and
Strata rows ran 2026-11-15 on Ollama 0.40.16 and Strata 0.2.13
(llm-audit-bench 2.5.0) from the clean trial commit `54822f2` (these pins
with the same profile files); reports under
`auditbench-trials/2026-11-15-a100/`. vLLM
`nanbeige4.3-33b-w4a16` ran 2026-10-26 on llm-audit-bench 2.4.0 (SCHEMA_VERSION
7) from `852441d`, its profile before a rebase, under
`auditbench-trials/2026-10-26-nanbeige-hunt/`. Audit fitness ran 4 samples per
task at each conf's declared sampling and passes with at least 11 of 12 samples
passed.

| Runtime | Profile | Identity | Reasoning | Thinking off | Tool call | Streaming tool call | Tool loop | JSON | Unaided document | Schema enforced | Audit fitness (passed of 12) | Result |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| vLLM | `gemma4-26b-a4b-awq` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 11/12 (failed: missed_findings 1) | pass |
| vLLM | `mimo-v2.6-9b-awq` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | fail 5/12 (failed: invented 2, no_reasoning 3, wrong_verdicts 2) | fail |
| vLLM | `nanbeige4.3-33b-w4a16` | pass | pass | pass | pass | pass | pass | pass | valid | whitespace runaway | pass 11/12 (failed: runaway 1) | pass |
| vLLM | `qwen3.6-35b-a3b-awq` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| vLLM | `qwen3.8-27b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| vLLM | `qwen3.8-27b-512k` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| vLLM | `qwen3.8-27b-dflash2` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| Ollama | `flint-40b-a2b-nvfp4` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 11/12 (failed: leak 1) | pass |
| Ollama | `nemotron-3.5-bolt-74b-a9b-iq2` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| Ollama | `ornith1.5-35b-a3b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 12/12 | pass |
| Strata | `deepseek-v4.1-flash-coder-iq2xxs` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | fail 8/12 (failed: invented 1, no_reasoning 3) | fail |
| Strata | `deepseek-v4.1-flash-q2` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | fail 8/12 (failed: no_reasoning 4) | fail |
| Strata | `qwen3.8-flash-next-nvfp4` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass 11/12 (failed: invented 1) | pass |

Every row's live identity matched the revision or digest pinned in its
model config.

### Findings

- Ten profiles pass: vLLM `qwen3.6-35b-a3b-awq`, `qwen3.8-27b` (now the W4A16
  checkpoint), `qwen3.8-27b-dflash2`, `qwen3.8-27b-512k` (12 of 12 each),
  `gemma4-26b-a4b-awq` and `nanbeige4.3-33b-w4a16` (11 of 12 each), Ollama
  `nemotron-3.5-bolt-74b-a9b-iq2` and `ornith1.5-35b-a3b` (12 of 12 each)
  and `flint-40b-a2b-nvfp4` (11 of 12), and Strata
  `qwen3.8-flash-next-nvfp4` (11 of 12). Ollama
  `qwen3.8-flash-next-gguf-iq4xs` passed 12 of 12 and was dropped on
  2026-11-04: Strata serves the model faster here; its row is in git
  history. Ornith passed 10 and 12 of 12 on 0.40.13.
- Both DeepSeek-V4.1-Flash sets fail on the audit's opening turn: the model
  answers it with a tool call and no thinking at the template's default
  effort, pruned or not, and `reasoning_effort` max only halved it in a
  replay ([strata/BENCHMARKS.md](strata/BENCHMARKS.md)). The Coder also
  invented a finding once. Both serve for interactive use.
- `flint-40b-a2b-nvfp4` (Recursive's CUDA build, every layer on the GPU)
  passes on 0.40.16, 11 of 12 (one leak), after failing twice on 0.40.13,
  10 then 9 of 12, with reasoning preserved as the card requires: wrong
  triage verdicts in both, plus a missed finding and a tool misuse.
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
