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
non-streaming and streaming tool calls, tool round trip, and structured JSON.
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
- Ollama MLX: `qwen3.6-35b-a3b-mlx-nvfp4`,
  `qwen3.6-35b-a3b-coding-mlx-nvfp4`,
  `qwen3.8-27b-mlx-nvfp4`, `muse-glimmer-30b-mlx`,
  `nemotron-3.5-lightning-30b-mlx`
- Ollama MLX on the split 0.33.3 runtime: `qwen3.8-flash-next-mlx-nvfp4`
  (tech demo; audit-unusable on this host, see the conf)
- Ollama GGUF (llama.cpp runner on the 0.34.2 GGUF runtime):
  `qwen3.8-flash-next-gguf`, `qwen3.8-27b`

### RTX PRO 3000 Blackwell

- vLLM: `qwen3.5-4b-awq`, `gemma4-e2b-awq`
- Ollama retained profiles: `qwen3.5-4b`, `gemma4-e2b`, `qwen3.5-9b`,
  `gemma4-12b`, `qwen3.6-35b-a3b`, `qwen3.8-27b`
- Ollama candidate outside the canonical throughput table:
  `muse-glimmer-30b`

### A100-SXM4-80GB

- vLLM: `qwen3-coder-30b`, `glm4.7-flash-awq`,
  `qwen3.6-35b-a3b-awq`, `qwen3.8-27b`, `qwen3.8-27b-dflash2`,
  `gemma4-26b-a4b-awq`, `qwen3.8-27b-512k`
- Ollama: `qwen3-coder-30b`, `glm4.7-flash`, `qwen3.6-35b-a3b`,
  `qwen3.8-27b-native`, `gemma4-26b`, `qwen3.8-flash-next-gguf-iq4xs`
  (needs `OLLAMA_VERSION=0.33.3` on every lifecycle target)

## Apple M5 Max campaign

Host: MacBook Pro `Mac17,6`, Apple M5 Max, 128 GB unified memory, macOS
26.6.2. Initial run date: 2026-08-25; the original inventory re-run in full on
2026-09-06 at protocol SCHEMA_VERSION 4, which moved both tool-call
fixtures to automatic tool choice and added the streamed tool call. Two
rows are dated 2026-09-07: Muse Glimmer, whose 2026-09-06 run refused on
identity drift and whose reviewed replacement digest was checked the next
day, and `qwen3.8-flash-next-mlx-nvfp4`, which owed a record and runs on
the 0.34.2 GGUF runtime rather than the 0.32.14 fleet default.
Splash rows were added on 2026-09-19 with release 1.0 on macOS 27.0;
both were rechecked before the full managed AuditBench campaign and again
on 2026-09-24 on the committed checker. The
vLLM-Metal `qwen3.6-35b-a3b-4bit` and `qwen3.8-27b-4bit` rows are dated
2026-09-20 on plugin 0.29.0, as is the Ollama GGUF `qwen3.8-27b` row
(registry `qwen3.8:27b` on the 0.34.2 GGUF runtime at 262,144). The
vLLM-Metal `granite4.2-30b-4bit`, `ornith1.5-35b-a3b-4bit` and
`gemma4-31b-4bit` rows were rechecked 2026-09-21/22 on plugin 0.29.0
with unchanged verdicts (gemma4's schema check hit the default 600 s
timeout, the same runaway), and the vLLM-Metal
`nemotron-3.5-lightning-30b-4bit` row is dated 2026-09-22, the first
check with the conf's qwen3 dialect parsers declared, as is the
`mimo-v2.6-9b-4bit` row. LM Studio rows are dated 2026-09-24 on
LM Studio 0.4.25+1 with its Splash engine 0.0.5 and mlx-llm 1.11.0. The
managed adapters use the current checker, including schema enforcement.

Every passing row verified live model identity against the config's pinned
revision or digest, streamed reasoning separation, one exact structured tool
call on the non-streaming and the streaming path, a tool-result continuation,
direct JSON, and an honest answer to
schema-constrained decoding: the endpoint enforced the fixture schema or
refused the parameter. The unaided column records, without gating, what the
model produces when the schema is stated in words instead of a grammar.

