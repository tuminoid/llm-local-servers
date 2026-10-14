"""Generate the opencode provider configs from the model configs.

A provider is an access path to one runtime, and every model config of that
runtime is one of its models. Writes opencode/<provider>/opencode.json per
provider; `make test` fails when they are stale.
"""

import json
import os
from pathlib import Path
import re

from capability_check import resolve_shell_config

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "opencode"
SCHEMA = "https://opencode.ai/config.json"

# Runtime: served-id variable (None: the config name is the id), context
# variable, config prefix, and the response field reasoning streams in. Ollama's
# reasoning is verified only on its native API, so its entries declare none.
RUNTIMES = {
    "vllm": ("VLLM_SERVED_NAME", "VLLM_MAX_LEN", "VLLM", "reasoning"),
    "vllm-metal": ("VLLM_SERVED_NAME", "VLLM_MAX_LEN", "VLLM", "reasoning"),
    "splash": ("SPLASH_MODEL_REPO", "SPLASH_MAX_LEN", "SPLASH", "reasoning"),
    "lmstudio": (None, "LMSTUDIO_CONTEXT", "LMSTUDIO", "reasoning_content"),
    "ollama": ("OLLAMA_MODEL", "OLLAMA_CONTEXT_LENGTH", "OLLAMA", None),
    "ds4": ("DS4_SERVED_NAME", "DS4_CTX", "DS4", "reasoning_content"),
}

# Provider: runtime, display name, base URL on the launcher's default port.
PROVIDERS = {
    "vllm": ("vllm", "vLLM", "http://127.0.0.1:8000/v1"),
    "vllm-remote": ("vllm", "vLLM remote (make vllm-remote-tunnel)",
                    "http://127.0.0.1:8001/v1"),
    "vllm-metal": ("vllm-metal", "vLLM-Metal", "http://127.0.0.1:8021/v1"),
    "splash": ("splash", "Splash", "http://127.0.0.1:8022/v1"),
    "lmstudio": ("lmstudio", "LM Studio", "http://127.0.0.1:1234/v1"),
    "ollama": ("ollama", "Ollama", "http://127.0.0.1:11434/v1"),
    "ollama-remote": ("ollama", "Ollama remote (make ollama-remote-tunnel)",
                      "http://127.0.0.1:11436/v1"),
    "ds4": ("ds4", "ds4 (DwarfStar)", "http://127.0.0.1:8023/v1"),
}

UPPER = re.compile(r"awq|gptq|mlx|gguf|ud|bf16|f16|i?q\d[a-z0-9_]*|(nv|mx)?fp\d+"
                   r"|int\d+|w\d+a\d+|[ae]?\d+(\.\d+)?b")
SPELLING = {"deepseek": "DeepSeek", "dflash2": "DFlash2", "glm5.3": "GLM5.3", "lfm2.5": "LFM2.5",
            "mimo": "MiMo", "optiq": "OptiQ"}


def display(name):
    """Best-effort display name from a config name."""
    return " ".join(SPELLING.get(word) or (word.upper() if UPPER.fullmatch(word)
                                           else word[:1].upper() + word[1:])
                    for word in name.split("-"))


def resolve(conf, names):
    """Config defaults only: an exported variable must not reach the output."""
    saved = {name: os.environ.pop(name) for name in names if name in os.environ}
    try:
        return resolve_shell_config(conf, names)
    finally:
        os.environ.update(saved)


def model(runtime, conf):
    id_var, context_var, prefix, field = RUNTIMES[runtime]
    reasoning, mode, tools, efforts = (f"{prefix}_{name}" for name in (
        "CAP_REASONING", "CAP_REASONING_MODE", "CAP_TOOLS", "REASONING_EFFORTS"))
    values = resolve(conf, tuple(filter(None, (id_var, context_var, reasoning, mode,
                                               tools, efforts))))
    if not values[context_var].isdigit():
        raise RuntimeError(f"{conf.name}: {context_var} is not a token count")
    context = int(values[context_var])
    entry: dict = {"name": display(conf.stem)}
    # opencode sends no thinking toggle, so only a model that reasons by
    # default populates the field.
    declared = field and values[reasoning] == "required" and values[mode] == "default"
    if declared:
        entry.update(reasoning=True, interleaved={"field": field})
    entry["tool_call"] = values[tools] == "required"
    entry["limit"] = {"context": context, "output": context // 4}
    if declared and values[efforts]:
        entry["variants"] = {effort: {"reasoningEffort": effort}
                             for effort in values[efforts].split()}
    return values[id_var] if id_var else conf.stem, entry


def add(models, key, name, entry):
    """Configs sharing a served id are one model: the smallest context, so a
    client never outgrows the server either config started, and the shortest
    config name. Anything else they disagree on is an error."""
    if key not in models:
        models[key] = (name, entry)
        return
    other_name, other = models[key]
    if {**other, "name": None, "limit": None} != {**entry, "name": None, "limit": None}:
        raise RuntimeError(f"{other_name} and {name} serve {key} with different capabilities")
    if (len(name), name) < (len(other_name), other_name):
        other = {**other, "name": entry["name"]}
        other_name = name
    if entry["limit"]["context"] < other["limit"]["context"]:
        other = {**other, "limit": entry["limit"]}
    models[key] = (other_name, other)


def providers():
    catalog = {}
    for runtime in RUNTIMES:
        confs = sorted((REPO / runtime / "models").glob("*.conf"))
        if not confs:
            raise RuntimeError(f"no model configs in {runtime}/models")
        models = {}
        for conf in confs:
            key, entry = model(runtime, conf)
            add(models, key, conf.stem, entry)
        catalog[runtime] = {key: models[key][1] for key in sorted(models)}
    return {pid: {"npm": "@ai-sdk/openai-compatible", "name": name,
                  "options": {"baseURL": url}, "models": catalog[runtime]}
            for pid, (runtime, name, url) in PROVIDERS.items()}


def render(provider):
    return json.dumps({"$schema": SCHEMA, "provider": provider}, indent=2) + "\n"


def files():
    """Path under opencode/ to content, for every generated file."""
    return {f"{pid}/opencode.json": render({pid: provider})
            for pid, provider in providers().items()}


def main():
    for name, text in files().items():
        (OUT / name).parent.mkdir(exist_ok=True)
        (OUT / name).write_text(text)
        print(f"wrote opencode/{name}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        raise SystemExit(f"error: {error}") from error
