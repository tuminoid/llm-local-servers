# vllm/

vLLM OpenAI-compatible server. User-facing usage and the full host-tuning
rationale live in [README.md](README.md); this file covers the file
inventory, the invariants a change must not break, and the traps that
already cost time.

Tree conventions are in [AGENTS.md](../AGENTS.md).

## File inventory

| File | Role | Notes |
| -- | -- | -- |
| `lib.sh` | Shared paths and helpers | Sourced, never executed. Owns state dir, pidfile, log paths, `vllm_pid`, `vllm_gpu_mib`, `vllm_gpu_total_mib`, `vllm_compute_cap`, `vllm_bin`, `vllm_list_models` |
| `start.sh` | Foreground launcher | Reads `models/<name>.conf`, derives all host settings, records pid, `exec`s the resolved vllm |
| `run.sh` | Detached launcher | `setsid` + readiness wait, parses the log for success or failure |
| `stop.sh` | Shutdown | Pidfile-targeted, escalates to SIGKILL, verifies VRAM released, removes the log on a clean stop |
| `status.sh` | Introspection | Process, GPU, pinned model revision, backend, KV sizing, plus a live `/v1/models` probe |
| `bench.py` | Benchmark | CUDA adapter for shared AuditBench v2; records model identity, exact configs, and the resolved host profile |
| `capability.py` | Capability gate | OpenAI-compatible adapter for shared Capability Check v2 |
| `mimo-v2.6-chat-template.jinja` | Chat template | Loaded when the MiMo config sets `VLLM_CHAT_TEMPLATE`. The checkpoint's template with the thinking opener prefilled; the config records why |
| `models/*.conf` | Per-model settings | Portable model facts, including an immutable HF revision; all `${VAR:-default}` so env wins |
| `Makefile` | Guard, defines no targets | Fails with the root target list. Present only to disable Make's built-in `%: %.sh` rule, which turns `make stop` here into an executable copy of `stop.sh` |

## Host adaptation

The launcher derives every hardware-dependent setting at start, so one copy of
these scripts serves both a 12 GB laptop GPU and an 80 GB A100 with no edits
and no per-host branch. Verified on both.

What is derived, and from what:

| Setting | Derived from |
| -- | -- |
| KV dtype | model preference, downgraded below sm_89 |
| Attention backend | effective KV dtype, compute capability, `nvcc` presence |
| FlashInfer sampler | compute capability |
| Utilization, max-num-seqs, max-num-batched-tokens | total VRAM (24 GiB split) |
| Allocator config | host profile |
| vllm executable | `VLLM_BIN`, then `venv/bin/vllm`, then PATH |

The one model fact that reaches into that derivation is `VLLM_ATTN_AUTO`.
Some models accept only backends the launcher would not guess, so their config
sets it and the launcher names no backend at all rather than picking from the
dense list. That is still host-adaptive -- it defers to vLLM's own
capability-aware priority list, which is the portable choice on every host. It
is not a backend value in a model config. `VLLM_MLA` implies it, and
additionally caps utilization.

A model config must therefore stay portable: repo id, immutable revision,
served name, native context length, KV preference, parsers. Putting a
utilization or backend value in one is a bug -- it will be wrong on the next
host. Env overrides still win over both layers, which is the escape hatch for
one-off experiments.

Every `VLLM_MODEL` has a required 40-character `VLLM_MODEL_REVISION`. The
launcher passes it through `--revision`, and AuditBench records it. Never
replace a reviewed commit with a branch or tag: a fresh host must load the
same config, tokenizer, and weights as the measured host. If a historical
artifact's commit cannot be established, pin the current reviewed commit and
rerun rather than assigning it retroactively to an old result.

The current pins establish reproducibility for future starts. They are not
retroactive provenance for existing `BENCHMARKS.md` rows until the historical
A100 or RTX cache snapshot has been matched to the same revision.

The two hardware gates and the allocator interaction are explained with their
measured error messages in [README.md](README.md) (Host tuning notes). The
short version, because each one aborts startup if reintroduced:

