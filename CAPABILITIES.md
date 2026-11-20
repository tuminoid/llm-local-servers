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

Schema enforcement is recorded and never gates: no audit client depends on
constrained decoding yet, and its failures are engine gaps.

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
  `qwen3.8-flash-next-iq3s`, `ornith1.5-35b-a3b`, `bonsai2-27b-pq2`, and
  `flint-gguf` and `ornith1.5-122b` (both fail compatibility)
- LM Studio: `qwen3.6-35b-a3b-splash`, `qwen3.8-27b-splash`,
  `qwen3.6-35b-a3b-mlx`, and `qwen3.8-27b-mlx` (fails compatibility)
- vLLM-Metal: `granite4.2-30b-4bit`
- Ollama MLX: `muse-glimmer-30b-mlx`, `nemotron-3.5-lightning-30b-mlx`,
  `nemotron-3.5-super-mlx`, `gemma4-26b-mlx` (interactive)
- Ollama GGUF: `nemotron-3.5-bolt-74b-a9b-q3kxl`, `nanbeige4.3-33b-q4km`,
  and `mimo-v2.6-flash-q2ks` (fails compatibility)
- ds4: `qwen3.8-flash-next-q4`
- Kapitsa: `clover-35b-a3b`

### RTX PRO 3000 Blackwell

- Ollama: `qwen3.6-35b-a3b-reap48`, `saluki-27b`, and `lfm2.5-24b-a2b`
  (fails compatibility)

### A100-SXM4-80GB

- vLLM: `qwen3.6-35b-a3b-awq`, `qwen3.8-27b`, `qwen3.8-27b-dflash2`,
  `gemma4-26b-a4b-awq`, `qwen3.8-27b-512k`, and `mimo-v2.6-9b-awq` and
  `nanbeige4.3-33b-w4a16` (both fail compatibility)
- Ollama: `nemotron-3.5-bolt-74b-a9b-iq2`, `flint-40b-a2b-nvfp4`, and
  `ornith1.5-35b-a3b` (fails compatibility)
- Strata: `qwen3.8-flash-next-nvfp4`, `deepseek-v4.1-flash-coder-iq2xxs`,
  `deepseek-v4.1-flash-q2`

## Apple M5 Max campaign

Host: MacBook Pro `Mac17,6`, Apple M5 Max, 128 GB unified memory, macOS
27.0.1. Capability Check v3 (llm-audit-bench 3.0.0, `365510b`), run
2026-11-19/20 from fleet commit `a21fd8a` on Splash 1.5.0, LM Studio
0.4.25+1 (mlx-llm 1.14.0 for the MLX profiles), vLLM-Metal 0.31.0, Ollama
0.40.16, ds4 `0aaea5a` and Kapitsa 0.2.36; reports under
`~/.local/state/auditbench/trials/2026-11-19-v3-campaign/m5/`. Model
identity shows the first 12 characters of the digest or revision.

