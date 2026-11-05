"""Strata transport and admission evidence for the shared AuditBench v2."""

import json
import os
from pathlib import Path
import shlex
import sys

from audit_bench import OpenAIChatAdapter, Settings, openai_chat_fn, run_benchmark
import runtime


def capacity(owner, health):
    """Slots from the launch; each slot holds one full-context session, so the
    KV pool is slots times the context, never shared between them."""
    slots = int(owner["run_config"]["parallel"])
    pool = slots * int(health["max_context"])
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
        raise RuntimeError("no managed Strata server; run make strata-start")
    owner = json.loads(runtime.PIDFILE.read_text())
    receipt = runtime.verify_source()
    if owner["receipt"] != receipt:
        raise RuntimeError("installed engine differs from the running server")
    identity = runtime.verify_model(values)
    base, health = runtime.check_live(values, owner, identity)
    identity = {**identity, "checked": True, "matched": True, "managed_pid": owner["pid"],
                "configured_context": health["max_context"], "receipt": receipt}
    return values, owner, base, health, identity


def main():
    tag = sys.argv[1]
    values, owner, base, health, identity = evidence(tag)
    # The capability gate runs on any profile; a serving result needs every
    # routed expert on the GPU.
    residency = owner.get("residency") or {}
    if residency.get("experts") is None or residency["experts_in_vram"] != residency["experts"]:
        raise RuntimeError(f"routed experts are not all in VRAM ({residency}); "
                           "a run with experts on the CPU is not a GPU serving result")
    slots, pool = capacity(owner, health)
    model = values["STRATA_SERVED_NAME"]
    # The checkpoint's sampling, a model fact; the harness decodes at it.
    os.environ["AUDIT_BENCH_SAMPLING"] = values["STRATA_SAMPLING"]
    settings = Settings.from_env()
    timeout = int(os.environ.get("AUDIT_BENCH_TIMEOUT", "7200"))
    return run_benchmark(
        runtime="strata", tag=tag, model=model,
        context=health["max_context"], active_slots=slots, kv_pool_tokens=pool,
        request=OpenAIChatAdapter(base, model, timeout, reasoning_effort=settings.reasoning_effort,
                                  system_prompt=settings.system_prompt),
        openai_chat=openai_chat_fn(f"{base}/v1", model, timeout,
                                   reasoning_effort=settings.reasoning_effort,
                                   system_prompt=settings.system_prompt),
        runtime_metadata={
            "model_identity": identity,
            "runtime_profile": {
                "checked": True, "launcher_lines": [shlex.join(owner["command"])],
                "engine_args": owner["run_config"]["args"], "configured_context": health["max_context"],
                "active_slots": owner["run_config"]["parallel"], "benchmark_active_slots": slots,
                "kv_pool_tokens": pool, "capacity_source": "run config parallel; /health max_context",
                "capacity_kind": "one full-context session per slot",
                "expert_residency": owner["residency"], "receipt": owner["receipt"],
                "prefix_caching": True,
            },
        },
        provenance_files={
            "adapter": Path(__file__), "lifecycle": runtime.ROOT / "runtime.py",
            "model_config": runtime.config_path(tag), "launcher": runtime.ROOT / "start.sh",
            "library": runtime.ROOT / "lib.sh",
        },
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        raise SystemExit(f"error: {error}") from error