- fp8 KV requires sm_89+; both usable backends refuse it on sm_80.
- Some models must not be given an attention backend at all, and a model
  config says so with `VLLM_ATTN_AUTO=1` (`VLLM_MLA=1` implies it). vLLM
  *raises* on an explicitly selected backend where it would skip one it chose
  itself, so a wrong guess aborts engine init instead of falling back. Two
  distinct causes were measured here: MLA models take a disjoint backend
  family (`Reason: ['MLA not supported']`), and multimodal models using
  PrefixLM bidirectional attention need a backend implementing `mm_prefix`
  (`Reason: ['partial multimodal token full attention not supported', ...]`).
  The legal set depends on model architecture as well as host capability,
  which is precisely what the launcher declines to infer.
- FlashInfer requires sm_89+ even with a working `nvcc`; its kernels do not
  compile for arch 80, and its sampler is a separate JIT path with the same
  failure, hence `VLLM_USE_FLASHINFER_SAMPLER=0` below sm_89.
- `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` belongs to the small-card
  profile only. At 0.98 utilization it OOMs in `_allocate_kv_cache_tensors`
  *after* profiling succeeded. The OOM message recommends the flag, which is
  how it originally got set globally -- do not take that advice at face value.
- A venv install needs its `bin` on PATH, not just its `vllm` path: kernel JIT
  shells out to `ninja` and otherwise dies with `FileNotFoundError: 'ninja'`.

## Invariants

### The memory constraint chain

These four are one decision, not four. Changing any link breaks the
others, so change them together and re-measure:

```text
context length -> KV cache dtype -> attention backend -> toolkit requirement
```

For `qwen3.5-4b-awq` on the 12 GB RTX (served there until 2026-10-12), the
native 256k context at the verified
0.92 utilization requires fp8 KV: bf16 needs 8.0 GiB, while fp8 needs
4.06 GiB. fp8 KV eliminates FlashAttention on sm_120; that leaves FlashInfer,
which JIT-compiles and needs `nvcc`, or Triton, which does not.

Consequence for edits: dropping `VLLM_KV_DTYPE` silently makes the server
refuse to start, because vLLM requires the KV cache to hold one whole
`max-model-len` sequence. It does not degrade gracefully to a shorter
context.

Every model conf also pins `VLLM_PREFIX_CACHING` explicitly (regular
attention `1`, hybrid GDN/Mamba `0`), matching the 0.27.1 engine default
the operating points were first gated under; the pins carried unchanged
through the 0.28.0 re-baseline. The pin exists because vLLM
main resolves supported hybrids to align-mode APC ON, so an unset knob
would silently flip those models on a core bump -- changing temp-0
outputs from the first generated token and shrinking the engine-sized KV
pool. The environment still wins over the conf; the qwen3.8 extended
profiles inherit the base conf's pin.

### Serving is text only

`start.sh` always passes `--language-model-only`. Multimodal checkpoints
(the Qwen3.5 family, Gemma 4) serve text, reasoning and tools only: image
and video requests are rejected, the checkpoint's image processor is never
built, and the vision tower is not loaded. Text-only architectures ignore
the flag.

### The runtime pin is enforced at start

`start.sh` refuses to launch when the resolved vllm's installed version
differs from `VLLM_VERSION`, which the `vllm-start` and `vllm-remote-start`
recipes pass from the Makefile pin. Start never installs: a venv moves only
through `vllm-remote-bootstrap` (or a local reinstall), so a pin bump is
incomplete until every host's venv has been re-bootstrapped, and the guard
is what makes a forgotten host fail loudly instead of serving a retired
release under the documented rates. `bench.py` applies the same check to
the live engine.

### Budget is footprint

vLLM preallocates the KV cache as a single tensor sized to fill whatever
`--gpu-memory-utilization` allows. It never grows on demand, so the budget
*is* the memory footprint. Bound memory with that flag.

Do not reach for `--num-gpu-blocks-override`: the block size here is not
16, so a plausible-looking 8192 blocks requested 16.25 GiB and OOM'd.

MLA models are the exception, and it is not a small one. Their
chunked-prefill context path allocates a workspace **lazily**, on the first
prefill long enough to need chunking, sized for up to 64k tokens -- vLLM's own
comment in `determine_chunked_prefill_workspace_size` puts the up-projected
context in gigabytes. Startup profiling never sees it, so the KV cache is
sized as if that memory were free.

