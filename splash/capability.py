"""Capability Check v2 against the owned, pinned Splash server."""

import os
import sys

from capability_check import (
    CapabilityConfig, OpenAIChatAdapter, parse_sampling, run_capability_check,
    setup_failure,
)
import bench


def control(mode):
    # Splash accepts reasoning_effort at the top level. The shared OpenAI
    # control maps it to chat_template_kwargs for vLLM, which Splash ignores.
    if mode == "default":
        return {}
    # No documented control: the check records it as unsupported.
    if mode == "none":
        return None
    if mode == "reasoning-effort-none":
        return {"reasoning_effort": "none"}
    raise ValueError(f"unsupported Splash thinking control: {mode}")


def main():
    tag = sys.argv[1]
    model = None
    try:
        values, _owner, base, status, identity = bench.evidence(tag)
        model = values["SPLASH_MODEL_REPO"]
        timeout = int(os.environ.get("CAPABILITY_TIMEOUT", "600"))
        return run_capability_check(
            runtime="splash", tag=tag, model=model,
            adapter=OpenAIChatAdapter(base, model, timeout),
            config=CapabilityConfig(
                reasoning=values["SPLASH_CAP_REASONING"], tools=values["SPLASH_CAP_TOOLS"],
                reasoning_options=control(values["SPLASH_CAP_REASONING_MODE"]),
                disable_options=control(values["SPLASH_CAP_DISABLE_MODE"]),
                system_prompt=values["SPLASH_CAP_SYSTEM_PROMPT"] or None,
                sampling=parse_sampling(values["SPLASH_SAMPLING"]),
                preserve_reasoning=values["SPLASH_PRESERVE_REASONING"] == "1",
                concurrency=bench.capacity(status)[0],
                context=int(status["maximum_context_tokens"]),
            ),
            identity=identity,
            timeout_tokens=int(os.environ.get("CAPABILITY_REASONING_TOKENS", "2048")),
        )
    except Exception as error:
        return setup_failure(runtime="splash", tag=tag, model=model, error=error)


if __name__ == "__main__":
    raise SystemExit(main())
