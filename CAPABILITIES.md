# Capability Check v1 results

Capability Check v1 is the pass/fail API compatibility gate for models in the
serving inventory. It proves response semantics needed by coding agents;
AuditBench separately measures serving performance and capacity. The protocol
-- fixed checks, model expectations, and the mapping from the retained JSON
report to the tables below -- is defined in
[llm-audit-bench](https://github.com/tuminoid/llm-audit-bench)
(`docs/CAPABILITY.md`); this file holds the fleet's campaign inventory and
retained results.

Capability results never rank model quality or serving performance.

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

A model intended for agent workloads must pass identity, streaming, tool call,
tool round trip, and structured JSON. Its reasoning result must match the
model-config expectation. A throughput result cannot override a capability
failure.

## Host campaign inventory

### Apple M5 Max

- vLLM-Metal: `qwen3.6-35b-a3b-4bit`, `qwen3.8-27b-4bit`,
  `gemma4-31b-4bit`, `qwen3.8-27b-uncensored-4bit`
- Ollama MLX: `qwen3.6-35b-a3b-mlx-nvfp4`,
  `qwen3.6-35b-a3b-coding-mlx-nvfp4`,
  `qwen3.8-27b-mlx-nvfp4`, `muse-glimmer-30b-mlx`,
  `nemotron-3.5-lightning-30b-mlx`
- Ollama GGUF (llama.cpp runner on the split 0.33.3 managed runtime):
  `qwen3.8-flash-next-gguf`

### RTX PRO 3000 Blackwell

- vLLM: `qwen3.5-4b-awq`, `gemma4-e2b-awq`
- Ollama retained profiles: `qwen3.5-4b`, `gemma4-e2b`, `qwen3.5-9b`,
  `gemma4-12b`, `qwen3.6-35b-a3b`, `qwen3.8-27b`
- Ollama candidate outside the canonical throughput table:
  `muse-glimmer-30b`

### A100-SXM4-80GB

- vLLM: `qwen3-coder-30b`, `glm4.7-flash-awq`,
  `qwen3.6-35b-a3b-awq`, `qwen3.8-27b`, `qwen3.8-27b-dflash2`,
  `gemma4-26b-a4b-awq`
- Ollama: `qwen3-coder-30b`, `glm4.7-flash`, `qwen3.6-35b-a3b`,
  `qwen3.8-27b-native`, `gemma4-26b`

## Apple M5 Max campaign

Host: MacBook Pro `Mac17,6`, Apple M5 Max, 128 GB unified memory, macOS
26.6.2. Initial run date: 2026-08-25; every row below re-run in full on
2026-09-05 at protocol SCHEMA_VERSION 3, which added the gating
schema-enforcement check and the recorded unaided-document outcome.

Every passing row verified live model identity against the config's pinned
revision or digest, streamed reasoning separation, one exact structured tool
call, a tool-result continuation, direct JSON, and an honest answer to
schema-constrained decoding: the endpoint enforced the fixture schema or
refused the parameter. The unaided column records, without gating, what the
model produces when the schema is stated in words instead of a grammar.

| Runtime | Profile | Identity | Reasoning | Thinking off | Tool call | Tool loop | JSON | Unaided document | Schema enforced | Result |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| vLLM-Metal | `qwen3.6-35b-a3b-4bit` | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| vLLM-Metal | `qwen3.8-27b-4bit` | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| vLLM-Metal | `gemma4-31b-4bit` | pass | pass | pass | pass | pass | pass | valid | whitespace_runaway | fail |
| Ollama MLX | `qwen3.6-35b-a3b-mlx-nvfp4` | pass | pass | pass | pass | pass | pass | valid | ignored | fail |
| Ollama MLX | `qwen3.6-35b-a3b-coding-mlx-nvfp4` | pass | pass | pass | pass | pass | pass | valid | ignored | fail |
| Ollama MLX | `qwen3.8-27b-mlx-nvfp4` | pass | pass | pass | pass | pass | pass | valid | ignored | fail |
| Ollama MLX | `muse-glimmer-30b-mlx` | pass | pass | unsupported | pass | pass | pass | valid | ignored | fail |
| Ollama MLX | `nemotron-3.5-lightning-30b-mlx` | pass | pass | pass | pass | pass | pass | json_only | ignored | fail |
| Ollama GGUF | `qwen3.8-flash-next-gguf` | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| vLLM-Metal | `qwen3.8-27b-uncensored-4bit` | pass | pass | pass | pass | pass | pass | valid | enforced | pass |

### Findings

- All current Apple MLX and vLLM-Metal serving profiles pass the six
  pre-SCHEMA_VERSION-3 checks; every 2026-09-05 result change is the new
  schema-enforcement gate.
- Qwen3.6, Qwen3.8, and Gemma 4 correctly separate reasoning from final
  content and honor their configured no-thinking controls.
- Muse Glimmer passes under its documented `Reasoning strength: low` system
  control. It has no configured no-thinking mode, so that check is explicitly
  unsupported rather than silently assumed.
- Ollama's `qwen3.6:35b-a3b-coding-nvfp4` and
  `muse-glimmer:30b-mlx` tags had moved since their reviewed identity pins.
  The first checks failed before inference.
  The replacement manifests were reviewed, tested under explicit digest
  overrides, passed every applicable capability check, and were then repinned.
- The current Muse Glimmer MLX manifest packages tensors from the
  `30b-nvfp4-dflash` artifact and includes an assistant-model config.
  Capability success proves response semantics only; it does not prove a
  DFlash speedup.
- Nemotron 3.5 Lightning (`nemotron-3.5-lightning:30b-a3b-mlx`, pulled and
  onboarded after the initial campaign rows) passed every check
  on its first run, including thinking off via `think: false` -- no parser
  or prompt accommodation was needed, unlike the Nemotron Nano `<TOOLCALL>`
  history on CUDA vLLM. No AuditBench numbers exist for it yet.
- The three vLLM-Metal rows were re-run on the new plugin pin
  0.3.0.dev20260826100011 (PR #634 APC decay fix): clean sweeps on all
  three, with qwen3.6 checked at its new serving default of align-mode
  APC on.
- The three vLLM-Metal rows were re-run again on 2026-09-03 at plugin
  0.28.0 (the first stable release, adopted after upstream deleted the
  dev channel): clean sweeps on all three, qwen3.6 again at its
  align-mode APC serving default.
- The base Qwen3.6 NVFP4 (`qwen3.6:35b-a3b-nvfp4`, checked after
  the initial campaign rows) passed every check at its reduced 131,072
  launch context. Capability success says nothing about survivable context
  depth; the same-day supervised depth probes that proved 131,072 on both
  qwen3.6 NVFP4 digests are recorded in the model configs and
  `ollama/BENCHMARKS.md`.
- `qwen3.8-flash-next-gguf` (checked 2026-09-04 on the split 0.33.3
  runtime, locally imported artifact, identity by digest) passed all
  seven checks with JSON-schema enforcement verified. The bare
  `format: "json"` mode is separately unenforced on this model
  (returns fenced JSON); the conf documents the distinction. Its
  known runtime defect -- HTTP 500 on cap-truncated tool calls --
  sits outside the capability checks, which never truncate a call.
- `qwen3.8-27b-uncensored-4bit` (checked 2026-09-05 at plugin 0.28.0
  on its 512k YaRN serving default, identity by pinned HF revision)
  passed all seven checks. Capability proves response semantics only:
  the abliteration behavior of the checkpoint is deliberately not
  assessed by this gate.
- 2026-09-05 full refresh at protocol SCHEMA_VERSION 3: the Ollama MLX
  runner accepts a JSON schema in `format` and returns unconstrained
  prose. All five MLX rows fail the enforcement gate as `ignored`,
  while the llama.cpp runner enforces the same schema in the same
  0.32.14 binary (`qwen3.8-flash-next-gguf` on the split 0.33.3 runtime
  and the entire A100 Ollama side pass `enforced`). This is a runner
  defect, not a model property: every MLX-row model except Nemotron
  still produces a valid unaided document when asked in words.
- Gemma4-31b under the vLLM-Metal grammar backend is
  `whitespace_runaway`: the grammar permits structural whitespace and
  the model emits it until the protocol's fixed 16,384-token budget
  ends. Its 26B CUDA sibling fails identically, so this reads as a
  Gemma 4 behavior under adversarial constrained decoding. The model
  decodes slowly enough here that the default 600 s request timeout
  cannot reach a verdict; the recorded row used `CAPABILITY_TIMEOUT=1500`
  with the protocol token budget untouched.
- Nemotron 3.5 Lightning MLX pairs `ignored` enforcement with an
  `unaided` document that is `json_only`: the combination the protocol
  singles out as unusable for structured work on this host.
- The promotion rule's required checks are unchanged by the new gate;
  the two new columns record which host-model pairs support
  grammar-constrained structured output. No serving profile was demoted
  on this evidence.

## A100-SXM4-80GB campaign

Host: shared A100 test host (`tuomo-ubuntu-gpu`, ssh alias
`xd-ubuntu-gpu`). Initial run date: 2026-08-26, all ten managed
operating points, vLLM 0.27.1 and isolated Ollama 0.32.14. Every row
below re-run in full on 2026-09-05 at protocol SCHEMA_VERSION 3 on the
vLLM 0.28.0 venv and Ollama 0.32.14, retiring the last 0.27.1-era
capability evidence.

| Runtime | Profile | Identity | Reasoning | Thinking off | Tool call | Tool loop | JSON | Unaided document | Schema enforced | Result |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| vLLM | `qwen3.6-35b-a3b-awq` | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| vLLM | `qwen3.8-27b` | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| vLLM | `qwen3.8-27b-dflash2` | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| vLLM | `glm4.7-flash-awq` | pass | pass | unsupported | pass | pass | pass | valid | truncated | fail |
| vLLM | `qwen3-coder-30b` | pass | pass | unsupported | pass | pass | pass | valid | whitespace_runaway | fail |
| vLLM | `gemma4-26b-a4b-awq` | pass | pass | pass | pass | pass | pass | valid | whitespace_runaway | fail |
| Ollama | `qwen3.6-35b-a3b` | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| Ollama | `qwen3.8-27b-native` | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| Ollama | `qwen3-coder-30b` | pass | pass | unsupported | pass | pass | pass | valid | enforced | pass |
| Ollama | `glm4.7-flash` | pass | pass | pass | pass | pass | pass | ignored | enforced | pass |
| Ollama | `gemma4-26b` | pass | pass | pass | pass | pass | pass | valid | truncated | fail |

Every passing row's live identity matched the revision or digest pinned in
its model config.

### Findings

- Every vLLM revision pin matched the host's HF cache snapshot before
  any server start, and every identity check passed live -- the CUDA
  pin-verification debt is closed.
- The remote Ollama store held stale manifests for `qwen3.6:35b-a3b`
  and `gemma4:26b` (pre-tag-move digests). The identity guard failed
  both checks before inference; pulling through the managed server
  landed exactly the reviewed pinned digests, and both then passed.
  No repin was needed: the registry tags still resolve to the pins.
- The same-instant pair probe passed 0/12 against `qwen3.6-35b-a3b-awq`
  at 10x concurrency admission -- the Metal plugin's admission bail has
  no CUDA counterpart, as expected.
- GLM 4.7 Flash and Qwen3 Coder declare no thinking-disable control on
  the vLLM side; Coder also declares none on Ollama. GLM's Ollama
  profile has a documented disable and passed it.
- `qwen3.8-27b-dflash2` (onboarded 2026-08-31 with the vLLM 0.28.0 pin
  bump, after the initial campaign rows) passed every check: same
  weights and revision as `qwen3.8-27b` plus the pinned DFlash 2
  drafter. `qwen3.6-35b-a3b-awq` was re-checked clean the same day on
  the 0.28.0 venv.
- The 2026-09-05 SCHEMA_VERSION 3 refresh re-ran all eleven rows on the
  0.28.0 venv, so no capability row rests on 0.27.1 evidence anymore.
  The six pre-v3 checks stayed clean everywhere; the three failures are
  the new enforcement gate.
- vLLM's grammar backend permits structural whitespace between JSON
  tokens: Qwen3 Coder and Gemma 4 emit it until the 16,384-token budget
  ends (`whitespace_runaway`). Ollama's llama.cpp grammar bounds it, so
  the same Coder checkpoint passes `enforced` there, and Gemma 4 fails
  as plain `truncated` instead.
- GLM 4.7 Flash on vLLM is `truncated`: with no thinking-disable
  control, reasoning crowds the constrained document out of the fixed
  budget. Its Ollama profile runs the check under its documented
  disable mode and passes `enforced` -- while its unaided document is
  `ignored`, so on that pairing the host carries the model for
  structured work.

## Other hosts

| Host | Automated status | Existing evidence |
| -- | -- | -- |
| RTX PRO 3000 Blackwell | Not run in this campaign | Existing benchmark documents contain partial manual parser and tool-call checks |

Manual evidence is not promoted to a Capability Check v1 pass. Run the
matching capability target on each managed operating point when the host
is available; no full AuditBench rerun is required.