The failure therefore arrives long after a clean start, and it kills the
engine rather than failing the request. Measured on A100 with
`glm4.7-flash-awq` (since dropped) at 0.98, after an ~11k prefill had
already succeeded:

```text
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 342.00 MiB.
GPU 0 has a total capacity of 79.25 GiB of which 237.88 MiB is free.
... vllm.v1.engine.exceptions.EngineDeadError
```

`start.sh` caps utilization at 0.92 when `VLLM_MLA` is set and the caller has
not pinned it. That costs nothing real: the canonical A100 run still held
1,050,624 tokens, 5.18x a full-length sequence, so the memory handed back was
never addressable by any request.

### Do not orphan the server

`start.sh` refuses to start when the pidfile names a live process. The
pidfile is the only handle `stop.sh` has, so overwriting it strands the
running server -- it keeps the GPU while `stop.sh` reads the new pid, finds it
dead, and reports `not running`.

Two ways to hit it, both real:

- starting twice, and
- running `start.sh` with `VLLM_BIN` pointed at a stub to inspect the resolved
  arguments. The pidfile is written just before the `exec`, so a dry run takes
  the handle just as effectively as a real start.

Use a scratch handle for that kind of probing rather than defeating the guard:

```bash
VLLM_PIDFILE=$(mktemp -d)/pid VLLM_BIN=/path/to/stub ./start.sh <conf>
```

If it does happen, recover by writing the real pid back into the pidfile and
running `stop.sh`. Do not reach for `pkill -f`.

### Parsers are explicit, per model

vLLM auto-detects neither the reasoning parser nor the tool-call parser.
There is no default and it does not inspect the chat template. Both are
named in the model config. Omitting them leaves the server working but
with raw `</think>` and `<tool_call>` text in `message.content`.

Out-of-tree parsers additionally name their files with
`VLLM_REASONING_PLUGIN` or `VLLM_TOOL_PLUGIN`. A reasoning plugin must be
passed explicitly even when the same file is already a tool plugin: vLLM's
engine subprocess imports it independently from the API process.

The response field is `message.reasoning`, renamed from
`reasoning_content` in vLLM 0.26. Code reading the old name gets `None`
silently rather than an error.

That rename reaches clients. An opencode provider entry for this server must
use `interleaved.field: reasoning`; the older `reasoning_content` spelling
silently yields no reasoning against vLLM 0.26. Confirm with a streaming
request rather than assuming, since the field appears in the delta objects:

```bash
curl -sN localhost:8000/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.6-35b-a3b-awq","messages":[{"role":"user","content":"hi"}],"stream":true}'
```

### Startup profiling is a memory event

`--max-num-batched-tokens` sizes the startup profiling forward pass, not
just steady-state scheduling. Left at its default, which tracks
`max-model-len`, the logits tensor alone (vocab 100352) exhausts the card
before the KV cache is allocated. Any change here risks an OOM that
appears to come from the KV cache.

### Process handling

`start.sh` writes `$$` before `exec`, so the recorded pid is the server's.
That pidfile is the only supported way to stop it -- see the `pkill -f`
self-kill trap in [AGENTS.md](../AGENTS.md).

`run.sh` must keep `setsid`. Without it a Ctrl-C in the caller's shell
kills the server mid-startup, which presents as "nothing happening" with
a log that stops abruptly.

The log is scoped to one run: `run.sh` truncates it at start and `stop.sh`
removes it on a clean stop, so a stopped server leaves nothing behind and
`make vllm-logs` only works while one is up. Removal is skipped on the two
paths where the log is still evidence -- a teardown that left VRAM held, and a
stop that found nothing running, which is what preserves the log of a failed
startup.

Do not reach for rotation instead. The failure that motivated this was a single
run, so there was no second start to rotate at: an idle server's c10d TCPStore
socket died overnight (it binds a routable LAN address, so a suspend or DHCP
renewal breaks it), after which `ProcessGroupNCCL::HeartbeatMonitor::runLoop`
retried at 1 Hz and printed a seven-frame C++ backtrace each time -- 133,409 of
them, 238 MB, over 37 hours, while the engine still held 9.6 GiB. Note what that
means beyond disk: `vllm_pid` and the GPU both looked healthy, so nothing in
`status.sh` distinguished a wedged engine from a working one.

