# Qwen3.8-Flash-Next Investigation and Implementation Handoff

Status date: 2026-08-27 11:09 EEST

## Executive decision

Qwen3.8-Flash-Next is viable on the 128 GiB M5 Max at its native
262,144-token context using the Unsloth `UD-IQ4_XS` GGUF.

The recommended first operating point is:

| Setting | Initial value |
| -- | -- |
| Artifact | `unsloth/Qwen3.8-Flash-Next-GGUF:UD-IQ4_XS` |
| Context | 262,144 tokens |
| Parallel slots | 1 |
| Physical batch | 128 |
| Flash Attention | enabled |
| KV cache | F16 |
| Load mode | `none` / `--no-mmap` |
| GPU layers | all possible |
| Bind address | loopback only |

The decisive evidence is a same-host M5 Max report that ran the larger
103.68 GiB `UD-Q4_K_XL` artifact through the full 262,144-token context with
`--no-mmap`. The smaller 87.25 GiB `UD-IQ4_XS` therefore has substantial
additional margin.

Do not begin by raising the macOS IOGPU wired-memory limit. The shipped GGUF
layout makes mmap unnecessarily wire the n-gram table with the Metal model
buffers. `--no-mmap` avoids that problem without a system-wide kernel setting.

## Naming and release state

The open-weight model is `Qwen3.8-Flash-Next`.

`Qwen3.8-Flash` without `-Next` is the hosted QwenCloud production model. It
adds production features such as a default 1M context and built-in tools. It is
not the open-weight artifact.

The existing Ollama `qwen3.8` model is the unrelated Qwen3.8-27B model.

## Architecture facts relevant to serving

The official checkpoint is a multimodal Qwen4 preview architecture:

- 125B main-model parameters
- 6B parameters active per token
- 51B additional n-gram embedding parameters
- 4B MTP head in the official checkpoint
- 48 language layers
- 36 Gated DeltaNet linear-attention layers
- 12 Qwen Sparse Attention layers
- 512 experts, with 10 routed and 1 shared expert active
- native context of 262,144 tokens
- advertised extension to 1,000,000 tokens with YaRN

The open llama.cpp conversion currently omits the 4B MTP head. The GGUF sizing
below therefore does not include MTP. Standalone n-gram speculation is
available, but it is not equivalent to the trained MTP head.

## Artifact inventory

### Official Hugging Face checkpoints

| Artifact | Revision | Exact weight size |
| -- | -- | --: |
| `Qwen/Qwen3.8-Flash-Next` | `de4b8e4d43b917e7706784d8bb445c9af86a3540` | 360,000 MB / 335.276 GiB |
| `Qwen/Qwen3.8-Flash-Next-FP8` | `970c569adaca6b35532111fd6b27351b2baefe50` | 185,502 MB / 172.762 GiB |

The official FP8 release uses dynamic activations and 128 x 128 weight blocks.
Many modules remain BF16, including embeddings and several linear-attention,
shared-expert, and hyper-connection tensors.

### Selected GGUF

Repository:
`unsloth/Qwen3.8-Flash-Next-GGUF`

Repository revision observed during this investigation:
`824f539b2710e5a9e47af4952cf6578cf5ee8932`

The IQ4_XS files themselves remain at upload commit:
`2c41bd2a0b3f51c503c11f1c7ed2e6bb34036beb`

| File | Bytes | LFS SHA-256 |
| -- | --: | -- |
| `UD-IQ4_XS/...-00001-of-00003.gguf` | 10,946,624 | `5ce89370720f8bf90890f439361282104c1aa1482d4013bb9a50923e758e71a4` |
| `UD-IQ4_XS/...-00002-of-00003.gguf` | 49,835,229,856 | `577a38a2392b40ca2193cea502e1d92f60b8cd370675d308e0ec21885d9daaa7` |
| `UD-IQ4_XS/...-00003-of-00003.gguf` | 43,836,407,744 | `d4634e6d84f0ebb0940be15c90d3790bf6464e3dea3a1cddc567dc0e83ad8833` |
| Total | 93,682,584,224 | 93.683 GB / 87.249 GiB |

### Vision projector

Unsloth added the separate vision projectors in commit
`178b998806b7b406c311a3e6174aa99cf6304eaf`:

| Artifact | Bytes | GiB |
| -- | --: | --: |
| `mmproj-F16.gguf` | 904,004,000 | 0.842 |
| `mmproj-BF16.gguf` | 907,542,944 | 0.845 |