| Runtime | Profile | Identity | Reasoning | Thinking off | Tool call | Streaming tool call | Tool loop | JSON | Unaided document | Schema enforced | Result |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| Splash | `qwen3.6-35b-a3b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| Splash | `qwen3.8-27b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| LM Studio | `qwen3.6-35b-a3b-splash` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| LM Studio | `qwen3.8-27b-splash` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| LM Studio | `qwen3.6-35b-a3b-mlx` | pass | pass | unsupported | pass | pass | pass | pass | valid | ignored | fail |
| LM Studio | `qwen3.8-27b-mlx` | pass | pass | unsupported | pass | pass | pass | pass | valid | ignored | fail |
| vLLM-Metal | `qwen3.6-35b-a3b-4bit` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| vLLM-Metal | `qwen3.8-27b-4bit` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| vLLM-Metal | `granite4.2-30b-4bit` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| vLLM-Metal | `ornith1.5-35b-a3b-4bit` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| vLLM-Metal | `gemma4-31b-4bit` | pass | pass | pass | pass | pass | pass | pass | valid | whitespace_runaway | fail |
| vLLM-Metal | `nemotron-3.5-lightning-30b-4bit` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| vLLM-Metal | `mimo-v2.6-9b-4bit` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| Ollama MLX | `qwen3.6-35b-a3b-mlx-nvfp4` | pass | pass | pass | pass | pass | pass | pass | valid | ignored | fail |
| Ollama MLX | `qwen3.6-35b-a3b-coding-mlx-nvfp4` | pass | pass | pass | pass | pass | pass | pass | valid | ignored | fail |
| Ollama MLX | `qwen3.8-27b-mlx-nvfp4` | pass | pass | pass | pass | pass | pass | pass | valid | ignored | fail |
| Ollama MLX | `muse-glimmer-30b-mlx` | pass | pass | pass | pass | pass | pass | pass | valid | ignored | fail |
| Ollama MLX | `nemotron-3.5-lightning-30b-mlx` | pass | pass | pass | pass | pass | pass | pass | json_only | ignored | fail |
| Ollama GGUF | `qwen3.8-flash-next-gguf` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| Ollama GGUF | `qwen3.8-27b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| Ollama MLX 0.33.3 | `qwen3.8-flash-next-mlx-nvfp4` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |

### Findings

Splash 1.0, 2026-09-24 recheck: both pinned packages passed all eight checks
through the managed uv entry points at 262,144 configured context and
a 64 GiB memory cap. Both produced valid unaided JSON and passed schema
enforcement. Qwen3.8 exercised authenticated HTTP transport in the earlier
integration check; the rechecks used the owned loopback endpoint.
The thinking-disable control is top-level `reasoning_effort: "none"`;
the default remains thinking enabled. These are short API fixtures.
Deep-context capacity is established separately by the retained full
[AuditBench runs](splash/BENCHMARKS.md), not by the capability gate.
Qwen3.6 subsequently failed one of two growing-conversation samples;
that fixture result remains separate from its short API pass.

Reports under `~/.local/state/capability-check/`, from a clean `2bbfce7`
tree on llm-audit-bench `382760d`, checker file SHA-256
`2012b9c4332823033b7c526177bbb8b7a0265623a85d680458267d0c008c3e99`:

```text
20260924T083242.715681+0000_splash_qwen3-6-35b-a3b.json
20260924T083202.997136+0000_splash_qwen3-8-27b.json
```

The 2026-09-19 campaign rechecks, with the same verdicts, and the earlier
authenticated Qwen3.8 report
(`20260919T192742.892922+0000_splash_qwen3-8-27b.json`, same directory)
ran on an uncommitted checker snapshot.

LM Studio 0.4.25+1, 2026-09-24: the Splash-engine configs load the native
Splash packages at their pinned revisions and pass all eight checks, with the
same top-level `reasoning_effort: "none"` control. The MLX-engine configs load
the vLLM-Metal checkpoints. Neither `reasoning_effort` nor `enable_thinking`
disables their thinking, so thinking-off is unsupported. The engine accepts
the schema parameter, and the model thinks, then stops with empty content,
so schema enforcement is ignored. Reasoning arrives only in
`reasoning_content`; these rows pass through the checker's alias for it. The
tree and checker are the Splash rows'; reports are under
`~/.local/state/capability-check/`:

```text
20260924T082154.775587+0000_lmstudio_qwen3-6-35b-a3b-splash.json
20260924T082102.420159+0000_lmstudio_qwen3-8-27b-splash.json
20260924T083009.694517+0000_lmstudio_qwen3-6-35b-a3b-mlx.json
20260924T082509.680783+0000_lmstudio_qwen3-8-27b-mlx.json
```

- Every vLLM-Metal and Ollama profile that reached inference passes both
  tool-call checks under automatic tool choice, so the plugin's and both
  Ollama runners' parsers handle this host's tool dialects on the
  streaming and the non-streaming path. No M5 row changed verdict on the
  new check.
- Qwen3.6, Qwen3.8, Gemma 4, Granite 4.2 and Ornith 1.5 correctly separate
  reasoning from final content and honor their configured no-thinking
  controls.
- `granite4.2-30b-4bit` and `ornith1.5-35b-a3b-4bit` (onboarded 2026-09-05,
  first rows here) passed every check at plugin 0.28.0, Granite at its
  declared 131,072 context and Ornith at 262,144. Ornith needs the
  `qwen3_xml` tool parser it inherits with the Qwen3.5-MoE architecture;
  Granite needs `qwen3_coder` rather than the `granite4` parser, which
  targets a dialect this generation no longer emits.
- `muse-glimmer-30b-mlx` first failed the 2026-09-06 refresh before
  inference on true identity drift, the tag's second move: the registry
  served manifest `015fa21845be` against a pin of `ef32a55b4976`. The
  replacement manifest was reviewed on 2026-09-07 -- safetensors,
  mixed-precision NVFP4, architecture muse_glimmer, 131,072 native
  context, the same four declared capabilities, DFlash assistant model
  still packaged -- then checked under one explicit digest override,
  where it passed everything except the host-wide MLX enforcement
  defect. The conf is repinned to that digest. Its weights are ~3 GiB
  smaller than the previous artifact's and residency fell with them, so
  no performance number carries across the move.
- Muse Glimmer runs under its documented `Reasoning strength: low` system
  control. Its vendor documentation grades reasoning and never turns it
  off, so this conf declared no disable mode until 2026-09-07; the
  serving path has one anyway, and Ollama's `think: false` produces
  correct content with an empty reasoning field on this digest. The conf
  now declares it and the row records a real result instead of
  `unsupported`. On the current digest its schema-constrained response
  leaked raw channel markers into content, which the streaming reasoning
  check did not show; the conf records it.
- `qwen3.8-flash-next-mlx-nvfp4` (125B-A6B NVFP4, the MLX sibling of the
  GGUF flash-next profiles) passes all eight checks on the split 0.33.3
  runtime, moved there on 2026-09-07 from its 0.33.1 first-light pin to
  match every other flash-next profile in the fleet. Capability success
  says nothing about servability here: prefill beyond roughly 3k tokens
  still dies in a Metal working-set OOM, so the profile stays a tech demo
  and AuditBench cannot run on it at all.
- Ollama's `qwen3.6:35b-a3b-coding-nvfp4` and `muse-glimmer:30b-mlx`
  tags had both moved once before, in the 2026-08-25 campaign. Those
  replacement manifests were reviewed, tested under explicit digest
  overrides, passed every applicable capability check, and were then
  repinned. Muse Glimmer has now consumed that procedure twice.
- The Muse Glimmer MLX manifests reviewed in both rounds package tensors
  with an assistant-model config. Capability success proves response
  semantics only; it does not prove a DFlash speedup.
- Nemotron 3.5 Lightning (`nemotron-3.5-lightning:30b-a3b-mlx`) passes
  reasoning, thinking off via `think: false`, and both tool paths with no
  parser or prompt accommodation -- unlike the Nemotron Nano `<TOOLCALL>`
  history on CUDA vLLM. No AuditBench numbers exist for it yet.
- The base Qwen3.6 NVFP4 (`qwen3.6:35b-a3b-nvfp4`) passes every check
  except schema enforcement at its reduced 131,072 launch context.
  Capability success says nothing about survivable context depth; the
  supervised depth probes that proved 131,072 on both qwen3.6 NVFP4
  digests are recorded in the model configs and `ollama/BENCHMARKS.md`.
- `qwen3.8-flash-next-gguf` (locally imported artifact, identity by
  digest, split 0.33.3 runtime) passes all eight checks with JSON-schema
  enforcement verified, including the streamed tool call. The bare
  `format: "json"` mode is separately unenforced on this model
  (returns fenced JSON); the conf documents the distinction. Its
  known runtime defect -- HTTP 500 on cap-truncated tool calls --
  still sits outside the capability checks, which never truncate a call
  on either path.
- The Ollama MLX runner on the 0.32.14 fleet pin accepts a JSON schema in
  `format` and returns unconstrained prose: all five rows at that pin fail
  the enforcement gate as `ignored`, while the llama.cpp runner enforces
  the same schema in the same binary. The defect is version-scoped, not a
  property of the MLX runner: `qwen3.8-flash-next-mlx-nvfp4` on the split
  0.33.3 runtime reports `enforced`, and a same-day control run of
  `qwen3.6-35b-a3b-mlx-nvfp4` on 0.33.3 -- identical model, identical
  fixture, only the runtime changed -- flipped from `ignored` to
  `enforced`. The five rows keep the pinned-runtime result they were
  measured at; a runtime bump is the way to change them, and that is a
  pin decision rather than a capability one.
- Every MLX-row model except Nemotron still produces a valid unaided
  document when asked in words, so nothing here blocks structured work
  through prompting alone.
- Gemma4-31b under the vLLM-Metal grammar backend is
  `whitespace_runaway`: the grammar permits structural whitespace and
  the model emits it until the protocol's fixed 16,384-token budget
  ends. Its 26B CUDA sibling fails identically, so this reads as a
  Gemma 4 behavior under adversarial constrained decoding. The model
  decodes slowly enough here that the default 600 s request timeout
  cannot reach a verdict; the recorded row used `CAPABILITY_TIMEOUT=1500`
  with the protocol token budget untouched, and spent 1,045 s on that
  single check.
- Nemotron 3.5 Lightning MLX pairs `ignored` enforcement with an
  `unaided` document that is `json_only`: the combination the protocol
  singles out as unusable for structured work on this host.
- No serving profile was promoted or demoted on this refresh. The
  vLLM-Metal `nemotron-3.5-lightning-30b-4bit` profile passes every
  check on plugin 0.29.0, schema enforcement included in 11.5 s, so the
  whitespace runaway seen on the 2026-09-18 trial venv did not recur on
  the pinned venv.

## A100-SXM4-80GB campaign

Host: shared A100 test host, reached over ssh through the `HOST` alias
supplied by `.envrc`. Protocol SCHEMA_VERSION 4. `qwen3.8-27b` and
`qwen3.8-27b-dflash2` are dated 2026-09-19 on vLLM 0.29.0;
`qwen3.8-27b-native` and `qwen3.8-flash-next-gguf-iq4xs` the same day on
Ollama 0.34.2; every other row is the 2026-09-06/07 run on vLLM 0.28.0 and
Ollama 0.32.14 (`qwen3.8-27b-512k` and `glm4.7-flash-awq` on 2026-09-07,
the latter after its conf gained the thinking-disable control).

| Runtime | Profile | Identity | Reasoning | Thinking off | Tool call | Streaming tool call | Tool loop | JSON | Unaided document | Schema enforced | Result |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| vLLM | `qwen3.6-35b-a3b-awq` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| vLLM | `qwen3.8-27b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| vLLM | `qwen3.8-27b-dflash2` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| vLLM | `glm4.7-flash-awq` | pass | pass | pass | pass | pass | pass | pass | ignored | enforced | pass |
| vLLM | `qwen3-coder-30b` | pass | pass | unsupported | fail | fail | not run | pass | valid | whitespace_runaway | fail |
| vLLM | `gemma4-26b-a4b-awq` | pass | pass | pass | pass | pass | pass | pass | valid | whitespace_runaway | fail |
| vLLM | `qwen3.8-27b-512k` | pass | pass | pass | pass | pass | pass | pass | valid | whitespace_runaway | fail |
| Ollama | `qwen3.6-35b-a3b` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| Ollama | `qwen3.8-27b-native` | pass | pass | pass | pass | pass | pass | pass | valid | enforced | pass |
| Ollama | `qwen3-coder-30b` | pass | pass | unsupported | pass | pass | pass | pass | valid | enforced | pass |
| Ollama | `glm4.7-flash` | pass | pass | pass | pass | pass | pass | pass | ignored | enforced | pass |
| Ollama | `gemma4-26b` | pass | pass | pass | pass | pass | pass | pass | valid | truncated | fail |
| Ollama | `qwen3.8-flash-next-gguf-iq4xs` | pass | pass | pass | pass | pass | pass | pass | error | enforced | pass |

