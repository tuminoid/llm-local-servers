#!/usr/bin/env python3
"""Run capability-v2 against the managed Ollama server."""

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
from capability_check import (
    CapabilityConfig,
    OllamaChatAdapter,
    parse_sampling,
    ollama_control,
    resolve_shell_config,
    run_capability_check,
    setup_failure,
)


class InlineReasoningAdapter(OllamaChatAdapter):
    """Resends prior reasoning inside content; see bench.inline_reasoning."""

    def chat(self, messages: list[dict], **kwargs):
        return super().chat(
            benchmark_adapter.inline_reasoning(messages, self.reasoning_field), **kwargs
        )


def _managed_pid() -> int:
    state_root = pathlib.Path(
        os.environ.get("XDG_STATE_HOME", pathlib.Path.home() / ".local" / "state")
    )
    state_dir = pathlib.Path(
        os.environ.get("OLLAMA_STATE_DIR", state_root / "ollama")
    )
    pidfile = pathlib.Path(
        os.environ.get("OLLAMA_PIDFILE", state_dir / "server.pid")
    )
    try:
        pid = int(pidfile.read_text(encoding="utf-8").strip())
        os.kill(pid, 0)
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"managed Ollama pidfile has no live process: {pidfile}") from exc
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
                "OLLAMA_MODEL",
                "OLLAMA_CAP_REASONING",
                "OLLAMA_CAP_TOOLS",
                "OLLAMA_CAP_REASONING_MODE",
                "OLLAMA_CAP_DISABLE_MODE",
                "OLLAMA_CAP_SYSTEM_PROMPT",
                "OLLAMA_SAMPLING",
                "OLLAMA_PRESERVE_REASONING",
                "OLLAMA_CONTEXT_LENGTH",
            ),
        )
        model = values["OLLAMA_MODEL"]
        reasoning_options, reasoning_prefix = ollama_control(
            values["OLLAMA_CAP_REASONING_MODE"]
        )
        disable_options, disable_prefix = ollama_control(
            values["OLLAMA_CAP_DISABLE_MODE"]
        )
        config = CapabilityConfig(
            reasoning=values["OLLAMA_CAP_REASONING"],
            tools=values["OLLAMA_CAP_TOOLS"],
            reasoning_options=reasoning_options or {},
            disable_options=disable_options,
            reasoning_prefix=reasoning_prefix,
            disable_prefix=disable_prefix,
            system_prompt=values["OLLAMA_CAP_SYSTEM_PROMPT"] or None,
            sampling=parse_sampling(values["OLLAMA_SAMPLING"]),
            preserve_reasoning=values["OLLAMA_PRESERVE_REASONING"] == "1",
            context=int(values["OLLAMA_CONTEXT_LENGTH"]),
        )
        timeout = int(os.environ.get("CAPABILITY_TIMEOUT", "600"))
        tokens = int(os.environ.get("CAPABILITY_REASONING_TOKENS", "2048"))
        base = benchmark_adapter.BASE
        managed_pid = _managed_pid()
        identity = benchmark_adapter.verified_identity(
            model, benchmark_adapter._identity_expectations(conf)
        )
        inline = benchmark_adapter._config_setting(conf, "OLLAMA_REASONING_INLINE") == "1"
        adapter = (InlineReasoningAdapter if inline else OllamaChatAdapter)(
            base, model, timeout
        )
        preload_messages = []
        if config.system_prompt:
            preload_messages.append(
                {"role": "system", "content": config.system_prompt}
            )
        preload_messages.append({"role": "user", "content": "Reply with ok."})
        adapter.chat(
            preload_messages,
            max_tokens=256,
            stream=False,
            options=(
                config.disable_options
                if config.disable_options is not None
                else config.reasoning_options
            ),
        )
        residency = benchmark_adapter._residency(model, identity)
        runner, effective_slots = benchmark_adapter._effective_runner()
        benchmark_adapter._validate_runner(identity, runner)
        identity = {
            **identity,
            "runner": runner,
            "effective_slots": effective_slots,
            "loaded_digest": residency["digest"],
            "managed_pid": managed_pid,
            "reasoning_inline": inline,
        }
        return run_capability_check(
            runtime="ollama",
            tag=tag,
            model=model,
            adapter=adapter,
            config=replace(config, concurrency=effective_slots),
            identity=identity,
            timeout_tokens=tokens,
        )
    except Exception as exc:
        return setup_failure(runtime="ollama", tag=tag, model=model, error=exc)


if __name__ == "__main__":
    sys.exit(main())