The 87.249 GiB IQ4_XS total does not include either projector. Loading vision
therefore adds about 0.84 GiB of weights plus its runtime buffers. The `-hf`
path can pair the projector automatically, so the launcher must make this
choice explicit rather than allowing an unnoticed memory difference between
text-only and multimodal runs.

## IQ4_XS weight decomposition

The GGUF metadata in the second shard identifies:

```text
per_layer_token_embd.weight
type: IQ4_NL
shape: [160, 320001536]
elements: 51,200,245,760
```

That tensor is the n-gram PLE table:

| Component | Size |
| -- | --: |
| N-gram PLE table | 28.800 GB / 26.822 GiB |
| All remaining weights | 64.882 GB / 60.426 GiB |
| Total IQ4_XS weights | 93.683 GB / 87.249 GiB |

The overall quant is named IQ4_XS, but the PLE table itself is IQ4_NL. It is
deliberately kept at a higher-quality four-bit class across the smaller
Unsloth quants.

## Native-context memory arithmetic

### Main QSA KV cache

Only 12 of the 48 layers use token-addressed attention:

```text
12 layers
x 2 KV heads
x 256 dimensions
x K and V
x 2 bytes for F16
= 24 KiB per token
```

At 262,144 tokens this is exactly 6.000 GiB.

### QSA indexer cache

The current llama.cpp PR creates a second cache for the QSA indexer. It uses
one 128-dimensional key head, but the generic cache implementation also
allocates an unused 256-dimensional V side:

```text
12 layers
x (128 K + 256 V dimensions)
x 2 bytes
x 262,144 tokens
= 2.250 GiB
```

Only the 0.750 GiB K portion is semantically required. Removing the unused V
allocation would save about 1.500 GiB, but that optimization is not present in
the current PR.

### Recurrent state

The 36 Gated DeltaNet layers keep fixed per-sequence state rather than
per-token KV:

| State | Size at one sequence |
| -- | --: |
| DeltaNet and PLE convolution history | about 0.016 GiB |
| DeltaNet recurrent matrix state | about 0.105 GiB |
| Total | about 0.122 GiB |

### Fixed subtotal

| Component | GiB |
| -- | --: |
| IQ4_XS weights | 87.249 |
| Main F16 KV | 6.000 |
| Current QSA indexer cache | 2.250 |
| Recurrent state | 0.122 |
| Subtotal before graph buffers | 95.621 |

### QSA graph buffers

The current graph creates a full
`[context, physical_batch]` F32 QSA bias input for each of the 12 QSA layers.
This makes physical batch size a material memory control:

| Physical batch | QSA persistent inputs |
| --: | --: |
| 64 | 0.785 GiB |
| 128 | 1.535 GiB |
| 256 | 3.035 GiB |
| 512 | 6.035 GiB |

Temporary score, expanded-score, attention-mask, activation, and scheduler
buffers add further memory. Buffer lifetimes are reused, so their sizes cannot
simply be summed, but another 1-4 GiB is a reasonable planning allowance.

The current reserve pass can build without the QSA indexer cache attached. It
therefore reserves for the dense path and grows the compute buffer once QSA
actually runs. A load-only check, decode from an empty context, or a prompt
below the 2,051-token sparse-attention threshold will not reveal the final
buffer size. A proposed fix exists in commit
`1246e34257cfe027c3076e28f82a57e273cb252b`, but it was not in PR head
`6c5afc86a` at the status date.

Theoretical full-residency planning ranges are therefore:

| Physical batch | Expected process range |
| --: | --: |
| 64 | about 98-101 GiB |
| 128 | about 99-102 GiB |
| 256 | about 101-104 GiB |
| 512 | about 104-108 GiB |

These figures explain why a 105 GiB operational target is reasonable, but
actual macOS wired memory depends strongly on mmap layout.

## M5 Max evidence

A public report on the exact 128 GiB M5 Max host class tested the larger
Unsloth `UD-Q4_K_XL` artifact:

- artifact size: 103.68 GiB
- context: 262,144
- short-context decode: 34-36 tokens/s
- decode at 20K depth: about 29 tokens/s
- 20K prompt prefill: about 614 tokens/s
- tool calls parsed correctly
- Flash Attention worked
- full 262,144 context completed with `--no-mmap`

### The shipped mmap layout problem

The PLE tensor shares a GGUF shard mapping with Metal-assigned tensors. Even
when the PLE tensor is assigned to CPU, Metal wires the shared mmap region.