Every passing row's live identity matched the revision or digest pinned in
its model config.

### Findings

- Qwen3 Coder on vLLM fails both tool-call checks under automatic tool
  choice: asked for one `lookup_issue` call, the endpoint returns two.
  The same checkpoint passes both checks on Ollama, so this is the vLLM
  side of the pairing -- the model's own tool syntax through the
  configured parser -- and not the checkpoint. This failure was invisible
  under the pre-SCHEMA_VERSION-4 fixture, which named the tool and let
  guided decoding produce the one call the check wanted. The profile is
  demoted for agent workloads on vLLM until it emits exactly one call;
  its serving throughput numbers are unaffected and its Ollama row
  remains a pass.
- Every other A100 row passes both tool paths, non-streaming and
  streamed, on both runtimes.
- `qwen3.8-flash-next-gguf-iq4xs` passes all eight checks with schema
  enforcement verified, and is the only row in the fleet whose unaided
  document is `error`: that request reproducibly (3/3 across Ollama
  0.33.3 and 0.34.2) kills the model with `CUDA error: an illegal memory
  access was encountered` and an HTTP 500. The grammar-constrained
  document over the same fixture completes in the same session, and the
  M5 Q4_K_XL sibling returns a valid document, so this is the CUDA
  llama.cpp path on the qwen4exp architecture, not the prompt or the
  import. `unaided` never gates, so the row passes -- but the crash is a
  serving risk on unconstrained long generations, recorded in the model
  conf with its retest condition.