## Where to change what

| Goal | Edit |
| -- | -- |
| Different context length, dtype, parser, model id, or revision | `models/<name>.conf` |
| Different reasoning/tool capability expectation | `models/<name>.conf` |
| Add a model | New `models/<name>.conf`, then `make vllm-start MODEL=<name>` |
| Bind address, port, attention backend | `start.sh` host settings block, or the matching `VLLM_*` env var |
| State or log location | `lib.sh` |
| Readiness detection or timeout | `run.sh` (`VLLM_READY_TIMEOUT`) |
| Benchmark shape | `bench.py` |
| One-off experiment | Env override, no file edit: `VLLM_MAX_LEN=32768 make vllm-start MODEL=qwen3.6-35b-a3b-awq` |

## Known limits

The per-model memory arithmetic in README.md assumes pure attention
layers. Two cases it does not cover:

- **Hybrid mamba models** store recurrent state per sequence rather than
  per token, so the formula is wrong rather than imprecise.
  Nemotron Nano 9B v2 (served on the RTX until 2026-10-12) billed about
  135 MiB per sequence inside the KV pool; measure the recurrent-state
  footprint rather than use the pure-attention formula.
- **Quantized checkpoints** (AWQ, GPTQ, compressed-tensors) change both
  weight size and which attention backends are legal.

There is no auto-detection of model properties from `config.json`. Adding
a model means reading its config and doing the arithmetic. This is a
deliberate omission, not an oversight: the detection is heuristic
(several bundled tool parsers claim the same `<tool_call>` syntax), and a
wrong guess produces a subtly broken server rather than a loud failure.

### Model inventory

Footprints are at each model's native context (capped at 256k), bf16 KV, plus
~2.5 GiB per process. The last column is what matters on a single 80 GB card,
where roughly 76 GiB is allocatable across processes.

These are minimums -- what it takes to hold the weights and one full-length
sequence. They are deliberately not the numbers in the measured baselines
in [BENCHMARKS.md](BENCHMARKS.md), which are larger because vLLM expands the KV
pool to fill whatever `--gpu-memory-utilization` allows. Use this table to
decide what fits; use the baselines to see what a run actually consumed.

| Config | Weights | KV | Total | Two instances | Tools |
| -- | -- | -- | -- | -- | -- |
| `gemma4-26b-a4b-awq` | 15.4 | 10.2 @256k | 28.1 | yes | yes |
| `qwen3.6-35b-a3b-awq` | 23.7 | 5.0 @256k | 31.2 | yes | yes |
| `qwen3.8-27b` | 28.7 | 16.0 @256k | 47.4 | no | yes |