| Runtime | Profile | Identity | Reasoning | Thinking off | Tool call | Streaming tool call | Tool loop | JSON | Unaided document | Schema enforced | Clean samples | Compatibility | Audit aptitude | Model identity | Artifact |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| Splash | `bonsai2-27b-pq2` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 35 of 36 (97%); fitness 7 of 8 | passed | +0.64 [+0.30, +0.83]; sound 7 of 7 | `b072e1d3b35a` | `20261119T191858.346786+0000_splash_bonsai2-27b-pq2.json` |
| Splash | `flint-gguf` | passed | passed | untested | supported | supported | supported | supported | valid | enforced (supported) | 6 of 8 (75%); fitness 6 of 8 | failed (fitness_clean, clean_rate) | not scored | `20468edfc38a` | `20261119T162756.796595+0000_splash_flint-gguf.json` |
| Splash | `ornith1.5-122b` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 22 of 29 (76%); fitness 8 of 8 | failed (clean_rate) | not scored | `06a57aba4fba` | `20261120T044622.588519+0000_splash_ornith1-5-122b.json` |
| Splash | `ornith1.5-35b-a3b` | passed | passed | supported | supported | supported | supported | supported | json_only | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | +0.57 [+0.21, +0.79]; sound 7 of 8 | `19504d912fa8` | `20261119T162142.304315+0000_splash_ornith1-5-35b-a3b.json` |
| Splash | `qwen3.6-35b-a3b` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 34 of 36 (94%); fitness 7 of 8 | passed | +0.43 [+0.08, +0.67]; sound 7 of 7 | `38740b847e4c` | `20261119T142240.648293+0000_splash_qwen3-6-35b-a3b.json` |
| Splash | `qwen3.8-27b` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 35 of 36 (97%); fitness 8 of 8 | passed | +0.57 [+0.21, +0.79]; sound 8 of 8 | `10c35caafbb8` | `20261119T183126.227604+0000_splash_qwen3-8-27b.json` |
| Splash | `qwen3.8-flash-next-iq3s` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | +0.79 [+0.44, +0.94]; sound 6 of 8 | `ed59f92082b1` | `20261119T204311.255698+0000_splash_qwen3-8-flash-next-iq3s.json` |
| Splash | `qwen3.8-flash-next-q2` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 34 of 36 (94%); fitness 8 of 8 | passed | +0.57 [+0.20, +0.80]; sound 8 of 8 | `ed59f92082b1` | `20261119T200252.121007+0000_splash_qwen3-8-flash-next-q2.json` |
| LM Studio | `qwen3.6-35b-a3b-mlx` | passed | passed | untested | supported | supported | supported | supported | valid | ignored (broken) | 36 of 36 (100%); fitness 8 of 8 | passed | +0.36 [+0.02, +0.60]; sound 8 of 8 | `38740b847e4c` | `20261120T170233.333159+0000_lmstudio_qwen3-6-35b-a3b-mlx.json` |
| LM Studio | `qwen3.6-35b-a3b-splash` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | +0.36 [+0.02, +0.60]; sound 8 of 8 | `0f4714b2db37` | `20261120T164513.676448+0000_lmstudio_qwen3-6-35b-a3b-splash.json` |
| LM Studio | `qwen3.8-27b-mlx` | passed | passed | untested | supported | supported | supported | supported | valid | ignored (broken) | 24 of 31 (77%); fitness 7 of 8 | failed (clean_rate) | not scored | `10c35caafbb8` | `20261120T185445.662511+0000_lmstudio_qwen3-8-27b-mlx.json` |
| LM Studio | `qwen3.8-27b-splash` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | +0.71 [+0.35, +0.90]; sound 8 of 8 | `9d27070b71f7` | `20261120T172619.590802+0000_lmstudio_qwen3-8-27b-splash.json` |
| vLLM-Metal | `granite4.2-30b-4bit` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | +0.57 [+0.21, +0.79]; sound 8 of 8 | `d3f143b44006` | `20261119T175225.897910+0000_vllm-metal_granite4-2-30b-4bit.json` |
| Ollama | `gemma4-26b-mlx` | passed | passed | supported | supported | supported | supported | supported | valid | whitespace_runaway (broken) | 36 of 36 (100%); fitness 8 of 8 | passed | +0.64 [+0.28, +0.85]; sound 7 of 8 | `f60799545325` | `20261119T145038.089065+0000_ollama_gemma4-26b-mlx.json` |
| Ollama | `mimo-v2.6-flash-q2ks` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 23 of 27 (85%); fitness 7 of 8 | failed (clean_rate) | not scored | `aecb7b7e21a4` | `20261120T042350.276175+0000_ollama_mimo-v2-6-flash-q2ks.json` |
| Ollama | `muse-glimmer-30b-mlx` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | +0.64 [+0.28, +0.84]; sound 8 of 8 | `015fa21845be` | `20261119T154421.554447+0000_ollama_muse-glimmer-30b-mlx.json` |
| Ollama | `nanbeige4.3-33b-q4km` | passed | passed | supported | supported | supported | supported | supported | valid | unsupported (refused) | 35 of 36 (97%); fitness 8 of 8 | passed | +0.43 [+0.06, +0.69]; sound 8 of 8 | `f630b1711fd6` | `20261120T163001.592389+0000_ollama_nanbeige4-3-33b-q4km.json` |
| Ollama | `nemotron-3.5-bolt-74b-a9b-q3kxl` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 35 of 36 (97%); fitness 8 of 8 | passed | +0.36 [-0.01, +0.64]; sound 8 of 8 | `bdeed349c1c2` | `20261120T025423.974659+0000_ollama_nemotron-3-5-bolt-74b-a9b-q3kxl.json` |
| Ollama | `nemotron-3.5-lightning-30b-mlx` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 35 of 36 (97%); fitness 8 of 8 | passed | +0.36 [+0.00, +0.62]; sound 6 of 8 | `d1e17d7dabac` | `20261119T153335.892402+0000_ollama_nemotron-3-5-lightning-30b-mlx.json` |
| Ollama | `nemotron-3.5-super-mlx` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | +0.57 [+0.21, +0.79]; sound 8 of 8 | `aba4cee1e75e` | `20261120T000927.447388+0000_ollama_nemotron-3-5-super-mlx.json` |
| ds4 | `qwen3.8-flash-next-q4` | passed | passed | supported | supported | supported | supported | supported | valid | ignored (broken) | 36 of 36 (100%); fitness 8 of 8 | passed | +0.86 [+0.52, +0.98]; sound 8 of 8 | `d600fe1a43d2` | `20261119T225509.672284+0000_ds4_qwen3-8-flash-next-q4.json` |
| Kapitsa | `clover-35b-a3b` | passed | passed | supported | supported | supported | supported | supported | valid | unsupported (refused) | 34 of 36 (94%); fitness 8 of 8 | passed | +0.36 [+0.00, +0.62]; sound 8 of 8 | `4b0402b65e52` | `20261119T160555.416930+0000_kapitsa_clover-35b-a3b.json` |