- `qwen3.8-27b-512k` came up on its first start with a 748,760-token KV
  pool at max_len 524,288, close to the base profile's measured pool, and
  passed the first seven checks. Its enforcement result is
  `whitespace_runaway`, reproducibly (2/2, 343 s per attempt), where the
  same weights and revision at native context pass `enforced` on the same
  venv. Static YaRN at factor 2.0 is the only difference between the two
  profiles, so schema-constrained decoding is not a property this
  checkpoint keeps across the scaling. The profile still owes the depth
  and quality evidence its conf demands; this record closes only the
  capability item.
- Every vLLM revision pin matched the host's HF cache snapshot before
  any server start, and every identity check passed live -- the CUDA
  pin-verification debt is closed.
- The remote Ollama store needed no manifest recovery this round: every
  tag resolved to its pinned digest on the first pull. Earlier campaigns
  hit stale pre-tag-move digests on `qwen3.6:35b-a3b` and `gemma4:26b`,
  which pulling through the managed server repaired without a repin.
- The same-instant pair probe passed 0/12 against `qwen3.6-35b-a3b-awq`
  at 10x concurrency admission -- the Metal plugin's admission bail has
  no CUDA counterpart, as expected.
- Qwen3 Coder declares no thinking-disable control on either runtime, and
  that is now verified against the checkpoint rather than assumed: its
  chat template defines neither `enable_thinking` nor `reasoning_effort`,
  so there is nothing to disable and the `unsupported` cell is correct.
