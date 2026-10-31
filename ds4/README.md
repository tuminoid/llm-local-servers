# ds4 (DwarfStar)

[ds4](https://github.com/antirez/ds4) is a native C/Metal engine for a few
large MoE models. It serves only the GGUFs its project produces. Here it
runs four of them on Apple Silicon for interactive agentic use; Splash
serves Qwen3.8 Flash Next for audits (see [AGENTS.md](AGENTS.md)).

| Config | Model | Disk | Fit on a 128 GB Mac |
| -- | -- | --: | -- |
| `qwen3.8-flash-next-q4` | Qwen3.8 Flash Next, Q4_K + MXFP4 experts | 165.11 GiB | resident, 69.73 GiB; n-gram table read from the file |
| `deepseek-v4-flash-q2` | DeepSeek V4 Flash 0731 (284B-A13B), imatrix Q2 | 80.76 GiB | resident |
| `glm5.3-flash-q2` | GLM 5.3 Flash, imatrix Q2 | 89.88 GiB | resident, tight |
| `deepseek-v4.1-flash-q2` | DeepSeek V4.1 Flash 1017, imatrix Q2 | 340.60 GiB | SSD streaming; Engram tables read from the file |

Measured capabilities, speeds and verdicts are in
[BENCHMARKS.md](BENCHMARKS.md). In short: Qwen3.8 Flash Next is the pick,
V4 Flash works at half its speed, GLM returns tool arguments as strings,
and V4.1 Flash 1017 is usable but slow from SSD. No model enforces a JSON
schema: ds4 does not implement `response_format`.

## Use

```bash
make ds4-install                              # clone and build the pinned commit
make ds4-pull MODEL=qwen3.8-flash-next-q4     # pinned GGUF into the HF cache
make ds4-start MODEL=qwen3.8-flash-next-q4    # port 8023, loopback
make ds4-status
make ds4-stop
```

`ds4-install` clones ds4 into `~/.local/share/ds4/src/<commit>` and builds
it with the Xcode command-line tools. Point `DS4_SRC` at another checkout
of the pinned commit to build there instead; it must be clean.
`make ds4-capability` runs Capability Check v2. `make ds4-bench` exists for
diagnosis only.

From opencode, use the `ds4` provider in
[opencode/ds4/opencode.json](../opencode/ds4/opencode.json); the model id
is the served name, for example `ds4/qwen3.8-flash-next`.

## Knobs

| Variable | Default | Effect |
| -- | -- | -- |
| `DS4_SLOTS` | 1 | Resident sessions (`--batched-session`); each costs its full-context KV |
| `DS4_KV_DISK` | 1 | Disk KV checkpoints; 0 turns them off |
| `DS4_KV_DISK_DIR` | `~/.cache/ds4/kv` | Checkpoint root, one subdirectory per model config |
| `DS4_KV_DISK_MB` | per config | Checkpoint budget per model config |
| `DS4_MTP` | per config | Built-in MTP speculative decoding at exact sampling (Qwen and GLM only) |
| `DS4_TRACE` | unset | Trace file for prompt rendering, cache decisions and tool parsing |
| `DS4_PORT` | 8023 | Loopback port |

Disk checkpoints persist across restarts and contain prompt text; clear
`DS4_KV_DISK_DIR` only with the server stopped. Traces also contain
prompts.
