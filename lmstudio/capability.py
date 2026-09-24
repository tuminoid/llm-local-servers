"""Capability Check v1 against the owned, pinned LM Studio server."""

import os
import sys

from capability_check import (
    CapabilityConfig, OpenAIChatAdapter, run_capability_check, setup_failure,
)
import bench


def control(mode):
    # LM Studio reads reasoning_effort at the top level. The shared OpenAI
    # control maps it into chat_template_kwargs for vLLM, which LM Studio
    # ignores; "none" declares that the model has no working disable control.
    if mode == "default":
        return {}
    if mode == "reasoning-effort-none":
        return {"reasoning_effort": "none"}
    if mode == "none":
        return None
    raise ValueError(f"unsupported LM Studio thinking control: {mode}")


def main():
    tag = sys.argv[1]
    try:
        values, _owner, base, identity = bench.evidence(tag)
        timeout = int(os.environ.get("CAPABILITY_TIMEOUT", "600"))
        return run_capability_check(
            runtime="lmstudio", tag=tag, model=tag,
            adapter=OpenAIChatAdapter(base, tag, timeout),
            config=CapabilityConfig(
                reasoning=values["LMSTUDIO_CAP_REASONING"], tools=values["LMSTUDIO_CAP_TOOLS"],
                reasoning_options=control(values["LMSTUDIO_CAP_REASONING_MODE"]),
                disable_options=control(values["LMSTUDIO_CAP_DISABLE_MODE"]),
                system_prompt=values["LMSTUDIO_CAP_SYSTEM_PROMPT"] or None,
            ),
            identity=identity,
            timeout_tokens=int(os.environ.get("CAPABILITY_REASONING_TOKENS", "2048")),
        )
    except Exception as error:
        return setup_failure(runtime="lmstudio", tag=tag, model=tag, error=error)


if __name__ == "__main__":
    raise SystemExit(main())