Measured on `UD-Q4_K_XL` at 262,144 context:

| Mode | System wired | Result |
| -- | --: | -- |
| Shipped layout, mmap | 114.4 GiB | Fails above about 196K under stock wired limits |
| Shipped layout, `--no-mmap` | 90.1 GiB | Full 262,144 context works |
| PLE repacked into its own shard, mmap | 90.8 GiB | Full context works at about 35 tokens/s |

The repacked PLE pages remain clean, file-backed, and evictable. That is the
intended SSD-resident behavior.

The current IQ4_XS second shard also interleaves the PLE tensor with
Metal-assigned tensors, so the same layout issue applies.

### Random-access mmap finding

The PR author measured the PLE access pattern as 16 gathers per token of about
170 bytes each. None of 4.75 million consecutive gathers shared a page, so
sequential readahead and eager population are actively wrong for this tensor.

Marking the table as random-access reduced its page-cache footprint from
26.82 GiB to 1.19 GiB at identical perplexity. The tradeoff is slower cold
prefill unless row gathers are batched. This work is not merged and is tracked
by llama.cpp issue 27766.

A separate Metal I/O prototype also demonstrated direct SSD n-gram lookup
without an obvious performance loss, but it changes ggml APIs and is not part
of PR 27742. Neither path replaces the safe `--no-mmap` baseline yet.

### IQ4_XS projection from measured Q4_K_XL

IQ4_XS is 16.43 GiB smaller than Q4_K_XL while retaining the same 26.82 GiB
PLE tensor. Subtracting that model-weight difference from the measured wired
figures gives a useful, but still unverified, projection:

| IQ4_XS mode | Projected wired memory |
| -- | --: |
| Shipped mmap layout | about 98 GiB |
| `--no-mmap` | about 74 GiB wired, with the PLE allocation pageable |

This supports the conclusion that IQ4_XS at 262K should fit comfortably with
`--no-mmap`. Shipped-layout mmap may also fit, but it should be treated as an
experiment rather than the first operating point.

## KV quantization

An early PR revision crashed with Q8_0 and Q4_0 KV. The current branch contains
the Hadamard rotate/unrotate fix and has been tested successfully on CUDA with:

- Q8_0 K and V
- Q8_0 K with F16 V
- F16 K and V

Metal validation has not been reported.

If Q8_0 works on Metal, the cache and recurrent-state total changes from:

| KV choice | Cache and recurrent state | Saving versus F16 |
| -- | --: | --: |
| F16 | 8.372 GiB | - |
| Q8_0 | 4.505 GiB | 3.867 GiB |
| Q4_0 | 2.442 GiB | 5.930 GiB |

Use F16 for the first full-context proof. Q8_0 is the next memory experiment
after capability and deep-context correctness pass. Do not promote Q4_0
without long-context quality evidence.

## Runtime status

### llama.cpp

Required support MERGED upstream on 2026-08-27 (after the status date
above): merge commit `6c84c7d5d8833c6e0df69628f75a0f599797934e`. Pin a
master commit at or after it instead of the PR branch. Original PR
facts retained below for the analysis they ground:

- PR: `ggml-org/llama.cpp#27742`
- head observed at status date: `6c5afc86ae84448ae4d744e357017e2c490ad9c3`
- local full clone: `/Users/tumi/git/unslothai/llama.cpp`
- local working tree was still at older commit
  `035e22731a7fd70b9854b3a2d64ec68e9b1a45d3`
- inspect and explicitly pin the desired commit before building

The current head includes fixes for:

- quantized main KV
- distinct index-cache tensor names
- per-context PLE history and state serialization
- index-cache save/restore and multi-slot cache synchronization
- the graph node budget used by `--fit`
- row-banded conversion of enormous tensors
- additional tensor-parallel split handling

Thirteen commits landed in the strict 12-hour update window ending
2026-08-27 11:32 EEST. Thirty-one new PR comments supplied additional runtime
reports and failure reproductions.

Current unresolved work:

- tensor split still fails on recurrent-state sub-range views
- the QSA reserve pass still grows its compute buffer on first sparse use
- MTP is still omitted

### Ollama

The status changed overnight.

Ollama now has an official library entry:

```text
qwen3.8-flash-next
digest prefix: ae2130e55774
size: 360 GB
context: 256K
inputs: text and image
```

Only the 360 GB tag is currently visible. It does not fit either the 128 GiB
Mac or one A100.