Every row's live identity matched the revision or digest pinned in its
model config.

### Findings

- Eighteen of 22 profiles pass. ds4 `qwen3.8-flash-next-q4` (+0.86) and
  Splash `qwen3.8-flash-next-iq3s` (+0.79) score highest; with 28 cases
  the interval spans about +-0.3, so only the ends of the range separate.
- Splash `flint-gguf` fails fitness, 6 of 8 clean: two tool misuses.
- Splash `ornith1.5-122b` fails on clean rate, 22 of 29: seven
  vulnerability answers put analysis prose before a fenced JSON array, and
  sampling stopped after 21 of 28 cases. Its 35B sibling passes 36 of 36.
- LM Studio `qwen3.8-27b-mlx` fails on clean rate, 24 of 31: mlx-llm 1.14.0
  crashed on `[metal::malloc] Resource limit (499000) exceeded` with four
  requests in flight, leaving six cases incomplete. The Splash-engine
  profile of the same model passes 36 of 36.
- Ollama `mimo-v2.6-flash-q2ks` fails on clean rate, 23 of 27 (two format
  failures, two runaways).
- Ollama `nemotron-3.5-lightning-30b-mlx`, `muse-glimmer-30b-mlx` and
  `nanbeige4.3-33b-q4km` and LM Studio `qwen3.6-35b-a3b-splash`, which
  failed v2's judgment-based fitness, pass. Nanbeige took about 10 hours
  on one slot.
- Schema enforcement never gates. It is broken on Ollama `gemma4-26b-mlx`
  (whitespace runaway), ignored by both LM Studio MLX profiles and by ds4,
  which has no `response_format`, and refused by Ollama Nanbeige and
  Kapitsa. Splash `ornith1.5-35b-a3b` returns a parseable unaided document
  that violates the schema (`json_only`).
- ds4's interactive-only models are in
  [ds4/BENCHMARKS.md](ds4/BENCHMARKS.md).

## A100-SXM4-80GB campaign

