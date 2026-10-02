#!/usr/bin/env python3
"""Capability Check v2 against the managed ds4-server."""

import os
import sys

from capability_check import (
    CapabilityConfig, OpenAIChatAdapter, parse_sampling, run_capability_check,
    setup_failure,
)
import bench


def control(mode):
    # ds4 reads a top-level thinking object; chat_template_kwargs is skipped.
    if mode == "default":
        return {}
    if mode == "thinking-disabled":
        return {"thinking": {"type": "disabled"}}
    raise ValueError(f"unsupported ds4 thinking control: {mode}")


def main():
    tag = sys.argv[1]
    model = None
    try:
        _conf, values, base, card, _command, slots, identity = bench.evidence(tag)
        model = card["id"]
        timeout = int(os.environ.get("CAPABILITY_TIMEOUT", "600"))
        return run_capability_check(
            runtime="ds4", tag=tag, model=model,
            adapter=OpenAIChatAdapter(base, model, timeout),
            config=CapabilityConfig(
                reasoning=values["DS4_CAP_REASONING"], tools=values["DS4_CAP_TOOLS"],
                reasoning_options=control(values["DS4_CAP_REASONING_MODE"]),
                disable_options=control(values["DS4_CAP_DISABLE_MODE"]),
                system_prompt=values["DS4_CAP_SYSTEM_PROMPT"] or None,
                sampling=parse_sampling(values["DS4_SAMPLING"]),
                concurrency=slots,
            ),
            identity=identity,
            timeout_tokens=int(os.environ.get("CAPABILITY_REASONING_TOKENS", "2048")),
        )
    except Exception as error:
        return setup_failure(runtime="ds4", tag=tag, model=model, error=error)


if __name__ == "__main__":
    raise SystemExit(main())