Ollama added Qwen4Exp support through its MLX runner in commit:
`18ea9de0fe9cfef75864f7eb07939689bb46ee90`

That support is included in Ollama v0.33.1. This repository currently pins
Ollama 0.32.14, so its managed runtime predates Qwen3.8-Flash-Next support.

Ollama main can quantize the PLE shards at the requested type, but producing a
local quant from the 360 GB source is not the preferred route while the
ready-made Unsloth GGUF exists. Ollama's bundled llama.cpp pin also does not
yet contain qwen4exp GGUF support, so the current practical Mac path is the
open llama.cpp PR, not Ollama's GGUF runner.

#### Tech demo result (2026-08-28): MLX NVFP4 tag exists but is audit-unusable

The library gained `qwen3.8-flash-next:125b-a6b-nvfp4` (105 GB safetensors
NVFP4, manifest digest `c7b96ffe21af...`, requires 0.33.1; `125b-mlx` is an
alias to the same digest). A supervised demo on the 128 GB M5 Max with a
side-by-side Ollama 0.33.1 runtime and the repo conf
`ollama/models/qwen3.8-flash-next-mlx-nvfp4.conf` measured:

- Loads clean: 97.87 GiB all-GPU in ~25 s against the 107.5 GiB Metal
  working-set limit. `/api/show` reports architecture `qwen4_exp` and
  180.0B parameters -- 125B + 51B PLE + the 4B MTP head, so unlike the
  llama.cpp GGUF this MLX artifact carries the trained MTP head.
- Capability Check v1 passes in full (reasoning separation, think-false,
  structured JSON, tool call, tool round trip) in under 10 s.
- Short decode 47.4 tok/s; shallow prefill 260-300 tok/s.
- Prefill dies in a Metal command-buffer OOM above ~3k prompt tokens:
  2,942 completes, ~4,200 fails, and the ceiling is prompt-scaled, not
  allocation-scaled (identical failure at an 8,192-token allocation).
  The weights leave ~9.6 GiB of Metal headroom and the MLX runner's
  prefill compute exceeds it almost immediately.
