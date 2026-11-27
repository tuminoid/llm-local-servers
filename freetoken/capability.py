"""Capability Check against the owned, pinned FreeToken server."""

import os
import sys

from capability_check import (
    CapabilityConfig, OpenAIChatAdapter, openai_control, parse_sampling,
    run_capability_check, setup_failure,
)
import bench


def control(mode, disable=False):
    # FreeToken renders the GGUF's chat template with chat_template_kwargs.
    # A model with no off switch declares the disable control none.
    options, prefix = openai_control(mode)
    if prefix or (options is None and not disable):
        raise ValueError(f"unsupported FreeToken thinking control: {mode}")
    return options


def main():
    tag = sys.argv[1]
    model = None
    try:
        values, owner, base, identity = bench.evidence(tag)
        model = values["FREETOKEN_SERVED_NAME"]
        timeout = int(os.environ.get("CAPABILITY_TIMEOUT", "600"))
        return run_capability_check(
            runtime="freetoken", tag=tag, model=model,
            adapter=OpenAIChatAdapter(base, model, timeout),
            config=CapabilityConfig(
                reasoning=values["FREETOKEN_CAP_REASONING"], tools=values["FREETOKEN_CAP_TOOLS"],
                reasoning_options=control(values["FREETOKEN_CAP_REASONING_MODE"]),
                disable_options=control(values["FREETOKEN_CAP_DISABLE_MODE"], disable=True),
                system_prompt=values["FREETOKEN_CAP_SYSTEM_PROMPT"] or None,
                sampling=parse_sampling(values["FREETOKEN_SAMPLING"]),
                concurrency=bench.capacity(owner)[0],
                context=int(values["FREETOKEN_CTX"]),
            ),
            identity=identity,
            timeout_tokens=int(os.environ.get("CAPABILITY_REASONING_TOKENS", "2048")),
        )
    except Exception as error:
        return setup_failure(runtime="freetoken", tag=tag, model=model, error=error)


if __name__ == "__main__":
    raise SystemExit(main())