Qwen3.8 serves only its native-context config: the 160k/320k/720k context
profiles were retired as unused variants (measured capacity
ratios and the YaRN overrides remain in git history; see
[README.md](README.md#qwen38-context-profiles)).

Every listed model has an explicit tool path. Agentic work -- vulnerability
discovery and anything else that drives a tool loop -- depends on that path
working in streaming requests, not merely existing in a chat template.

A model whose tool dialect no bundled parser matches gets a parser plugin,
named by its config's `VLLM_TOOL_PLUGIN` (and `VLLM_REASONING_PLUGIN`), not
model-specific syntax in `start.sh`. No current config needs one.

Two instances of the *same* config is rarely the right move: vLLM already
batches continuously, so one engine with the whole KV pool serves more
concurrency than two with half each. The pairs are for running two *different*
models without swapping. Note also that `--gpu-memory-utilization` is a
fraction of total GPU memory, not of free memory, so co-tenancy means halving
it explicitly -- the large-card default of 0.98 will OOM the second engine.

## The A100 test host

The second GPU generation this tree is verified against, and the machine every
host-adaptation change must be exercised on before it is done.

| Fact | Value |
| -- | -- |
| ssh host | the standing `HOST` value supplied by `.envrc`, never committed; override per invocation with `HOST=<ssh-host>` |
| GPU | A100-SXM4-80GB, sm_80, 81920 MiB |
| Scripts | `~/tmp/vllm/`, i.e. the Makefile's default `VLLM_REMOTE_DIR=tmp/vllm` |
| venv | `~/tmp/vllm/venv`, the Makefile's pinned `VLLM_VERSION`, created by `vllm-remote-bootstrap` |
| Runtime state | `~/.local/state/vllm/` on that host, never in the repo |

Rules for working on it, all of them learned the hard way:

- **Drive it with the make targets, never ssh into it and run the scripts by
  hand.** The repo-wide Makefile rule applies across the ssh boundary too.
  The `.envrc` here sets `HOST` to this machine, so a bare remote target lands
  here; override with `HOST=<ssh-host>` for another box.
- **It is a shared, single-GPU machine.** One server can run at a time and
  someone else's may be up. Because the ambient `HOST` points at it, a remote
  target run without thinking targets it -- check `make vllm-remote-status`
  first and stop what is running before starting your own.
- **Deploy is internal plumbing, not a verb.** The targets that execute a
  repo script -- `vllm-remote-start`, `vllm-remote-bench`, and
  `vllm-remote-capability` -- run the internal `vllm-remote-deploy` step as a
  prerequisite, an `rsync --delete` that excludes `venv/` (host-owned,
  gigabytes of CUDA wheels), so they always carry the current scripts; a
  stale remote copy is indistinguishable from a broken change. The read-only,
  teardown and plumbing verbs (`status`, `stop`, `logs`, `tunnel`,
  `bootstrap`) deliberately do not deploy, since a `--delete` sync must not
  be a side effect of inspecting or stopping a server that on a shared host
  may not be yours.
- **Stop by the make target and confirm the GPU reached 0 MiB.** `stop.sh`
  verifies this and exits non-zero if not.

The full cycle (`vllm-remote-start` deploys first, so no explicit sync step):

```bash
make vllm-remote-status HOST=<ssh-host>                  # who is using it
make vllm-remote-stop   HOST=<ssh-host>                  # free the card
make vllm-remote-start  HOST=<ssh-host> MODEL=<conf>   # syncs, then starts
make vllm-remote-status HOST=<ssh-host>                  # backend, KV sizing
make vllm-remote-bench  HOST=<ssh-host> MODEL=<conf>
make vllm-remote-stop   HOST=<ssh-host>                  # must report 0 MiB
```

The server binds loopback on the remote host and has no authentication, so
reaching it from here means `make vllm-remote-tunnel HOST=<ssh-host>`; a
one-off request is easier run over ssh with `curl localhost:8000`.

`VLLM_*` overrides are forwarded across ssh by the `VLLM_ENV` variable in the
root Makefile. ssh passes no environment of its own, so before that existed
every documented override worked locally and silently did nothing remotely --
the server came up on the config defaults while appearing to honour the
request. Only variables the caller set are forwarded, and only ones the
launcher reads, so make-level names such as `MODEL` are excluded.

## Verifying a change

`make lint` is necessary and not sufficient. Run the cycle:

```bash
make lint
make vllm-start  MODEL=<model>       # must reach ready, note GPU MiB and KV tokens
make vllm-status                     # backend, KV sizing, and a live model-name probe
make vllm-capability MODEL=<model>   # reasoning, tools, tool loop, JSON
make vllm-stop                       # must report GPU back to idle
```

Also send one real request and confirm `message.reasoning` is populated
and `message.content` carries no `</think>`.

A change to `lib.sh` or `start.sh` touches host adaptation, so it must be
exercised on more than one GPU generation before it is done. One machine cannot
show that the derivation is right -- it only shows that one branch of it is.
The two generations are the RTX PRO 3000 (sm_120) and the A100 described
above. The RTX carries no vLLM profile since 2026-10-12, so exercising its
branch takes a temporary small conf on that host (the retired
`qwen3.5-4b-awq` in git history is the measured one); `VLLM_VRAM_MIB` can
fake a smaller card on the A100 for the utilization split only. The A100:

```bash
make vllm-remote-start  HOST=<ssh-host> MODEL=<model>   # deploys first
make vllm-remote-status HOST=<ssh-host>
make vllm-remote-stop   HOST=<ssh-host>
```

What proves a host-adaptation change is the resolved profile, not throughput,
so start and status carry the dual-host verification -- benchmarking is not
part of it. Run `make vllm-bench` (or `make vllm-remote-bench`) on-demand: when
a change is meant to affect throughput, or to reproduce a load-only failure a
clean start hides. The MLA workspace OOM above is that case -- it passed every
startup check and only appeared on a ~47k-token prefill -- so benchmark before
trusting a change near that path. You need not benchmark every change, or on
both hosts.

Check the `host:` line the launcher logs at startup, not just that the server
came up. It states the resolved profile, which is what a host-adaptation change
is actually changing:

```text
host: sm_120, 12227 MiB VRAM -> backend FLASHINFER, kv fp8, util 0.916, seqs 2, batched 2048
host: sm_80, 81920 MiB VRAM -> backend FLASH_ATTN, kv auto, util 0.98, seqs 8, batched 8192
host: sm_80, 81920 MiB VRAM -> backend vllm-selected (MLA), kv auto, util 0.92, seqs 8, batched 8192
```

The first shows the small-card profile deriving its utilization from
`VLLM_VRAM_RESERVE_MIB` (1024 by default) rather than naming a fraction, so the
figure differs per card: 0.916 here, 0.900 on a 10 GB card. Setting
`VLLM_VRAM_MIB` fakes the detected total, which is the only way to exercise the
profile a given host does not take -- the split is on that number.

The third is an MLA model on the same A100 as the second: no backend named, and
the utilization cap applied. `backend vllm-selected (MLA)` means the launcher
deferred; the backend actually chosen appears in vLLM's own log and in
`status.sh`.

### Measured baselines

The measured throughput, memory and concurrency numbers live in
[BENCHMARKS.md](BENCHMARKS.md); only the A100 has current vLLM rows (the
small-card rows left with the RTX profiles on 2026-10-12). New and replacement
results follow
[AuditBench v2](https://github.com/tuminoid/llm-audit-bench)
and must have
`canonical: true`.

The overview's `GPU KV pool` column copies the raw measured pool size. Do not
replace it with a derived context count or ratio. Keep scheduler admission
(`max-num-seqs`) distinct from KV capacity.

Benchmarking is on demand when a change affects throughput, context, memory, or
admission. Tune with the optional 1-through-8 stream sweep, then publish only a
fresh canonical run. Update [../README.md](../README.md) in the same change and
never derive a missing metric from a retired-harness rate.

## Prerequisites

- `vllm`, resolved by `vllm_bin` in this order: the `VLLM_BIN` override, a
  `venv/` beside the scripts, then PATH. PATH is whatever the host provides,
  typically a uv tool wrapper; the venv is the portable route and is what
  `make vllm-remote-bootstrap` creates. First install pulls
  roughly 10 GB of torch and CUDA wheels.
- `CUDA_HOME` only matters for FlashInfer, which is only selected for fp8 KV on
  sm_89+. It comes from the host environment.
- Gated models need `hf auth login` and acceptance of the model's terms.

### Host provisioning

GPU host provisioning lives outside this repo. What this server requires of
it:

- A CUDA toolkit from NVIDIA's own apt repo, new enough for the target GPU,
  exposed as `/usr/local/cuda` with `CUDA_HOME` set and `$CUDA_HOME/bin` on
  PATH. The toolkit is what unlocks FlashInfer, so a host without it gets
  the Triton fallback and roughly half the prefill throughput. Nothing
  breaks; it is just slower.

Two traps when provisioning a GPU host for this server:

- **Do not install Ubuntu's `nvidia-cuda-toolkit` package.** It is CUDA
  12.0, and sm_120 (Blackwell) needs 12.8 or newer, so that `nvcc` cannot
  emit code for the GPU at all. Use NVIDIA's own repo for exactly this
  reason.
- **A driver upgrade needs a reboot before this server will start.** The
  new userspace libraries load against the still-running old kernel
  module, and `nvidia-smi` fails with `Failed to initialize NVML:
  Driver/library version mismatch`. vLLM then dies at CUDA init. Confirm
  the versions agree (`cat /proc/driver/nvidia/version` against
  `ls /usr/lib/x86_64-linux-gnu/libnvidia-ml.so.*`) before debugging
  anything in this directory.

Do not put the toolkit's `lib64` on `LD_LIBRARY_PATH`: it shadows the
pip-installed CUDA libraries that torch links against.
