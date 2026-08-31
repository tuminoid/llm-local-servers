# Capability Check v1 results

Capability Check v1 is the pass/fail API compatibility gate for models in the
serving inventory. It proves response semantics needed by coding agents;
AuditBench separately measures serving performance and capacity. The protocol
-- fixed checks, model expectations, and the mapping from retained JSON to the
tables below -- is defined in
[llm-audit-bench](https://github.com/tuminoid/llm-audit-bench)
(`docs/CAPABILITY.md`); this file holds the fleet's campaign inventory and
retained results.

Capability results never rank model quality or serving performance. Raw JSON
lives under `${XDG_STATE_HOME:-~/.local/state}/capability-check/`.

## Running a campaign

Follow the campaign procedure in the protocol document, driving the servers
with this repository's targets. Use only the profiles listed for that host in
the inventory below; model configs for another host are not an implied
campaign. Update the host row and raw-artifact table mechanically from the
retained JSON per the protocol's mapping; record failures as failures, and
never convert manual evidence into a Capability Check pass.

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
after a failed check. Remote raw JSON remains in that host's capability state
directory; copy or archive it with the campaign evidence before editing this
file.

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
  `gemma4-31b-4bit`
- Ollama MLX: `qwen3.6-35b-a3b-mlx-nvfp4`,
  `qwen3.6-35b-a3b-coding-mlx-nvfp4`,
  `qwen3.8-27b-mlx-nvfp4`, `muse-glimmer-30b-mlx`,
  `nemotron-3.5-lightning-30b-mlx`

### RTX PRO 3000 Blackwell

- vLLM: `qwen3.5-4b-awq`, `gemma4-e2b-awq`
- Ollama retained profiles: `qwen3.5-4b`, `gemma4-e2b`, `qwen3.5-9b`,
  `gemma4-12b`, `qwen3.6-35b-a3b`, `qwen3.8-27b`
- Ollama candidate outside the canonical throughput table:
  `muse-glimmer-30b`

### A100-SXM4-80GB

- vLLM: `qwen3-coder-30b`, `glm4.7-flash-awq`,
  `qwen3.6-35b-a3b-awq`, `qwen3.8-27b`, `gemma4-26b-a4b-awq`
- Ollama: `qwen3-coder-30b`, `glm4.7-flash`, `qwen3.6-35b-a3b`,
  `qwen3.8-27b-native`, `gemma4-26b`

## Apple M5 Max campaign

Host: MacBook Pro `Mac17,6`, Apple M5 Max, 128 GB unified memory, macOS
26.6.2. Run date: 2026-08-25.

Every passing row verified live model identity, streamed reasoning separation,
one exact structured tool call, a tool-result continuation, and direct JSON.

| Runtime | Profile | Identity | Reasoning | Thinking off | Tool call | Tool loop | JSON | Result |
| -- | -- | -- | -- | -- | -- | -- | -- | -- |
| vLLM-Metal | `qwen3.6-35b-a3b-4bit` | pass | pass | pass | pass | pass | pass | pass |
| vLLM-Metal | `qwen3.8-27b-4bit` | pass | pass | pass | pass | pass | pass | pass |
| vLLM-Metal | `gemma4-31b-4bit` | pass | pass | pass | pass | pass | pass | pass |
| Ollama MLX | `qwen3.6-35b-a3b-mlx-nvfp4` | pass | pass | pass | pass | pass | pass | pass |
| Ollama MLX | `qwen3.6-35b-a3b-coding-mlx-nvfp4` | pass | pass | pass | pass | pass | pass | pass |
| Ollama MLX | `qwen3.8-27b-mlx-nvfp4` | pass | pass | pass | pass | pass | pass | pass |
| Ollama MLX | `muse-glimmer-30b-mlx` | pass | pass | unsupported | pass | pass | pass | pass |
| Ollama MLX | `nemotron-3.5-lightning-30b-mlx` | pass | pass | pass | pass | pass | pass | pass |

### Raw artifacts

| Profile | Model identity | Artifact |
| -- | -- | -- |
| `qwen3.6-35b-a3b-4bit` | `38740b847e4c` | `20260826T112421.001093+0000_vllm-metal_qwen3-6-35b-a3b-4bit.json` |
| `qwen3.8-27b-4bit` | `3e6447f082e8` | `20260826T112506.639507+0000_vllm-metal_qwen3-8-27b-4bit.json` |
| `gemma4-31b-4bit` | `696d436c4047` | `20260826T112554.849290+0000_vllm-metal_gemma4-31b-4bit.json` |
| `qwen3.6-35b-a3b-mlx-nvfp4` | `e92a3e94bbca` | `20260826T053921.155624+0000_ollama_qwen3-6-35b-a3b-mlx-nvfp4.json` |
| `qwen3.6-35b-a3b-coding-mlx-nvfp4` | `cd2692a833e6` | `20260825T130616.452898+0000_ollama_qwen3-6-35b-a3b-coding-mlx-nvfp4.json` |
| `qwen3.8-27b-mlx-nvfp4` | `5642e97495e1` | `20260825T130318.772653+0000_ollama_qwen3-8-27b-mlx-nvfp4.json` |
| `muse-glimmer-30b-mlx` | `ef32a55b4976` | `20260825T130632.969138+0000_ollama_muse-glimmer-30b-mlx.json` |
| `nemotron-3.5-lightning-30b-mlx` | `8b1474be6e54` | `20260825T135231.591587+0000_ollama_nemotron-3-5-lightning-30b-mlx.json` |

### Findings

- All current Apple MLX and vLLM-Metal serving profiles pass the automated
  agent API gate.
- Qwen3.6, Qwen3.8, and Gemma 4 correctly separate reasoning from final
  content and honor their configured no-thinking controls.
- Muse Glimmer passes under its documented `Reasoning strength: low` system
  control. It has no configured no-thinking mode, so that check is explicitly
  unsupported rather than silently assumed.
- Ollama's `qwen3.6:35b-a3b-coding-nvfp4` and
  `muse-glimmer:30b-mlx` tags had moved since their reviewed identity pins.
  The first checks failed before inference and retained these artifacts:
  `20260825T130213.427717+0000_ollama_qwen3-6-35b-a3b-coding-mlx-nvfp4.json`
  and
  `20260825T130327.665159+0000_ollama_muse-glimmer-30b-mlx.json`.
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
  APC on. The raw-artifact table lists the re-run artifacts; the
  artifacts from the old pin remain retained on disk.
- The base Qwen3.6 NVFP4 (`qwen3.6:35b-a3b-nvfp4`, checked after
  the initial campaign rows) passed every check at its reduced 131,072
  launch context. Capability success says nothing about survivable context
  depth; the same-day supervised depth probes that proved 131,072 on both
  qwen3.6 NVFP4 digests are recorded in the model configs and
  `ollama/BENCHMARKS.md`.

## A100-SXM4-80GB campaign

Host: shared A100 test host (`tuomo-ubuntu-gpu`, ssh alias
`xd-ubuntu-gpu`). Run date: 2026-08-26, all ten managed operating
points, vLLM 0.27.1 and isolated Ollama 0.32.14.

| Runtime | Profile | Identity | Reasoning | Thinking off | Tool call | Tool loop | JSON | Result |
| -- | -- | -- | -- | -- | -- | -- | -- | -- |
| vLLM | `qwen3.6-35b-a3b-awq` | pass | pass | pass | pass | pass | pass | pass |
| vLLM | `qwen3.8-27b` | pass | pass | pass | pass | pass | pass | pass |
| vLLM | `glm4.7-flash-awq` | pass | pass | unsupported | pass | pass | pass | pass |
| vLLM | `qwen3-coder-30b` | pass | pass | unsupported | pass | pass | pass | pass |
| vLLM | `gemma4-26b-a4b-awq` | pass | pass | pass | pass | pass | pass | pass |
| Ollama | `qwen3.6-35b-a3b` | pass | pass | pass | pass | pass | pass | pass |
| Ollama | `qwen3.8-27b-native` | pass | pass | pass | pass | pass | pass | pass |
| Ollama | `qwen3-coder-30b` | pass | pass | unsupported | pass | pass | pass | pass |
| Ollama | `glm4.7-flash` | pass | pass | pass | pass | pass | pass | pass |
| Ollama | `gemma4-26b` | pass | pass | pass | pass | pass | pass | pass |

### Raw artifacts

Remote originals stay in the host's capability state directory; copies
are archived outside the repository, including the retained
identity-mismatch failures.

| Profile | Model identity | Artifact |
| -- | -- | -- |
| `qwen3.6-35b-a3b-awq` | `119886a10723...` | `20260826T132148.124484+0000_vllm-cuda_qwen3-6-35b-a3b-awq.json` |
| `qwen3.8-27b` | `017b9c7af6b5...` | `20260826T132948.128619+0000_vllm-cuda_qwen3-8-27b.json` |
| `glm4.7-flash-awq` | `88e3d3d913c0...` | `20260826T133223.293698+0000_vllm-cuda_glm4-7-flash-awq.json` |
| `qwen3-coder-30b` | `dcaee4d4dfc5...` | `20260826T133441.448169+0000_vllm-cuda_qwen3-coder-30b.json` |
| `gemma4-26b-a4b-awq` | `0ef577a57100...` | `20260826T133952.289706+0000_vllm-cuda_gemma4-26b-a4b-awq.json` |
| `qwen3.6-35b-a3b` | `096fdbd02fe6` | `20260826T134315.318078+0000_ollama_qwen3-6-35b-a3b.json` |
| `qwen3.8-27b-native` | `22130167c4c2` | `20260826T134408.016509+0000_ollama_qwen3-8-27b-native.json` |
| `qwen3-coder-30b` | `06c1097efce0` | `20260826T134433.462979+0000_ollama_qwen3-coder-30b.json` |
| `glm4.7-flash` | `4475827791a2` | `20260826T134613.736056+0000_ollama_glm4-7-flash.json` |
| `gemma4-26b` | `08ae7ec1744b` | `20260826T134954.726124+0000_ollama_gemma4-26b.json` |

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

## Other hosts

| Host | Automated status | Existing evidence |
| -- | -- | -- |
| RTX PRO 3000 Blackwell | Not run in this campaign | Existing benchmark documents contain partial manual parser and tool-call checks |

Manual evidence is not promoted to a Capability Check v1 pass. Run the
matching capability target on each managed operating point when the host
is available; no full AuditBench rerun is required.
