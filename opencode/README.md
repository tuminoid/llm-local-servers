# opencode providers

Each provider, an access path to one runtime, has a ready opencode config
at `<provider>/opencode.json` in this directory. Start a server from the
repository root, then run opencode in your own project with that file
layered over your settings; opencode merges configs:

```bash
make splash-start MODEL=qwen3.8-27b           # in this repository

export OPENCODE_CONFIG=/path/to/llm-local-servers/opencode/splash/opencode.json
opencode models splash                        # the model ids it offers
opencode                                      # in your project
opencode run -m splash/mlx-community/Qwen3.8-27B-4bit "Summarise the auth flow."
```

- `MODEL` names a config in this repository; the opencode model id is its
  served name. Only the model the server was started with answers.
- To give one project a provider permanently, copy the file to that
  project's root as `opencode.json`.
- Entries with reasoning-effort variants take `opencode run --variant
  <effort>`; no variant leaves the model's default.
- The remote providers need their tunnel running (`make vllm-remote-tunnel`,
  `make ollama-remote-tunnel` or `make strata-remote-tunnel`).
- Do not point `OPENCODE_CONFIG_DIR` at these directories: opencode writes
  its plugin files into that directory.

| Provider | Base URL | Config | Reasoning field |
| -- | -- | -- | -- |
| `vllm` | `http://127.0.0.1:8000/v1` | [vllm/opencode.json](vllm/opencode.json) | `reasoning` |
| `vllm-remote` | `http://127.0.0.1:8001/v1`, `make vllm-remote-tunnel` | [vllm-remote/opencode.json](vllm-remote/opencode.json) | `reasoning` |
| `vllm-metal` | `http://127.0.0.1:8021/v1` | [vllm-metal/opencode.json](vllm-metal/opencode.json) | `reasoning` |
| `splash` | `http://127.0.0.1:8022/v1` | [splash/opencode.json](splash/opencode.json) | `reasoning` |
| `lmstudio` | `http://127.0.0.1:1234/v1` | [lmstudio/opencode.json](lmstudio/opencode.json) | `reasoning_content` |
| `ollama` | `http://127.0.0.1:11434/v1` | [ollama/opencode.json](ollama/opencode.json) | not declared |
| `ollama-mlx` | `http://127.0.0.1:11434/v1` | [ollama-mlx/opencode.json](ollama-mlx/opencode.json) | not declared |
| `ollama-remote` | `http://127.0.0.1:11436/v1`, `make ollama-remote-tunnel` | [ollama-remote/opencode.json](ollama-remote/opencode.json) | not declared |
| `ds4` | `http://127.0.0.1:8023/v1` | [ds4/opencode.json](ds4/opencode.json) | `reasoning_content` |
| `kapitsa` | `http://127.0.0.1:8024/v1` | [kapitsa/opencode.json](kapitsa/opencode.json) | `reasoning_content` |
| `strata` | `http://127.0.0.1:8025/v1` | [strata/opencode.json](strata/opencode.json) | `reasoning_content` |
| `strata-remote` | `http://127.0.0.1:8026/v1`, `make strata-remote-tunnel` | [strata-remote/opencode.json](strata-remote/opencode.json) | `reasoning_content` |

## How the files are generated

`make opencode-config` generates them from the model configs, and
`make test` fails when they are stale, so never edit them by hand.

- Every config of a runtime is a model of each of its providers, except
  that Ollama splits by artifact format: safetensors tags run on the MLX
  runner, which the fleet serves on Apple Silicon only, so they are
  `ollama-mlx` models and stay off `ollama` and `ollama-remote`, which list
  the GGUF configs. The hardware pages under
  [docs/hardware/](../docs/hardware/) list which configs run on which hardware.
- The id is `VLLM_SERVED_NAME`, the `OLLAMA_MODEL` tag, the
  `SPLASH_MODEL_REPO` repository, `DS4_SERVED_NAME`,
  `KAPITSA_SERVED_NAME`, `STRATA_SERVED_NAME`, or for LM Studio the config
  name.
  Configs that share a served id become one model, with the smaller
  context.
- The display name is derived from the config name.
- `limit.context` is the config's launch context, and `limit.output` is
  a quarter of it.
- `reasoning` is declared only where the model reasons with no request
  control, since opencode sends no thinking toggle. `tool_call` follows
  the config's tool expectation.
- Ollama entries declare no reasoning, because the capability check
  verifies Ollama reasoning only on its native API.
- `<PREFIX>_REASONING_EFFORTS` in a config, such as `VLLM_REASONING_EFFORTS`,
  becomes `reasoningEffort` variants on an entry that declares reasoning.
