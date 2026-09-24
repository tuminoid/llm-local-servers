# vllm/

vLLM OpenAI-compatible inference server. Config-driven and host-adaptive: one
file per model under `models/`, with everything hardware-dependent derived at
launch, so the same scripts and configs run unchanged on a 12 GB laptop GPU and
an 80 GB A100.

Serving benchmarks follow
[AuditBench v1](https://github.com/tuminoid/llm-audit-bench).

Everything runs through Makefile targets from the repo root. Model selection is
mandatory -- there is no default, so `MODEL` must name a config in
`models/`:

```bash
make vllm-start MODEL=qwen3.5-4b-awq  # start detached, wait until serving
make vllm-status                      # process, GPU use, KV cache sizing
make vllm-logs                        # follow the server log
make vllm-bench MODEL=qwen3.5-4b-awq  # AuditBench v1
make vllm-stop                        # stop, verify the GPU was released
```

`vllm-status`, `vllm-logs` and `vllm-stop` act on the running server, so they
take no model. `vllm-start` and `vllm-bench` do, and fail fast with the
available list if it is missing.

Any `VLLM_*` variable in a model config can be overridden from the
environment, since each uses `${VAR:-default}`:

```bash
VLLM_MAX_LEN=32768 VLLM_PORT=8002 make vllm-start MODEL=qwen3.5-4b-awq
```

## Qwen3.8 context profiles

Qwen3.8 serves one config at its native 262,144-token context; the measured
A100 pool (46.26 GiB / 749,204 tokens, 2.86x the floor) holds two full-length
jobs while unused capacity still serves additional short requests.

Retired 2026-08-26: the 160k, 320k, and 720k context profiles (native
narrow, YaRN 1.25, YaRN 2.8125) were removed as unused variants. Their
measured A100 capacity ratios (4.56x and 2.29x for 160k/320k; the 720k
one-job budget was never timed) and the full YaRN override JSON live in git
history at this section's last pre-removal revision. Reintroducing an
extended context needs the nested RoPE override plus
`VLLM_ALLOW_LONG_MAX_MODEL_LEN`; changing only `VLLM_MAX_LEN` would extend
the limit without the required scaling.

## Running on another host

The scripts are host-adaptive, so a remote GPU box needs no edited copy. Only
the venv is per-host; it is never synced, since it holds gigabytes of
platform-specific CUDA wheels.

```bash
make vllm-remote-bootstrap HOST=gpu-box   # create venv, install pinned vllm
make vllm-remote-start     HOST=gpu-box MODEL=qwen3-coder-30b  # syncs, then starts
make vllm-remote-status    HOST=gpu-box
make vllm-remote-bench     HOST=gpu-box MODEL=qwen3-coder-30b
make vllm-remote-stop      HOST=gpu-box
```

`vllm-remote-start`, `vllm-remote-bench`, and `vllm-remote-capability` sync
the scripts to the host before executing, so the remote copy is always
current; the read-only and teardown verbs (`status`, `stop`, `logs`,
`tunnel`) do not deploy, so they never mutate the remote tree as a side
effect.

`VLLM_REMOTE_DIR` (default `tmp/vllm`, relative to the remote home) sets where
the scripts land. `VLLM_VERSION` and `VLLM_TRANSFORMERS_VERSION` pin what
bootstrap installs; their defaults are vLLM 0.29.0 and Transformers 5.15.1.

The Transformers pin moves with the vLLM pin. vLLM 0.29.0 requires
Transformers >= 5.10.4; 5.15.1 is kept because 5.15 made Gemma 4's 256/512
head dimensions explicitly per-layer, matched on the vLLM side by
[PR #49797](https://github.com/vllm-project/vllm/pull/49797).

`HOST` comes from the environment (`.envrc`, where it points at the shared
A100 test host), so omitting `HOST=` targets that machine -- the `gpu-box`
above is only a placeholder for another box. Check `make vllm-remote-status`
before starting on the standing host.

`VLLM_*` overrides are forwarded across the ssh boundary, so the escape hatch
works the same remotely as locally:

```bash
make vllm-remote-start HOST=gpu-box MODEL=<conf> VLLM_MAX_LEN=32768
```

The executing verbs sync with `rsync --delete` before running, so an edited
script is always the one that executes and a stale remote copy cannot
masquerade as a broken change. If the host is shared, check
`vllm-remote-status` before starting: one GPU serves one server at a
time, and `start.sh` refuses rather than clobbering a running one.

Both ends bind loopback only and the server has no authentication, so reach it
with a tunnel rather than by rebinding:

```bash
make vllm-remote-tunnel HOST=gpu-box      # localhost:8001 -> the host
```

The local side defaults to 8001 because a local vLLM server already owns 8000;
reusing it makes ssh fail with `bind: Address already in use`. Override with
`VLLM_TUNNEL_PORT`, and `VLLM_REMOTE_PORT` for the far end. The foreground
tunnel fails immediately when forwarding cannot be established and exits
within about 90 seconds when SSH keepalives detect a dead connection. It does
not reconnect automatically.

## Using it from opencode

The generated providers `vllm` (`127.0.0.1:8000`) and `vllm-remote`
(`127.0.0.1:8001`, where `make vllm-remote-tunnel` lands) list every config
here; see [Using the servers from opencode](../README.md#using-the-servers-from-opencode).

```bash
make vllm-start MODEL=qwen3.5-4b-awq
export OPENCODE_CONFIG=/path/to/llm-local-servers/opencode/vllm/opencode.json
opencode run -m vllm/qwen3.5-4b-awq "Summarise the auth flow."

make vllm-remote-start  HOST=gpu-box MODEL=qwen3.8-27b
make vllm-remote-tunnel HOST=gpu-box      # separate shell; holds the tunnel
export OPENCODE_CONFIG=/path/to/llm-local-servers/opencode/vllm-remote/opencode.json
opencode run -m vllm-remote/qwen3.8-27b --variant low "Summarise the auth flow."
```

The model id is the config's `VLLM_SERVED_NAME`, and only the model the
server was started with is live; `/v1/models` lists it. Limits come from
`VLLM_MAX_LEN`.

An entry declares reasoning only where the model populates the field with no
request control, since opencode sends no thinking toggle:
`VLLM_CAP_REASONING=required` with `VLLM_CAP_REASONING_MODE=default`.
`qwen3-coder-30b` is a non-thinking model and returns `reasoning: None`. Gemma
4 inverts the usual sense: with `enable_thinking` false, the template default,
it pre-fills an empty closed thought block into the generation prompt, which
actively suppresses reasoning. The model then reasons inline in the content
and `message.reasoning` stays empty. Its configs therefore check reasoning
with `enable-thinking`, and its entries declare none. Sending
`chat_template_kwargs: {"enable_thinking": true}` produces reasoning normally,
which is verifiable with curl but is not something this provider path sends.

The field is `reasoning`: vLLM 0.26 renamed it from `reasoning_content`, and
the older name silently yields no reasoning here. Verified against the live
streaming deltas, which carry `reasoning`.

## Layout

| File | Purpose |
| -- | -- |
| `lib.sh` | Shared paths and helpers (sourced, not executed) |
| `start.sh` | Foreground launcher; reads `models/<name>.conf` |
| `run.sh` | Detached launcher; waits for readiness |
| `stop.sh` | Stop by pidfile; verifies VRAM released |
| `status.sh` | Process, GPU, backend, KV cache, liveness probe |
| `bench.py` | AuditBench v1 runtime adapter |
| `models/*.conf` | Per-model settings |

Runtime state (pidfile, log) lives in
`${XDG_STATE_HOME:-~/.local/state}/vllm/`, never in the repo.

Agent-facing invariants and the "where to change what" map are in
[AGENTS.md](AGENTS.md); the measured performance baselines for both GPU
generations are in [BENCHMARKS.md](BENCHMARKS.md).

## Prerequisites

- `vllm`, found in this order: the `VLLM_BIN` override, a `venv/` beside these
  scripts, then PATH. PATH is whatever the host provides, typically a uv tool
  wrapper; the venv is the portable route for
  hosts without it, created by `make vllm-remote-bootstrap`. First install pulls
  roughly 10 GB of torch and CUDA wheels either way.
- A CUDA toolkit only for the FlashInfer backend, which the launcher selects
  solely when fp8 KV is in play. `CUDA_HOME` comes from the host environment;
  without it the launcher falls back to Triton. Host provisioning (toolkit
  install, driver notes) is documented in [AGENTS.md](AGENTS.md).
- For gated models, `hf auth login` plus accepting the model's terms.

## Host tuning notes

Nothing hardware-dependent lives in a model config. The launcher reads compute
capability and total VRAM, then derives the attention backend, KV dtype and
memory policy; the environment still overrides any of it. A model config
carries only portable facts: repo id, served name, native context length, KV
preference, and parsers.

### Host profiles

Two memory profiles, split at 24 GiB of VRAM, each measured rather than
guessed:

| | Small card (< 24 GiB) | Large card (>= 24 GiB) |
| -- | -- | -- |
| `--gpu-memory-utilization` | `(total - 1024 MiB) / total` | 0.98 |
| `--max-num-seqs` | 2 | 8 |
| `--max-num-batched-tokens` | 2048 | 8192 |
| `PYTORCH_CUDA_ALLOC_CONF` | `expandable_segments:True` | unset (see below) |

A small card is told how much of itself to leave alone, as an absolute reserve
rather than a fraction, because what has to be left behind is a fixed quantity
-- a display, a compositor, another process -- not a proportion of the card. A
fraction tuned on 12 GB is wrong on 10 GB and wrong again on 16 GB. The default
1024 MiB resolves to 0.916 on a 12,227 MiB card, 0.900 on 10,240 MiB and 0.938
on 16,384 MiB; raise `VLLM_VRAM_RESERVE_MIB` on a host whose display lives on
this GPU. A dedicated large card is the opposite case, and surplus KV converts
directly into concurrent sequences.

This replaced a flat 0.80 with `max-num-seqs` 1, which was the one memory figure
here with no measured refusal behind it. Both parts cost real capability on
`qwen3.5-4b-awq`: 0.80 could not hold that model's native 262,144 context at all
(4.06 GiB of KV needed, 3.17 GiB offered), and `max-num-seqs` 1 forfeited a ~2x
aggregate decode gain that two streams deliver and four do not improve on. The
measurements are in [BENCHMARKS.md](BENCHMARKS.md#small-card).

### Capability gating

Two hardware gates, both established by measured refusals rather than
documentation:

**fp8 KV needs sm_89+.** A model config asks for fp8 as a *preference*; below
sm_89 the launcher downgrades to bf16 and says so, rather than failing. On
A100 (sm_80) both usable backends refuse it outright:

```text
FLASH_ATTN : not valid for this configuration ... kv_cache_dtype not supported
TRITON_ATTN: FP8 KV cache is not supported ... native FP8 (fp8e4nv) requires SM89+
```

The downgrade can make a long context stop fitting, since vLLM requires KV for
one whole `max-model-len` sequence. That is why the note is printed.

**FlashInfer needs sm_89+ too**, beyond just having `nvcc`. Its kernels fail to
compile for arch 80 even with a working toolkit, erroring inside
`libcudacxx`/`cooperative_groups`. Its sampler is a separate JIT entry point
with the same problem, so the launcher also sets
`VLLM_USE_FLASHINFER_SAMPLER=0` below sm_89 -- otherwise engine init dies for
no benefit even when attention uses another backend.

With bf16 KV the launcher picks `FLASH_ATTN`, which is prebuilt and needs no
JIT at all.

### The allocator setting is profile-scoped

`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` is set only on the
small-card profile. At 0.98 utilization it is actively harmful: memory
profiling sizes the KV cache successfully, then allocation dies in
`_allocate_kv_cache_tensors` with roughly 1.6 GiB "reserved but unallocated".
Measured on A100: 0.98 works without it and OOMs with it. Note the OOM message
itself recommends the flag, which is how it got applied globally in the first
place.

### fp8 KV preserves 131k concurrency

KV cache cost for `qwen3.5-4b-awq` is 8 attention layers x 4 KV heads x 256
head dim x 2 (K and V) = **32 KiB per token** at bf16. A full 131,072-token
sequence therefore needs 4.06 GiB, while the old 0.80 small-card profile
offered 3.17 GiB after weights and CUDA graphs. `--kv-cache-dtype fp8` halves
that to 2.03 GiB and lets the current default preserve two concurrent
131,072-token sequences. Its native 262,144 context still needs 4.06 GiB at
fp8 and was verified only at utilization 0.92 or higher.

vLLM refuses to start if the KV cache cannot hold one whole `max-model-len`
sequence, so this is the binding constraint on the card, not a preference.

### fp8 KV forces the attention backend

With fp8 KV on sm_120 the only candidates are FlashInfer and Triton, because
FlashAttention has no fp8 KV path. vLLM prefers FlashInfer, which JIT-compiles
its kernels and so needs `nvcc`; Triton is the no-toolkit fallback. Benchmark
the affected model before claiming a throughput change, especially for
single-stream decode where backend changes may be hidden by memory bandwidth.

`start.sh` picks FlashInfer only when fp8 KV is in use and the GPU is sm_89 or
newer; otherwise Triton (fp8 KV, no toolkit) or FlashAttention (bf16 KV).

### Some models select their own backend

Which attention backends are legal depends on the model's architecture as much
as on the GPU, and `start.sh` deliberately does not read `config.json` to find
out. Such a model's config sets `VLLM_ATTN_AUTO=1`, `start.sh` then passes no
`--attention-backend` at all, and vLLM's own capability-aware priority list
chooses. Two live cases, from different causes:

- `glm4.7-flash-awq` uses multi-head latent attention, which draws from a
  disjoint family (`FLASH_ATTN_MLA`, `FLASHMLA`, `FLASHINFER_MLA`,
  `TRITON_MLA`) whose membership varies by compute capability just like the
  dense one. Its config sets `VLLM_MLA=1`, which implies `VLLM_ATTN_AUTO`.
- `gemma4-26b-a4b-awq` is multimodal and uses PrefixLM bidirectional attention
  over the image prefix. That needs a backend implementing `mm_prefix`:
  `TRITON_ATTN` does unconditionally, while `FLASH_ATTN` requires
  FlashAttention v4, which does not resolve at this model's 256 head size.

This is not a preference. A backend named explicitly is raised rather than
skipped when it fails, so a wrong guess aborts engine init instead of falling
back:

```text
ValueError: Selected backend AttentionBackendEnum.FLASH_ATTN is not valid for
this configuration. Reason: ['MLA not supported']

ValueError: Selected backend AttentionBackendEnum.FLASH_ATTN is not valid for
this configuration. Reason: ['partial multimodal token full attention not
supported', 'mm_prefix (PrefixLM bidirectional attention) requires
FlashAttention v4, which does not resolve for this head_size']
```

On the A100 the point is not academic in either case: MLA there has exactly
one legal backend, `Using TRITON_MLA attention backend out of potential
backends: ['TRITON_MLA']`, and Gemma 4 lands on `TRITON_ATTN`.

The `host:` line reports `backend vllm-selected` in this case; the backend
actually chosen appears in vLLM's own `Using ... backend.` log line and in
`make vllm-status`.

Deferring is not free for Gemma 4 -- `TRITON_ATTN` gives it the fastest decode
of the five A100 models and the slowest long prefill, roughly half the
FlashAttention rate. That is a property of the model, not a choice available
to the launcher.

MLA also costs memory that startup profiling does not see. Its chunked-prefill
context workspace is allocated on the first prefill long enough to need
chunking, so a server that started cleanly at 0.98 utilization dies later, on a
long prompt, with an OOM that takes the whole engine down. `start.sh` therefore
caps utilization at 0.92 for MLA models unless you pin it yourself. The KV pool
is still 5.28x a full-length sequence at that budget, so nothing addressable is
lost.

### Memory footprint is the budget

vLLM preallocates the KV cache as a single tensor sized to fill whatever
budget `--gpu-memory-utilization` allows, so the budget *is* the footprint; it
never grows on demand. Budget converts to pool very nearly 1:1 -- measured on
`qwen3.5-4b-awq`, raising utilization from 0.92 to 0.958 offered 0.45 GiB more
and the pool took 0.44 GiB of it.

That is why the small-card default is now a reserve rather than a fraction. At
the old 0.80, `qwen3.5-4b-awq` got 200,704 KV tokens but admitted only one
sequence. At the derived 0.916 it gets 274,432 tokens (2.09x the configured
context), enough for the two concurrent sequences the profile now allows.

Sizing the cache directly with `--num-gpu-blocks-override` does not work
here: the block size is not 16, so 8192 blocks requested a 16.25 GiB
allocation and OOM'd. Bound it via the budget instead.

### max-num-batched-tokens guards startup

The startup memory-profiling pass batches this many tokens in one forward. At
the default, which tracks `max-model-len`, the logits tensor alone (vocab
100352) exhausts the card before the KV cache is allocated. 2048 also enables
chunked prefill, which is what makes a 128k prompt feasible at all.

## Output parsing

vLLM has no auto-detection for reasoning or tool-call parsers -- there is no
default and it does not inspect the chat template. Both must be named
explicitly, per model.

For `qwen3.5-4b-awq` the chat template pre-opens a `<think>` block in the
generation prompt, so output is reasoning, then `</think>`, then the answer.
Unparsed, that closing tag leaks into `message.content`. The `qwen3` parser
puts the reasoning in `message.reasoning`; that field was renamed from
`reasoning_content` in vLLM 0.26.

`qwen3_xml` matches the template's XML tool dialect, so tool calls arrive as a
structured `tool_calls` array.

## Adding a model

Copy an existing config and adjust:

```bash
cp models/qwen3.5-4b-awq.conf models/my-model.conf
make vllm-start MODEL=my-model
```

What needs checking per model:

- `VLLM_MAX_LEN` -- omit to accept the model's own maximum. vLLM reads it from
  `config.json`.
- Whether fp8 KV is needed: compute KV bytes per token from
  `num_hidden_layers`, `num_key_value_heads`, and
  `hidden_size / num_attention_heads`, multiply by context length, and compare
  against VRAM minus weight size.
- Both parsers, which have to be looked up rather than derived. Leave them
  empty and the server still works, just with tags left in the content.
- Whether attention is MLA (`kv_lora_rank` in `config.json`). If so set
  `VLLM_MLA=1`, and size the cache as
  `layers x (kv_lora_rank + qk_rope_head_dim) x 2 B` per token rather than by
  KV heads.

Three cases the memory arithmetic above does **not** cover. Hybrid models
store recurrent state per sequence rather than per token, so the formula is
wrong rather than merely imprecise -- `qwen3.6-35b-a3b-awq` is one, at
31.4 MiB per sequence across its 30 GatedDeltaNet layers, while
`qwen3.5-4b-awq` uses about 48 MiB across 24 such layers. Sliding-window layers
cap their cache at the window instead of growing with the sequence, so counting
all layers overstates them badly --
`gemma4-26b-a4b-awq` pays for 5 of its 30 layers per token and a fixed
0.2 GiB for the other 25. Quantized checkpoints (AWQ, GPTQ,
compressed-tensors) change both weight size and which backends are legal.

## Signal handling

Two traps worth knowing, both encoded in the scripts:

`nohup` is not enough to detach. It only ignores SIGHUP, so a Ctrl-C in the
invoking shell sends SIGINT to the whole foreground process group and kills a
merely-backgrounded server mid-startup. `run.sh` uses `setsid` to move the
server into its own session.

`pkill -f` cannot be used to stop the server. The pattern appears in the
command line of any shell that mentions it, including the shell running the
kill, so `pkill` matches and kills the caller. `stop.sh` targets the pid
recorded by `start.sh` instead, then verifies via `nvidia-smi` that VRAM was
actually released -- an orphaned EngineCore holds memory and breaks the next
start.
