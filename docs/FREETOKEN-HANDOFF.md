# FreeToken Investigation and Implementation Handoff

Status date: 2026-08-27

## Executive decision

FreeToken is a credible, technically substantial MoE serving runtime and a
strong candidate for the CUDA side of this repository. Its design is unusually
well aligned with repeated, growing agent conversations: host-resident expert
banks, a GPU LRU expert cache, CPU and GPU miss co-execution, recurrent-state
anchors, and runtime cache resizing.

Do not integrate it yet.

The smallest responsible decision is to keep FreeToken as a release-gated,
A100-first candidate:

| Question | Decision |
| -- | -- |
| Add a managed runtime now | No |
| Primary future host | A100 80 GiB |
| Secondary validation host | RTX 12 GiB |
| Mac path | Unsupported upstream; keep the existing llama.cpp and MLX paths |
| First target model | Qwen3.8-Flash-Next after merged and tagged upstream support |
| Later target | GLM-5.3-Flash after upstream architecture support |
| Promotion metric | AuditBench completed calls/hour at real audit depths |

Four blockers make an implementation premature:

1. Neither Qwen3.8-Flash-Next nor GLM-5.3-Flash is supported by the current
   FreeToken release.
2. Qwen3.8 support exists only in competing open pull requests with materially
   different constraints.
3. GLM-5.3 support is only a feature request.
4. No FreeToken result exists for Capability Check v1 or AuditBench v1 on any
   repository host.

This document records the evidence and the minimum implementation contract for
the point when those gates clear. It does not authorize using an upstream pull
request, fork, or untagged wheel as a managed runtime.

## Investigation scope

The investigation covered:

- the FreeToken source tree and current release;
- the arXiv design and evaluation paper;
- the engine's model loading, expert caching, CPU execution, prefill, cache
  budgeting, checkpoint, and API paths;
- the current Qwen3.8 and GLM-5.3 upstream support state;
- fit against the Mac, A100, and RTX hosts used by this repository; and
- the evidence required to decide whether FreeToken raises audit throughput.

No engine installation, model download, remote host mutation, or performance
run was performed.

## Source state

The source was cloned for inspection at:

```text
~/git/flashml-org/freetoken
```

| Fact | Value |
| -- | -- |
| Repository | `FlashML-org/FreeToken` |
| Inspected commit | `9ef3651309fe4058672f2cc92069238dea06be1b` |
| Default branch | `main` |
| Release | `v0.1.2`, published 2026-08-19 |
| License | Apache-2.0 |
| Runtime | Linux x86_64, NVIDIA CUDA 13, driver r580 or newer |
| Python | 3.10 through 3.13 |
| Current public history | Initial open-source commit 2026-08-11 |

The implementation is not a thin wrapper:

- about 72,000 lines of Python;
- about 25,000 lines of tests across 83 test files;
- custom Triton kernels and C++ extensions;
- model-native implementations for hybrid attention, sparse attention, MoE,
  quantized linears, paged caches, and serving APIs; and
- OpenAI and Anthropic compatible endpoints.

The pinned `flashlib==0.3.0` dependency is not a closed component. It is a
public Apache-2.0 repository under the same GitHub organization and supplies
the Triton LRU slot-cache kernel used by FreeToken.

The maturity evidence is mixed:

- `v0.1.2` has published manylinux wheels and a CUDA 13 kernel-cache wheel.
- The source has broad unit coverage and several real-checkpoint gates.
- The checked-in GitHub workflows build and publish wheels but do not run the
  test suite on pull requests.
- The public history is very young and most of the code arrived in a single
  100,000-line initial release.
- The paper publishes figures and methodology, but no raw CSV, JSON, logs, or
  independently reproduced result set is available.

The repository added `sm_80` to the default prebuilt kernel-cache
architectures in commit `184a4f1` on 2026-08-22, after `v0.1.2`. Source JIT may
serve A100, but the managed baseline must wait for a release whose prebuilt
artifacts include the A100 change.

## How FreeToken runs models larger than VRAM

FreeToken is an MoE offload engine, not a general mechanism for making any
dense model fit.

The runtime divides model state into two classes:

1. Non-routed weights, embeddings, attention state, KV cache, and a selected
   expert cache occupy GPU memory.
2. The complete routed-expert pool occupies host RAM for the lifetime of the
   process.

Decode follows the model router:

