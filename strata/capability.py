"""Capability Check v2 against the owned, pinned Strata server."""

import os
import sys

from capability_check import (
    CapabilityConfig, OpenAIChatAdapter, openai_control, parse_sampling,
    run_capability_check, setup_failure,
)
import bench


def control(mode):
    # Strata reads chat_template_kwargs (enable_thinking, reasoning_effort).
    options, prefix = openai_control(mode)
    if prefix or options is None:
        raise ValueError(f"unsupported Strata thinking control: {mode}")
    return options


def main():
    tag = sys.argv[1]
    model = None
    try:
        values, owner, base, health, identity = bench.evidence(tag)
        model = values["STRATA_SERVED_NAME"]
        timeout = int(os.environ.get("CAPABILITY_TIMEOUT", "600"))
        return run_capability_check(
            runtime="strata", tag=tag, model=model,
            adapter=OpenAIChatAdapter(base, model, timeout),
            config=CapabilityConfig(
                reasoning=values["STRATA_CAP_REASONING"], tools=values["STRATA_CAP_TOOLS"],
                reasoning_options=control(values["STRATA_CAP_REASONING_MODE"]),
                disable_options=control(values["STRATA_CAP_DISABLE_MODE"]),
                system_prompt=values["STRATA_CAP_SYSTEM_PROMPT"] or None,
                sampling=parse_sampling(values["STRATA_SAMPLING"]),
                concurrency=bench.capacity(owner, health)[0],
                context=int(health["max_context"]),
            ),
            identity=identity,
            timeout_tokens=int(os.environ.get("CAPABILITY_REASONING_TOKENS", "2048")),
        )
    except Exception as error:
        return setup_failure(runtime="strata", tag=tag, model=model, error=error)


if __name__ == "__main__":
    raise SystemExit(main())
