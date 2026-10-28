"""Capability Check v2 against the owned, pinned Kapitsa server."""

import os
import sys

from capability_check import (
    CapabilityConfig, OpenAIChatAdapter, openai_control, parse_sampling,
    run_capability_check, setup_failure,
)
import bench


def control(mode):
    # Kapitsa renders the chat template with chat_template_kwargs, as vLLM.
    options, prefix = openai_control(mode)
    if prefix or options is None:
        raise ValueError(f"unsupported Kapitsa thinking control: {mode}")
    return options


def main():
    tag = sys.argv[1]
    model = None
    try:
        values, _owner, base, entry, identity = bench.evidence(tag)
        model = values["KAPITSA_SERVED_NAME"]
        timeout = int(os.environ.get("CAPABILITY_TIMEOUT", "600"))
        return run_capability_check(
            runtime="kapitsa", tag=tag, model=model,
            adapter=OpenAIChatAdapter(base, model, timeout),
            config=CapabilityConfig(
                reasoning=values["KAPITSA_CAP_REASONING"], tools=values["KAPITSA_CAP_TOOLS"],
                reasoning_options=control(values["KAPITSA_CAP_REASONING_MODE"]),
                disable_options=control(values["KAPITSA_CAP_DISABLE_MODE"]),
                system_prompt=values["KAPITSA_CAP_SYSTEM_PROMPT"] or None,
                sampling=parse_sampling(values["KAPITSA_SAMPLING"]),
                concurrency=bench.capacity(entry)[0],
                context=int(entry["context_length"]),
            ),
            identity=identity,
            timeout_tokens=int(os.environ.get("CAPABILITY_REASONING_TOKENS", "2048")),
        )
    except Exception as error:
        return setup_failure(runtime="kapitsa", tag=tag, model=model, error=error)


if __name__ == "__main__":
    raise SystemExit(main())
