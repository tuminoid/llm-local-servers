#!/usr/bin/env python3
"""Run capability-v1 against the managed LM Studio server."""

import os
import pathlib
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
# The shared harness modules (audit_bench, capability_check) resolve via
# PYTHONPATH -- the sibling llm-audit-bench checkout's src/, set by the root
# Makefile -- or, on deployed remote trees, as copies rsynced next to this
# file.

import bench as benchmark_adapter
from audit_bench import openai_model_card
from capability_check import (
    CapabilityConfig,
    OpenAIChatAdapter,
    openai_control,
    resolve_shell_config,
    run_capability_check,
    setup_failure,
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {pathlib.Path(sys.argv[0]).name} <model-config-name>")
    tag = sys.argv[1]
    model = None
    try:
        conf = SCRIPT_DIR / "models" / f"{tag}.conf"
        if not conf.is_file():
            raise RuntimeError(f"no such model config: {conf}")
        values = resolve_shell_config(
            conf,
            (
                "LMSTUDIO_SERVED_NAME",
                "LMSTUDIO_CONTEXT_LENGTH",
                "LMSTUDIO_FORMAT",
                "LMSTUDIO_EXPECTED_QUANTIZATION",
                "LMSTUDIO_EXPECTED_ARCHITECTURE",
                "LMSTUDIO_CAP_REASONING",
                "LMSTUDIO_CAP_TOOLS",
                "LMSTUDIO_CAP_REASONING_MODE",
                "LMSTUDIO_CAP_DISABLE_MODE",
                "LMSTUDIO_CAP_SYSTEM_PROMPT",
            ),
        )
        model = values["LMSTUDIO_SERVED_NAME"]
        context = int(values["LMSTUDIO_CONTEXT_LENGTH"])
        reasoning_options, reasoning_prefix = openai_control(
            values["LMSTUDIO_CAP_REASONING_MODE"]
        )
        disable_options, disable_prefix = openai_control(
            values["LMSTUDIO_CAP_DISABLE_MODE"]
        )
        config = CapabilityConfig(
            reasoning=values["LMSTUDIO_CAP_REASONING"],
            tools=values["LMSTUDIO_CAP_TOOLS"],
            reasoning_options=reasoning_options or {},
            disable_options=disable_options,
            reasoning_prefix=reasoning_prefix,
            disable_prefix=disable_prefix,
            system_prompt=values["LMSTUDIO_CAP_SYSTEM_PROMPT"] or None,
        )
        timeout = int(os.environ.get("CAPABILITY_TIMEOUT", "600"))
        tokens = int(os.environ.get("CAPABILITY_REASONING_TOKENS", "2048"))
        host = os.environ.get("LMSTUDIO_HOST", "127.0.0.1")
        port = os.environ.get("LMSTUDIO_PORT", "1234")
        base = os.environ.get("LMSTUDIO_CAPABILITY_BASE", f"http://{host}:{port}")

        card = openai_model_card(base, timeout)
        if card.get("id") != model:
            raise RuntimeError(f"live model is {card.get('id')}, expected {model}")
        live_context = card.get("max_model_len")
        if live_context is not None and int(live_context) != context:
            raise RuntimeError(
                f"live max_model_len is {int(live_context):,}, expected {context:,}"
            )
        expectations = {
            "format": values["LMSTUDIO_FORMAT"],
            "quantization": values["LMSTUDIO_EXPECTED_QUANTIZATION"],
            "architecture": values["LMSTUDIO_EXPECTED_ARCHITECTURE"],
        }
        loaded = benchmark_adapter._model_identity(model, expectations)
        identity = {
            "checked": True,
            "matched": True,
            "served_name": model,
            "model_key": loaded["model_key"],
            "path": loaded["path"],
            "format": loaded["format"],
            "quantization": loaded["quantization"],
            "architecture": loaded["architecture"],
            "configured_context": context,
            "live_max_model_len": live_context,
        }
        return run_capability_check(
            runtime="lmstudio",
            tag=tag,
            model=model,
            adapter=OpenAIChatAdapter(base, model, timeout),
            config=config,
            identity=identity,
            timeout_tokens=tokens,
        )
    except Exception as exc:
        return setup_failure(runtime="lmstudio", tag=tag, model=model, error=exc)


if __name__ == "__main__":
    sys.exit(main())