- Ollama fails safe: the scheduler detects the runner OOM ("runtime
  OOM detected"), expires the model, and releases memory. No host
  reset. This protection is not a 0.33 feature: it shipped unannounced
  in v0.30.0 (PR #16031 lineage; the `llm/status.go` substring
  classifier catches the Metal `kIOGPUCommandBufferCallbackError`
  panic, and the MLX panic-to-error wiring came with PR #15845) and is
  already in the 0.32.14 fleet pin. No Ollama release note documents
  it. It only fires when Metal throws a catchable working-set error;
  the 2026-08-20 unbounded-KV hard-reset shape is not covered on any
  version.

AuditBench requires a 131,072-token allocation and never ran. The Mac
deep-context path for this checkpoint therefore remains the llama.cpp
IQ4_XS route below, whose pageable PLE keeps ~25 GiB more headroom.

A follow-up supervised experiment raised `iogpu.wired_limit_mb` to
120832 (118 GiB working set, ~10 GB left to the OS). It settled the
question definitively and was reverted the same day:

- 7,442 tokens prefilled at 199 tok/s (both former failure points
  passed), but ~12k consumed the entire extra 10.5 GiB in under 0.5 s
  and drove system pressure from normal straight to critical; the
  memory watchdog killed the process group at 14 MiB free. Without it
  this would have been the third hard reset.
- The prefill compute slope is therefore ~1.5-2 GiB per 1k tokens of
  depth and accelerating: 32k audit depth needs 40-60 GiB of compute
  headroom that a 128 GB host cannot provide beside 97.87 GiB of
  weights.
- Raising the limit also removes the safety property observed at the
  default: the Metal working-set wall no longer fires before system
  RAM exhausts, so failures change shape from catchable Metal OOM to
  host-killing runaway. Do not raise it for this model.

Note the timing irony: llama.cpp merged qwen4exp upstream the day
before (2026-08-27, commit `6c84c7d5d883`), so PR 27742 is no longer a
gate. The IQ4_XS route now pins a llama.cpp master commit instead of a
moving PR branch.

### vLLM

The official vLLM recipe requires the dedicated image:
`vllm/vllm-openai:qwen38-flash-next`.

For the official FP8 checkpoint:

- checkpoint size is 172.762 GiB
- TP2 is the minimum validated deployment on GB300
- TP4 is the recommended GB300 deployment
- TEP8 is recommended on an 8x H200 node
- the 51B PLE table can be offloaded to host RAM on NVIDIA
- at least 51 GB of host RAM plus runtime headroom is required for PLE offload

The current `vllm` environment should not be assumed compatible merely
because upstream vLLM has a dedicated image.

## A100 assessment

### Official precision

Neither official checkpoint fits one 80 GiB A100:

- BF16: 335.276 GiB before KV and runtime
- FP8: 172.762 GiB before KV and runtime

The official vLLM path is multi-GPU.

### GGUF experiment

IQ4_XS with the PLE tensor kept in host RAM is potentially viable on one A100:

| Accelerator-resident item | Approximate size |
| -- | --: |
| Non-PLE weights | 60.426 GiB |
| F16 cache and recurrent state | 8.372 GiB |
| QSA and runtime buffers | several GiB |

This is tight but plausible at F16 KV, and materially easier with Q8_0 KV.
The host must have enough RAM for the 26.822 GiB PLE table and enough PCIe
performance for the row gathers. There is no measured single-A100 result yet.

Do not use the shared A100 merely to validate wiring. If this experiment is
accepted later, use the repository's guarded remote workflow and first confirm
that the GPU is idle.

## Comparison with the existing Qwen3.8-27B profiles

The existing repository profiles serve a dense 27B model. Flash-Next has much
larger stored weights but much lower active compute.

| Property | Qwen3.8-27B | Flash-Next IQ4_XS |
| -- | --: | --: |
| Quantized weights on Metal | about 15.5 GiB | 87.25 GiB |
| Active parameters per token | 27B | 6B |
| Token-addressed cache cost | 64 KiB/token | 24 KiB/token main KV |
| Current additional index cache | none | 9 KiB/token |
| Native context | 262,144 | 262,144 |
| Measured M5 short decode | about 33 tokens/s | 34-36 tokens/s on larger Q4_K_XL |

The direct Metal result is consistent with the architecture's purpose:
Flash-Next pays heavily for storage but not proportionally for per-token
compute. It may therefore deliver dense-model quality at roughly the existing
Qwen3.8-27B decode rate, but it sacrifices the multi-context capacity that
vLLM-Metal has with the 27B model.

No AuditBench result exists yet, so it is not a serving recommendation.

## Recommended implementation handoff

All work in the AI tooling repository must be driven through root Makefile
targets. Do not turn the commands in upstream comments into an unmanaged
server invocation.

The clean integration is a dedicated llama.cpp runtime directory at the
repository root, because neither the current managed Ollama nor current
managed vLLM runtime is the tested GGUF path.

Minimum required lifecycle:

1. Pin and verify the llama.cpp fork commit.
2. Build the Metal runtime through a root Makefile target.
3. Download all three IQ4_XS shards outside the repository and verify their LFS
   SHA-256 values.
4. Start one loopback-only server in a detached, pidfile-owned process group.
5. Report model, KV, index-cache, compute-buffer, wired-memory, footprint, and
   memory-pressure values.
6. Stop by pidfile and verify the process group is empty.

Do not add generic runtime machinery beyond what this one experiment needs.

## Experiment sequence

### Phase 1: safe load proof

Resolve these runtime arguments through the Makefile-driven launcher:

| Argument class | Value |
| -- | -- |
| Model | first IQ4_XS split |
| Context | 262,144 |
| Slots | 1 |
| GPU layers | all |
| Flash Attention | on |
| Load mode | none |
| Physical batch | 128 |
| K cache | F16 |
| V cache | F16 |
| Vision projector | omit for the first text-only memory proof |
| Host | `127.0.0.1` |

Capture the startup lines for:

- CPU and Metal model buffers
- normal KV cache
- indexer cache
- recurrent cache
- compute buffers
- compute buffers again after the first prompt above 2,051 tokens
- total process footprint
- system wired memory
- available memory and memory pressure

### Phase 2: capability gate

Before throughput work, prove:

- default reasoning is separated from final content
- reasoning can be disabled
- structured single tool call
- tool-result continuation
- multi-turn tool loop
- direct JSON output
- no raw tool XML in final content

Use the model's supported reasoning efforts: `low`, `medium`, and `xhigh`.
Then repeat the relevant image-input check with `mmproj-F16.gguf` loaded and
record its separate memory delta.

### Phase 3: depth proof

Use a supervised memory watchdog and advance through:

1. 32K
2. 128K
3. 196K
4. 229K
5. approximately 246K prompt tokens

The final request must complete, not merely load. Keep the host otherwise
quiet. Stop the process group if available memory falls below the agreed
safety floor or memory pressure turns critical.

### Phase 4: operating-point sweep

After the full-context F16 baseline passes:

1. Sweep physical batch 128, 256, then 512.
2. Test Q8_0 KV on Metal and repeat capability plus deep-context checks.
3. Compare `--no-mmap` with the shipped mmap layout.
4. Repack PLE into a dedicated shard only if shipped mmap is worth retaining.
5. Test n-gram speculation separately; do not transfer the reported 2.4x
   copy-edit result to audit workloads.
6. Freeze the best safe operating point and run canonical AuditBench v1.

Primary metric is completed audit calls per hour at 32K, half context, and deep
context. Short decode is diagnostic only.

## Acceptance criteria

The model can enter the serving inventory only if:

- exact artifact and runtime revisions are pinned
- one approximately 246K-token request completes repeatedly
- reasoning, tools, tool continuation, and JSON all pass
- no host reset, compute error, or unreleased process occurs
- the chosen operating point remains below the safe memory-pressure threshold
- AuditBench is canonical and publishable
- the cross-runtime overview is updated from the retained benchmark artifact

## Known risks and open questions

1. PR 27742 is moving quickly and remains unmerged.
2. Quantized KV is fixed and tested on CUDA, not yet proven on Metal.
3. The shipped Unsloth shard layout prevents clean PLE mmap offload on Metal.
4. IQ4_XS full-context wired memory is projected, not directly measured.
5. The current indexer cache wastes about 1.5 GiB on an unused V allocation.
6. The graph reserve pass underestimates QSA compute memory until sparse
   attention first runs.
7. Tensor split remains broken; this does not block the one-device Metal path.
8. MTP is omitted, leaving substantial potential decode performance unused.
9. Ollama's only official tag is currently 360 GB.
10. Ollama 0.33.1 support uses a new MLX implementation whose audit throughput
   and memory ceiling have not been measured.
11. The Qwen Community License 1.0 requires a separate license for commercial
   Model-as-a-Service or AI Work Assistant use.

## Source references

### Primary model sources

- [Qwen3.8-Flash-Next source](https://github.com/QwenLM/Qwen3.8-Flash-Next)
- [Official BF16 checkpoint](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)
- [Official FP8 checkpoint](https://huggingface.co/Qwen/Qwen3.8-Flash-Next-FP8)
- [Qwen Community License 1.0](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/main/LICENSE)
- [Qwen release blog](https://qwen.ai/blog?id=qwen3.8-flash-next)

### Quant and runtime sources

- [Unsloth GGUF repository](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF)
- [Unsloth local inference guide](https://unsloth.ai/docs/models/qwen3.8-next)
- [llama.cpp Qwen4Exp PR](https://github.com/ggml-org/llama.cpp/pull/27742)
- [M5 Max memory report](https://github.com/ggml-org/llama.cpp/pull/27742#issuecomment-5429988128)
- [Quantized-KV fix and CUDA validation](https://github.com/ggml-org/llama.cpp/pull/27742#issuecomment-5427974543)
- [Current-head and random-mmap findings](https://github.com/ggml-org/llama.cpp/pull/27742#issuecomment-5434391556)
- [QSA reserve-pass finding](https://github.com/ggml-org/llama.cpp/pull/27742#issuecomment-5434660738)
- [Per-tensor mmap tracking issue](https://github.com/ggml-org/llama.cpp/issues/27766)
- [Metal I/O SSD prototype](https://github.com/ggml-org/llama.cpp/commit/b591584708a6d4fff43c08cb89809e88b389cb08)
- [DGX Spark reference](https://github.com/ggml-org/llama.cpp/pull/27742#issuecomment-5435281337)
- [Official vLLM recipe](https://recipes.vllm.ai/Qwen/Qwen3.8-Flash-Next)

### Ollama sources

- [Ollama model page](https://ollama.com/library/qwen3.8-flash-next)
- [Ollama model tags](https://ollama.com/library/qwen3.8-flash-next/tags)
- Local source clone:
  `/Users/tumi/git/ollama/ollama`
- Qwen4Exp MLX support commit:
  `18ea9de0fe9cfef75864f7eb07939689bb46ee90`

### Existing local comparison data

- `../vllm/BENCHMARKS.md`
- `../vllm-metal/BENCHMARKS.md`
- `../ollama/BENCHMARKS.md`
