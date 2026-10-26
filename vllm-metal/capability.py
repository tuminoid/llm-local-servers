#!/usr/bin/env python3
"""Run capability-v2 against the managed vLLM-Metal server."""

import os
import pathlib
import sys
from dataclasses import replace

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
    parse_sampling,
    resolve_shell_config,
    run_capability_check,
    setup_failure,
)


def _managed_pid() -> int:
    state_root = pathlib.Path(
        os.environ.get("XDG_STATE_HOME", pathlib.Path.home() / ".local" / "state")
    )
    pidfile = pathlib.Path(
        os.environ.get(
            "VLLM_METAL_PIDFILE", state_root / "vllm-metal" / "server.pid"
        )
    )
    try:
        pid = int(pidfile.read_text(encoding="utf-8").strip())
        os.kill(pid, 0)
    except (OSError, ValueError) as exc:
        raise RuntimeError(
            f"managed vLLM-Metal pidfile has no live process: {pidfile}"
        ) from exc
    return pid


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
                "VLLM_MODEL_REPO",
                "VLLM_MODEL_REVISION",
                "VLLM_SERVED_NAME",
                "VLLM_MAX_LEN",
                "VLLM_CAP_REASONING",
                "VLLM_CAP_TOOLS",
                "VLLM_CAP_REASONING_MODE",
                "VLLM_CAP_DISABLE_MODE",
                "VLLM_CAP_SYSTEM_PROMPT",
                "VLLM_SAMPLING",
                "VLLM_PRESERVE_REASONING",
            ),
        )
        model = values["VLLM_SERVED_NAME"]
        context = int(values["VLLM_MAX_LEN"])
        reasoning_options, reasoning_prefix = openai_control(
            values["VLLM_CAP_REASONING_MODE"]
        )
        disable_options, disable_prefix = openai_control(
            values["VLLM_CAP_DISABLE_MODE"]
        )
        config = CapabilityConfig(
            reasoning=values["VLLM_CAP_REASONING"],
            tools=values["VLLM_CAP_TOOLS"],
            reasoning_options=reasoning_options or {},
            disable_options=disable_options,
            reasoning_prefix=reasoning_prefix,
            disable_prefix=disable_prefix,
            system_prompt=values["VLLM_CAP_SYSTEM_PROMPT"] or None,
            sampling=parse_sampling(values["VLLM_SAMPLING"]),
            preserve_reasoning=values["VLLM_PRESERVE_REASONING"] == "1",
            context=context,
        )
        timeout = int(os.environ.get("CAPABILITY_TIMEOUT", "600"))
        tokens = int(os.environ.get("CAPABILITY_REASONING_TOKENS", "2048"))
        base = os.environ.get(
            "VLLM_METAL_CAPABILITY_BASE", "http://127.0.0.1:8021"
        )
        managed_pid = _managed_pid()
        download = benchmark_adapter._download_identity(
            benchmark_adapter._model_dir(tag)
        )
        if download["downloaded_revision"] != values["VLLM_MODEL_REVISION"]:
            raise RuntimeError(
                f"downloaded revision is {download['downloaded_revision']}, "
                f"expected {values['VLLM_MODEL_REVISION']}"
            )
        card = openai_model_card(base, timeout)
        if card.get("id") != model:
            raise RuntimeError(f"live model is {card.get('id')}, expected {model}")
        live_context = card.get("max_model_len")
        if live_context is not None and int(live_context) != context:
            raise RuntimeError(
                f"live max_model_len is {int(live_context):,}, "
                f"expected {context:,}"
            )
        log = benchmark_adapter._server_log()
        if not log.is_file():
            raise RuntimeError(f"managed vLLM-Metal log not found: {log}")
        starting_line = benchmark_adapter._last_match(
            r"^(starting .+)$", log.read_text(encoding="utf-8")
        )
        if not starting_line or f'as "{model}"' not in starting_line:
            raise RuntimeError("managed vLLM-Metal launch identity does not match")
        identity = {
            "checked": True,
            "matched": True,
            "source": values["VLLM_MODEL_REPO"],
            "revision": values["VLLM_MODEL_REVISION"],
            "downloaded_revision": download["downloaded_revision"],
            "verified_files": download["verified_files"],
            "served_name": model,
            "configured_context": context,
            "live_max_model_len": live_context,
            "managed_pid": managed_pid,
        }
        return run_capability_check(
            runtime="vllm-metal",
            tag=tag,
            model=model,
            adapter=OpenAIChatAdapter(base, model, timeout),
            # Samples never exceed the slots the launcher admitted.
            config=replace(
                config,
                concurrency=benchmark_adapter._capacity(context, False)[0],
            ),
            identity=identity,
            timeout_tokens=tokens,
        )
    except Exception as exc:
        return setup_failure(
            runtime="vllm-metal", tag=tag, model=model, error=exc
        )


if __name__ == "__main__":
    sys.exit(main())