- cache hits execute from the GPU expert cache;
- the offload backend copies misses over PCIe into LRU-selected slots;
- the CPU backend evaluates routed experts directly from host RAM; and
- the hybrid backend divides misses between PCIe transfer and CPU execution,
  using a machine-specific bandwidth profile from `ft bench bw`.

Prefill uses a different policy. Long prompts activate most experts across a
layer, so FreeToken streams a complete expert layer through two GPU buffers.
While the GPU evaluates one layer, the next layer transfers over PCIe. This
hides expert computation behind transfer when the link is saturated, but it
does not remove the transfer volume.

The FTW checkpoint format improves startup by writing weights in their final
host-bank layout and loading them with parallel direct I/O. It does not turn
the expert pool into an on-disk decode cache. Serving still requires the
expert banks to fit in host memory.

Runtime cache rebuilding can trade VRAM between the expert cache and KV pools
without reloading the model. The operation is idle-only, resets runtime cache
state, destroys and recaptures CUDA graphs, and must not be treated as a
zero-cost online resize.

## Relevance to the audit workload

The design has three properties worth testing for secaudit-cli:

1. Repeated-prefix and recurrent-state reuse may reduce the cost of resending a
   growing audit conversation.
2. Expert-cache locality may keep long reasoning decode stable as the
   conversation grows.
3. OpenAI and Anthropic compatible serving provides a plausible path to the
   existing Capability Check and AuditBench adapters.

The same design also has risks for this workload:

- AuditBench is prefill-heavy at deep context. Full-layer expert streaming may
  dominate calls/hour even when short decode is fast.
- Semantic anchors are model and tokenizer specific. Their existence in the
  engine does not prove they activate for a selected checkpoint and tool
  dialect.
- The upstream standalone decode benchmark warms the expert cache before the
  measured request and defaults to one stream and 256 generated tokens.
- The paper includes agent contexts up to roughly 65,000 tokens, but it does
  not prove repeated `audit_half` or `audit_deep` completion.
- A large pinned host allocation is hostile to a shared machine even when the
  GPU itself is idle.

The only useful decision metric is therefore completed AuditBench calls/hour,
with capability correctness and context survival as hard gates. Upstream
tokens/second results are feasibility evidence, not a serving recommendation.

## Published evidence

The FreeToken paper reports these author-run results:

| Model and host | Host memory | Reported decode |
| -- | --: | --: |
| Qwen3.6-35B-A3B NVFP4, RTX 4060 Laptop 8 GiB | 32 GiB | 39.3 tok/s |
| Qwen3.6-35B-A3B BF16, RTX 5090 32 GiB | 180 GiB server quota | 77-83 tok/s |
| DeepSeek-V4-Flash 284B-A13B, RTX 5090 32 GiB | 180 GiB server quota | 22-25 tok/s |
| GLM-5.2 753B-A40B, RTX PRO 6000 96 GiB | 512 GiB | 14.9 tok/s |

The paper also lists a real RTX 5090 desktop with 192 GiB RAM. The headline
"gaming desktop" result therefore means a high-memory workstation-class
desktop, not a conventional 32 or 64 GiB gaming machine.

The results are technically plausible:

- DeepSeek-V4 activates 13B of 284B parameters per token.
- The paper measured 52.7 GB/s expert transfer on PCIe 5.0 x16.
- The global LRU reduced decode expert misses relative to static placement.
- Long Qwen prefills became transfer-bound once double buffering hid expert
  computation.

They remain author-reported. No controlled third-party reproduction or raw
result artifact was found.

## Fleet fit

### M5 Max, 128 GiB unified memory

FreeToken does not support Apple Silicon, Metal, or macOS. Its memory model
assumes CUDA device memory plus separately pinned host banks.

Do not add a FreeToken compatibility layer for the Mac. The existing
[QWEN38-FLASH-HANDOFF.md](QWEN38-FLASH-HANDOFF.md) already defines the viable
Qwen3.8 llama.cpp experiment for this host. A Metal port would be a separate
runtime project rather than a FreeToken integration.

### A100-SXM4-80GB

This is the primary FreeToken candidate.

The A100 has enough VRAM for resident weights, KV state, and a materially
larger expert cache than the paper's consumer GPUs. Its `sm_80` architecture
is present on FreeToken `main`. Host bandwidth and the CPU connection still
matter because host-to-device expert transfer remains on the decode path.

There is a host-inventory conflict that must be resolved before any
implementation:

- the current operator statement says the A100 host has 512 GB RAM;
- existing repository benchmark documents record 211 GiB RAM for
  `xd-ubuntu-gpu`.

The live host value is the only acceptable input. At 512 GiB, both
Qwen3.8-Flash-Next FP8 and a future GLM-5.3 path are capacity-plausible. At
211 GiB, Qwen3.8 is possible but tight and GLM-5.3 is not a responsible
candidate.

The host is shared. FreeToken pins or locks expert banks for the process
lifetime, so a GPU-idle check is necessary but insufficient. Start must also
reserve host RAM explicitly and refuse when the required bank footprint would
leave inadequate memory for the OS and other users.

### RTX 12 GiB, 64 GiB host RAM

This machine matches FreeToken's low-memory validation audience, but not for
the two frontier targets.

It is a plausible control host for Qwen3.6-35B-A3B NVFP4: the paper served
that family on an 8 GiB GPU with 32 GiB host RAM. It can exercise the
small-card cache budget, PCIe behavior, and host-adaptive backend choice.

It should not be used for Qwen3.8-Flash-Next or GLM-5.3-Flash:

- 125B at four bits is already about 58 GiB before scales, non-MoE weights,
  embeddings, runtime state, and OS headroom; and
- FreeToken requires the routed expert banks to be resident, not merely
  addressable through swap.

## Target-model status

### Qwen3.8-Flash-Next

The official open checkpoint is:

- 125B main-model parameters;
- 6B active parameters per token;
- an additional 51B n-gram embedding table;
- a 4B MTP head in the official checkpoint;
- 48 layers, 512 experts, and 10 routed plus one shared expert active; and
- a native 262,144-token context.

Current FreeToken `main` does not register the
`Qwen4ExpForConditionalGeneration` architecture. Two open pull requests attempt
support:

| Pull request | Important evidence | Important limit |
| -- | -- | -- |
| `#226` | Loaded the official FP8 checkpoint on one RTX A6000 48 GiB | Caps serving at 2,048 tokens because sparse QSA is not implemented beyond that point |
| `#232` | Reports 5.791 tok/s and a 16.51% expert-cache miss rate on RTX 3090 | Large unmerged change covering NVFP4, vision, Windows, and full context |

Pull request `#226` reports:

- about 173 GiB of checkpoint weights;
- 113.6 GiB of routed-expert banks in host memory;
- about 48 GiB of mmap-backed PLE tables;
- a 212-second first cold request; and
- a warm 65-token prompt plus 45-token completion in 8.57 seconds.

Pull request `#232` reports:

- native 262,144-token allocation;
- a 131,072-token operating point with 2,048 expert slots; and
- full text and vision serving through the OpenAI-compatible API.

Neither report is merged, reviewed, tagged, or an AuditBench result. Do not
choose between the implementations in this repository. Wait for upstream to
merge a design, publish a release, and state the supported context and
checkpoint formats.

Once that happens, Qwen3.8 is the first frontier target because:

- its host footprint is already bounded well enough for admission checks;
- the A100 has enough VRAM to test a large cache;
- the Mac handoff supplies an independent llama.cpp serving path; and
- its hybrid attention and repeated-prefix behavior directly exercise the
  audit workload's difficult path.

### GLM-5.3-Flash

GLM-5.3-Flash is not a 125B-A6B model. The official checkpoint is 320B-A18B.
Its text configuration includes:

- 45 layers, with three leading dense layers;
- 288 routed experts and eight selected experts per token;
- hybrid KDA linear attention and DeepSeek-style sparse attention;
- manifold-constrained hyper-connections;
- NoPE projections in the sparse-attention path;
- a native 1,048,576-token context; and
- a multimodal wrapper.

FreeToken has an open feature request, issue `#215`, but no implementation
pull request. Existing GLM-5.2 support is not a drop-in base: the new
architecture adds linear-attention state, different sparse selection,
hyper-connections, and NoPE behavior.

Do not make GLM-5.3 the first integration target. Revisit it only after:

1. upstream model support is merged and released;
2. the exact host-bank and resident-weight footprints are published or
   measured;
3. the live A100 host is confirmed to have enough memory with safe headroom;
4. the model's reasoning and tool protocol pass Capability Check v1; and
5. Qwen3.8 or another supported FreeToken model has already validated the
   runtime integration.

## Release gate

Implementation may begin only when all of these are true:

1. A numbered FreeToken release contains `sm_80` prebuilt kernels.
2. The same release contains merged support for the selected model and exact
   checkpoint format.
3. The supported context is adequate for `audit_32k`, `audit_half`, and
   `audit_deep`; a 2,048-token bring-up path does not qualify.
4. Runtime wheels, kernel-cache wheels, source commit, and model revision can
   all be pinned by digest.
5. Live A100 GPU, driver, CUDA toolkit, RAM, swap, and available-memory values
   have been recorded.
6. The required host-bank footprint leaves an explicit operating reserve and
   does not depend on swap.
7. The shared A100 is idle and the operator has approved the large host-memory
   reservation.

## Minimum implementation handoff

When the release gate clears, add a dedicated `freetoken/` runtime.
The first phase is remote-only on the A100. Do not add nonfunctional local
targets on the Mac.

### Required root targets

| Target | Responsibility |
| -- | -- |
| `make freetoken-deploy HOST=` | Sync only repository-owned scripts and configs |
| `make freetoken-remote-bootstrap HOST=` | Install the pinned engine and kernel-cache wheels in an isolated venv |
| `make freetoken-remote-start HOST= MODEL=` | Preflight GPU and host RAM, then start detached |
| `make freetoken-remote-status HOST=` | Report process, API, GPU, host banks, cache geometry, and model identity |
| `make freetoken-remote-logs HOST=` | Follow the active run log |
| `make freetoken-remote-bench HOST= MODEL=` | Run the shared AuditBench adapter |
| `make freetoken-remote-capability HOST= MODEL=` | Run Capability Check v1 |
| `make freetoken-remote-stop HOST=` | Stop by pidfile and verify GPU and pinned memory are released |
| `make freetoken-remote-tunnel HOST=` | Forward the loopback API to a runtime-specific local port |

Do not add checkpoint conversion to the first implementation. Serve the
supported upstream checkpoint directly, measure startup, and add an FTW target
only if startup time is material to the retained operating procedure.

### Runtime isolation

Use an owned remote tree such as:

```text
tmp/freetoken/
```

Keep these outside the repository:

- the virtual environment;
- Hugging Face and ModelScope caches;
- downloaded checkpoints and FTW conversions;
- bandwidth profiles;
- pidfiles, logs, and benchmark JSON; and
- generated kernel caches.

The launcher must name the venv's `ft` executable explicitly. A missing
installation must fail rather than falling back to another `ft` on `PATH`.

The server must bind to remote loopback. Do not expose the API and do not use
`ft launch`: that command can install and reconfigure third-party agent CLIs,
which is outside the server runtime's scope.

Remote mutation and GPU work require:

```text
FREETOKEN_REMOTE_CONFIRM=$(HOST)
```

### Model configuration

Each `freetoken/models/<name>.conf` stores model facts only:

- repository id and immutable revision;
- expected architecture;
- checkpoint format and expected bytes;
- native and served context;
- reasoning and tool parser expectations;
- expected expert-bank bytes;
- minimum safe host-memory reserve; and
- whether the model supports CUDA graphs, prefix reuse, and multimodal input.

GPU selection, ports, cache size, CPU thread count, pin policy, and bandwidth
profile are host decisions derived by the launcher.

### Start preflight

Start must fail before model loading unless all checks pass:

1. no FreeToken pidfile names a live process;
2. no unrelated NVIDIA compute process is active;
3. the configured GPU is the expected device;
4. the installed driver and CUDA runtime satisfy the pinned release;
5. the checkpoint revision and expected files are present;
6. `MemAvailable` exceeds expert banks plus the configured reserve;
7. swap activity is zero or below an explicit safe threshold; and
8. the API and state ports are unused.

The host-memory check is mandatory. GPU-only admission is unsafe for a runtime
that may pin more than 100 GiB.

### Status contract

Status must report:

- process and API liveness;
- exact FreeToken version, source commit, wheel digests, and model revision;
- GPU name, compute capability, VRAM used, and VRAM total;
- host RAM total, available RAM, process RSS, and locked or pinned bank bytes;
- resolved attention and MoE backends;
- CPU thread and affinity policy;
- bandwidth-profile path and measured CPU and PCIe values;
- expert format, total expert-bank bytes, cache slots, and miss statistics;
- KV pages, usable context, active requests, and admission limit; and
- whether CUDA graphs, semantic anchors, and prefix reuse are active.

### Stop contract

Stop must:

1. terminate the recorded process group;
2. verify no child process remains;
3. verify the GPU returned to its pre-start idle range;
4. verify the process no longer holds pinned or locked host pages; and
5. preserve the log only when teardown verification fails.

## Experiment sequence

### Phase 1: supported control

Before a frontier model, validate the runtime with a released model that both
CUDA hosts can fit, preferably the official Qwen3.6-35B-A3B NVFP4 checkpoint.

Run on RTX and A100:

1. bootstrap and start;
2. inspect the resolved offload or hybrid backend;
3. run Capability Check v1;
4. run AuditBench at the admitted stream counts;
5. record cache misses, host bandwidth, PCIe bandwidth, and RAM residency; and
6. stop and verify complete resource release.

This phase proves host adaptation and the managed lifecycle. It does not prove
the frontier target.

### Phase 2: Qwen3.8 on A100

After tagged upstream support:

1. prove a clean load with one request and no model truncation;
2. run Capability Check v1, including streaming tool calls and continuation;
3. run `audit_32k`;
4. run `audit_half`;
5. run `audit_deep`;
6. tune only the expert-cache and KV split needed to maximize completed
   calls/hour;
7. run the canonical 1, 2, 4, and 8 stream sweep only where admission and
   context capacity permit; and
8. stop and prove host and GPU memory release.

Record cold startup separately. Do not include checkpoint load, kernel JIT, or
first-touch PLE page faults in steady-state calls/hour, but retain them as
operational latency.

### Phase 3: GLM-5.3

GLM-5.3 begins only after Phase 2 establishes that FreeToken belongs in the
fleet. Repeat the same capability and AuditBench gates with an independently
verified host-memory budget. Do not infer its footprint from GLM-5.2.

## Required benchmark evidence

A retained result must record:

- FreeToken release and source commit;
- runtime and kernel-cache wheel SHA-256 values;
- model repository, revision, and checkpoint format;
- checkpoint, resident-weight, expert-bank, and PLE bytes;
- GPU cache slots and fraction of the expert pool;
- KV and recurrent-state allocation;
- CPU and PCIe bandwidth profile;
- expert miss, fetch, and CPU-compute rates;
- configured context, measured tokenizer counts, active streams, and
  admission;
- cold TTFT, warm TTFT, prefill throughput, decode throughput, and completed
  calls/hour;
- preemption, queueing, failures, and retries;
- Capability Check v1 result; and
- AuditBench JSON provenance and `publishable` state.

Do not publish a FreeToken rate from its bundled AIME decode script as an
AuditBench result.

## Promotion gate

FreeToken earns a retained serving role only if:

1. reasoning, structured tools, tool-result continuation, and direct JSON pass;
2. repeated deep-context AuditBench calls complete without engine death,
   runaway swap, or host pressure;
3. prefix and state reuse are observed on the actual audit request pattern;
4. completed calls/hour beats the best existing path for the same role;
5. the required host reservation is acceptable on the shared A100;
6. concurrent requests are genuinely overlapped or explicitly capped;
7. every artifact and runtime component is pinned; and
8. stop reliably releases both GPU and host resources.

Reject or retire the path if short decode improves while deep audit
calls/hour regresses.

## Sources

- [FreeToken repository](https://github.com/FlashML-org/FreeToken)
- [FreeToken paper](https://arxiv.org/html/2608.16157)
- [FreeToken v0.1.2 release](https://github.com/FlashML-org/FreeToken/releases/tag/v0.1.2)
- [FreeToken supported models](https://github.com/FlashML-org/FreeToken/blob/main/docs/models.md)
- [FreeToken benchmark scripts](https://github.com/FlashML-org/FreeToken/tree/main/benchmarks)
- [flashlib repository](https://github.com/FlashML-org/flashlib)
- [Qwen3.8 support pull request 226](https://github.com/FlashML-org/FreeToken/pull/226)
- [Qwen3.8 support pull request 232](https://github.com/FlashML-org/FreeToken/pull/232)
- [Qwen3.8 support request 214](https://github.com/FlashML-org/FreeToken/issues/214)
- [GLM-5.3 support request 215](https://github.com/FlashML-org/FreeToken/issues/215)
- [Qwen3.8-Flash-Next FP8 model](https://huggingface.co/Qwen/Qwen3.8-Flash-Next-FP8)
- [GLM-5.3-Flash model](https://huggingface.co/zai-org/GLM-5.3-Flash)