Host: shared A100 test host, reached over ssh through the `HOST` alias supplied
by `.envrc`. Capability Check v3 (llm-audit-bench 3.0.0, `365510b`), run
2026-11-19/20 from fleet commit `a21fd8a` on vLLM 0.31.0 with Transformers
5.15.1, Ollama 0.40.16 and Strata 0.2.13; reports under
`auditbench-trials/2026-11-19-v3-campaign/` on the host. Model identity
shows the first 12 characters of the digest or revision.

| Runtime | Profile | Identity | Reasoning | Thinking off | Tool call | Streaming tool call | Tool loop | JSON | Unaided document | Schema enforced | Clean samples | Compatibility | Audit aptitude | Model identity | Artifact |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| vLLM | `gemma4-26b-a4b-awq` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | +0.71 [+0.36, +0.89]; sound 8 of 8 | `0ef577a57100` | `20261119T145100.047835+0000_vllm-cuda_gemma4-26b-a4b-awq.json` |
| vLLM | `mimo-v2.6-9b-awq` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 5 of 8 (62%); fitness 5 of 8 | failed (fitness_clean, clean_rate) | not scored | `09a55d0912c0` | `20261119T143611.513989+0000_vllm-cuda_mimo-v2-6-9b-awq.json` |
| vLLM | `nanbeige4.3-33b-w4a16` | passed | passed | supported | supported | supported | supported | supported | valid | whitespace_runaway (broken) | 6 of 8 (75%); fitness 6 of 8 | failed (fitness_clean, clean_rate) | not scored | `1c1666af6d96` | `20261119T205316.035551+0000_vllm-cuda_nanbeige4-3-33b-w4a16.json` |
| vLLM | `qwen3.6-35b-a3b-awq` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | +0.50 [+0.15, +0.73]; sound 8 of 8 | `119886a10723` | `20261119T142313.656730+0000_vllm-cuda_qwen3-6-35b-a3b-awq.json` |
| vLLM | `qwen3.8-27b-512k` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | +0.64 [+0.28, +0.85]; sound 8 of 8 | `017b9c7af6b5` | `20261119T164755.866465+0000_vllm-cuda_qwen3-8-27b-512k.json` |
| vLLM | `qwen3.8-27b-dflash2` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | +0.64 [+0.28, +0.85]; sound 8 of 8 | `017b9c7af6b5` | `20261119T160828.532762+0000_vllm-cuda_qwen3-8-27b-dflash2.json` |
| vLLM | `qwen3.8-27b` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 34 of 36 (94%); fitness 7 of 8 | passed | +0.71 [+0.35, +0.90]; sound 7 of 7 | `1f05c441c4e6` | `20261119T153701.415810+0000_vllm-cuda_qwen3-8-27b.json` |
| Ollama | `flint-40b-a2b-nvfp4` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | +0.29 [-0.08, +0.58]; sound 8 of 8 | `9543f736310d` | `20261119T184514.296753+0000_ollama_flint-40b-a2b-nvfp4.json` |
| Ollama | `nemotron-3.5-bolt-74b-a9b-iq2` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 34 of 36 (94%); fitness 8 of 8 | passed | +0.43 [+0.05, +0.70]; sound 8 of 8 | `d6d3deeca271` | `20261119T201109.714683+0000_ollama_nemotron-3-5-bolt-74b-a9b-iq2.json` |
| Ollama | `ornith1.5-35b-a3b` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 19 of 23 (83%); fitness 8 of 8 | failed (clean_rate) | not scored | `9f3b89b25219` | `20261119T175309.862604+0000_ollama_ornith1-5-35b-a3b.json` |
| Strata | `deepseek-v4.1-flash-coder-iq2xxs` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 35 of 36 (97%); fitness 8 of 8 | passed | +0.86 [+0.52, +0.98]; sound 7 of 8 | `0b1d5da5734d` | `20261120T015850.589411+0000_strata_deepseek-v4-1-flash-coder-iq2xxs.json` |
| Strata | `deepseek-v4.1-flash-q2` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | +0.86 [+0.52, +0.98]; sound 8 of 8 | `cb02422c900d` | `20261120T062422.397959+0000_strata_deepseek-v4-1-flash-q2.json` |
| Strata | `qwen3.8-flash-next-nvfp4` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | +0.86 [+0.52, +0.98]; sound 8 of 8 | `640a1db97446` | `20261119T220514.667979+0000_strata_qwen3-8-flash-next-nvfp4.json` |