- GLM 4.7 Flash on vLLM was the opposite case. Its conf declared no
  disable control until 2026-09-07, which cost it the whole gate: with
  reasoning always on, the constrained document ran out of the fixed
  16,384-token budget and enforcement recorded `truncated`. The
  checkpoint's own chat template implements the toggle -- with
  `enable_thinking` false it emits `<|assistant|></think>` -- and its
  Ollama pairing had declared the equivalent all along. Declaring
  `enable-thinking-false` makes thinking off pass and enforcement land
  `enforced` in 18 s instead of failing at 204 s, so the profile now
  passes every check. Its unaided document is `ignored`, matching the
  Ollama pairing: on both runtimes the host carries this model for
  structured work.
- Sweeping the fleet for the harness's new graded `reasoning_effort`
  controls found no profile that needs them. Granite 4.2 and Qwen3.8 are
  the checkpoints whose templates read the kwarg. Granite uses it only to
  set `low_effort = reasoning_effort == "low"`, so it grades verbosity.
  Qwen3.8 grades the thinking instruction with `low`, `medium` or `xhigh`
  (the default) and rejects any other value. Neither can disable thinking
  through it; `enable-thinking-false` remains their control.
  The remaining `unsupported` cells are Qwen3 Coder's, where the model
  genuinely has no control.
- `qwen3.8-27b-dflash2` passes every check with the same weights and
  revision as `qwen3.8-27b` plus the pinned DFlash 2 drafter, so the
  drafter changes no response semantics.
- vLLM's grammar backend permits structural whitespace between JSON
  tokens: Qwen3 Coder and Gemma 4 emit it until the 16,384-token budget
  ends (`whitespace_runaway`). Ollama's llama.cpp grammar bounds it, so
  the same Coder checkpoint passes `enforced` there, and Gemma 4 fails
  as plain `truncated` instead.
- No capability row on this host rests on 0.27.1 evidence, and none on
  pre-SCHEMA_VERSION-4 tool-call evidence.

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
