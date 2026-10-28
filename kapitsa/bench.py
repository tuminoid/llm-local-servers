"""Kapitsa transport and admission evidence for the shared AuditBench v2."""

import json
import os
from pathlib import Path
import shlex
import sys

from audit_bench import OpenAIChatAdapter, Settings, openai_chat_fn, run_benchmark
import runtime


def capacity(entry):
    """Slots from the live model entry; the KV pool is the room the engine
    planned at load, which every slot's conversation draws from."""
    slots, pool = int(entry["slots"]), runtime.kv_room()
    if slots <= 0 or pool < entry["context_length"]:
        raise RuntimeError("Kapitsa cannot admit one configured full-context request")
    for variable, limit in (("AUDIT_BENCH_ACTIVE_SLOTS", slots), ("AUDIT_BENCH_KV_TOKENS", pool)):
        if os.environ.get(variable):
            value = int(os.environ[variable])
            if not 0 < value <= limit:
                raise ValueError(f"{variable} must be positive and no greater than live capacity {limit}")
            if variable.endswith("SLOTS"):
                slots = value
            else:
                pool = value
    return slots, pool


def evidence(tag):
    values = runtime.config(tag)
    if not runtime.PIDFILE.exists():
        raise RuntimeError("no managed Kapitsa server; run make kapitsa-start")
    owner = json.loads(runtime.PIDFILE.read_text())
    release = runtime.verify_release()
    if owner["release"] != release:
        raise RuntimeError("installed release differs from the running server")
    identity = runtime.verify_model(tag, values)
    base, entry = runtime.check_live(tag, values, owner, identity)
    identity = {**identity, "checked": True, "matched": True, "managed_pid": owner["pid"],
                "configured_context": entry["context_length"], "release": release}
    return values, owner, base, entry, identity


def main():
    tag = sys.argv[1]
    values, owner, base, entry, identity = evidence(tag)
    slots, pool = capacity(entry)
    model = values["KAPITSA_SERVED_NAME"]
    # The checkpoint's sampling, a model fact; the harness decodes at it.
    os.environ["AUDIT_BENCH_SAMPLING"] = values["KAPITSA_SAMPLING"]
    settings = Settings.from_env()
    timeout = int(os.environ.get("AUDIT_BENCH_TIMEOUT", "7200"))
    return run_benchmark(
        runtime="kapitsa", tag=tag, model=model,
        context=entry["context_length"], active_slots=slots, kv_pool_tokens=pool,
        request=OpenAIChatAdapter(base, model, timeout, reasoning_effort=settings.reasoning_effort,
                                  system_prompt=settings.system_prompt),
        openai_chat=openai_chat_fn(f"{base}/v1", model, timeout,
                                   reasoning_effort=settings.reasoning_effort,
                                   system_prompt=settings.system_prompt),
        runtime_metadata={
            "model_identity": identity,
            "runtime_profile": {
                "checked": True, "launcher_lines": [shlex.join(owner["command"])],
                "engine_env": owner["engine_env"], "configured_context": entry["context_length"],
                "active_slots": entry["slots"], "benchmark_active_slots": slots,
                "kv_pool_tokens": pool, "capacity_source": "/v1/models slots; launch log KV room",
                "capacity_kind": "KV room shared by the slots' conversations",
                "release": owner["release"], "prefix_caching": True, "disk_prefix_cache": "off",
            },
        },
        provenance_files={
            "adapter": Path(__file__), "lifecycle": runtime.ROOT / "runtime.py",
            "model_config": runtime.config_path(tag), "launcher": runtime.ROOT / "start.sh",
            "library": runtime.ROOT / "lib.sh", "makefile": runtime.ROOT.parent / "Makefile",
        },
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        raise SystemExit(f"error: {error}") from error