Every row's live identity matched the revision or digest pinned in its
model config.

### Findings

- Ten profiles pass. The three Strata profiles score highest, +0.86 each;
  with 28 cases the interval spans about +-0.3, so only the ends of the
  range separate, and `flint-40b-a2b-nvfp4` (+0.29) is the one row whose
  interval includes zero.
- Both DeepSeek-V4.1-Flash sets pass. The opening turn that v2 failed them
  on (a tool call without thinking) is recorded, not gated: 34 of 36
  samples reasoned on each. The Coder leaked once.
- `mimo-v2.6-9b-awq` fails fitness, 5 of 8 clean (three runaways).
- `nanbeige4.3-33b-w4a16` fails fitness, 6 of 8 clean: one workflow turn
  emitted tool arguments that are not JSON and one ran out of turn budget.
  Its selection answers run 33k to 64k tokens. Schema enforcement is
  broken (`whitespace_runaway`), which never gates.
- Ollama `ornith1.5-35b-a3b` fails on clean rate, 19 of 23: four
  vulnerability answers wrapped the JSON array in analysis prose, and
  sampling stopped after 15 of 28 cases. The same model passes on M5
  Splash, so the failure belongs to this engine and model combination.
- `qwen3.8-27b-dflash2` (FP8 target) matches the plain profiles check for
  check, so the drafter changes no response semantics.

## RTX PRO 3000 Blackwell campaign

Host: local laptop, RTX PRO 3000 Blackwell Generation
Laptop GPU, sm_120, 12,227 MiB VRAM, Intel Core Ultra 9 285H, 62 GiB
RAM. Capability Check v3 (llm-audit-bench 3.0.0, `365510b`), run
2026-11-21 from fleet commit `a21fd8a` on Ollama 0.40.6; reports under
`~/.local/state/auditbench/trials/2026-11-21-rtx-v3/` on the host and
copied under the M5 trial's `rtx/`. Model identity shows the first 12
characters of the digest.

| Runtime | Profile | Identity | Reasoning | Thinking off | Tool call | Streaming tool call | Tool loop | JSON | Unaided document | Schema enforced | Clean samples | Compatibility | Audit aptitude | Model identity | Artifact |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| Ollama | `qwen3.6-35b-a3b-reap48` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | +0.07 [-0.14, +0.26]; sound 8 of 8 | `a738d78e39f3` | `20261121T113025.392154+0000_ollama_qwen3-6-35b-a3b-reap48.json` |
| Ollama | `saluki-27b` | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 33 of 36 (92%); fitness 8 of 8 | passed | +0.29 [-0.09, +0.59]; sound 6 of 8 | `4868fcc0efd9` | `20261121T143918.523126+0000_ollama_saluki-27b.json` |
| Ollama | `lfm2.5-24b-a2b` | passed | passed | untested | supported | supported | supported | supported | valid | enforced (supported) | 4 of 8 (50%); fitness 4 of 8 | failed (fitness_clean, clean_rate) | not scored | `d4220f26c6dd` | `20261121T145211.214731+0000_ollama_lfm2-5-24b-a2b.json` |

Every row's live identity matched the digest pinned in its model config.

### Findings

- REAP-48 (+0.07) and Saluki (+0.29) pass; their intervals overlap.
- `lfm2.5-24b-a2b` fails fitness, 4 of 8 clean: three workflow runs wrote
  `audit/findings.json` with literal `\n` escapes, so it is not bare JSON,
  and one selection answer is an object instead of an array. Its card
  documents no thinking control, so thinking-off is untested.

Every other RTX profile was dropped on 2026-10-12; their rows are in git
history.
