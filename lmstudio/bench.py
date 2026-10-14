#!/usr/bin/env python3
"""LM Studio transport and admission evidence for the shared AuditBench v2."""

import json
import os
from pathlib import Path
import sys

from audit_bench import OpenAIChatAdapter, Settings, openai_chat_fn, run_benchmark
import runtime


def evidence(tag):
    values = runtime.config(tag)
    if not runtime.RECORD.exists():
        raise RuntimeError("no managed LM Studio server; run make lmstudio-start")
    owner = json.loads(runtime.RECORD.read_text())
    if owner["identifier"] != tag:
        raise RuntimeError(f"the managed server holds {owner['identifier']}, not {tag}")
    engines = runtime.verify_install()
    if runtime.app_version() != owner["app"] or engines[owner["format"]] != owner["engine"]:
        raise RuntimeError("LM Studio or its engine changed since the managed start")
    # LM Studio updates itself, so a measurement runs on what it selected and
    # records how that differs from the measured release.
    drift = runtime.pin_drift(owner["app"], {owner["format"]: owner["engine"]})
    if drift:
        print(f"note: {'; '.join(drift)}; recorded as pin_drift", file=sys.stderr)
    # Serving coexists with the operator's loads; a measurement does not.
    others = [item["identifier"] for item in runtime.loaded() if item["identifier"] != tag]
    if others:
        raise RuntimeError(f"measurements need {tag} alone in LM Studio; also loaded: "
                           f"{', '.join(others)}")
    identity = runtime.verify_model(tag, values)
    base, entry = runtime.check_live(tag, values, owner)
    identity.update(checked=True, matched=True, served_name=tag,
                    configured_context=owner["context"], live_path=entry["path"],
                    live_format=entry["format"], live_context=entry["contextLength"],
                    pin_drift=drift)
    return values, owner, base, identity


def main():
    tag = sys.argv[1]
    values, owner, base, identity = evidence(tag)
    # The MLX engine's usage accounting is one low on length-capped responses
    # (docs/PROTOCOL.md "Off-by-one token accounting"); the config says when.
    if values["LMSTUDIO_BENCH_TOLERATE_OFF_BY_ONE"]:
        os.environ.setdefault("AUDIT_BENCH_TOLERATE_OFF_BY_ONE",
                              values["LMSTUDIO_BENCH_TOLERATE_OFF_BY_ONE"])
    # The checkpoint's sampling, a model fact; the harness decodes at it.
    os.environ["AUDIT_BENCH_SAMPLING"] = values["LMSTUDIO_SAMPLING"]
    settings = Settings.from_env()
    timeout = int(os.environ.get("AUDIT_BENCH_TIMEOUT", "7200"))
    slots = owner["parallel"]
    launcher_lines = [line for line in runtime.LOG.read_text().splitlines()
                      if line.startswith(("config:", "host:", "launch:"))]
    return run_benchmark(
        runtime="lmstudio", tag=tag, model=tag, context=owner["context"],
        active_slots=slots, kv_pool_tokens=owner["context"] * slots,
        request=OpenAIChatAdapter(base, tag, timeout,
                                  reasoning_effort=settings.reasoning_effort,
                                  system_prompt=settings.system_prompt),
        openai_chat=openai_chat_fn(f"{base}/v1", tag, timeout,
                                   reasoning_effort=settings.reasoning_effort,
                                   system_prompt=settings.system_prompt),
        runtime_metadata={
            "model_identity": identity,
            "runtime_profile": {
                "checked": True, "launcher_lines": launcher_lines,
                "configured_context": owner["context"], "active_slots": slots,
                "kv_pool_tokens": owner["context"] * slots,
                "capacity_source": "configured context x active slots",
                "capacity_kind": "LM Studio exposes no KV pool; allocation is per request",
                "lmstudio_version": owner["app"], "engine": owner["engine"],
            },
        },
        provenance_files={
            "adapter": Path(__file__), "lifecycle": runtime.ROOT / "runtime.py",
            "model_config": runtime.config_path(tag),
            "makefile": runtime.ROOT.parent / "Makefile",
        },
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        raise SystemExit(f"error: {error}") from error
