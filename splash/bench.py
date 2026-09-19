"""Splash transport and admission evidence for the shared AuditBench v1."""

import json
import os
from pathlib import Path
import shlex
import sys

from audit_bench import OpenAIChatAdapter, Settings, openai_chat_fn, run_benchmark
import runtime


def capacity(status):
    plan = status["memory_plan"]
    budget = plan["budget"]
    if not plan["valid"] or budget["deficit_bytes"]:
        raise RuntimeError("Splash reports an invalid memory plan")
    slots = int(budget["maximum_batch_width"])
    # Virtual KV is sparse, not committed memory. Reserve the native active
    # state cells before admitting a workload; retained cache states can evict.
    available = budget["dynamic_budget_bytes"] - slots * budget["active_state_cell_bytes"]
    extent = budget["kv_extent_pages"]
    pages = max(0, available // budget["kv_page_bytes"] // extent * extent)
    pool = min(budget["kv_virtual_tokens"], pages * budget["kv_page_tokens"])
    if slots <= 0 or pool < status["maximum_context_tokens"]:
        raise RuntimeError("Splash cannot admit one configured full-context request")
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
    owner = json.loads(runtime.PIDFILE.read_text())
    release = runtime.verify_release()
    if owner["release"] != release:
        raise RuntimeError("installed release differs from the running server")
    identity = runtime.verify_model(values)
    base, status = runtime.check_live(values, owner, identity)
    identity.update(checked=True, matched=True, managed_pid=owner["pid"],
                    configured_context=owner["context"], release=release,
                    live_identity=status["identity"])
    return values, owner, base, status, identity


def main():
    tag = sys.argv[1]
    values, owner, base, status, identity = evidence(tag)
    slots, pool = capacity(status)
    settings = Settings.from_env()
    timeout = int(os.environ.get("AUDIT_BENCH_TIMEOUT", "7200"))
    return run_benchmark(
        runtime="splash", tag=tag, model=values["SPLASH_MODEL_REPO"],
        context=status["maximum_context_tokens"], active_slots=slots, kv_pool_tokens=pool,
        request=OpenAIChatAdapter(base, values["SPLASH_MODEL_REPO"], timeout,
                                  reasoning_effort=settings.reasoning_effort,
                                  system_prompt=settings.system_prompt),
        openai_chat=openai_chat_fn(f"{base}/v1", values["SPLASH_MODEL_REPO"], timeout,
                                   reasoning_effort=settings.reasoning_effort,
                                   system_prompt=settings.system_prompt),
        runtime_metadata={
            "model_identity": identity,
            "runtime_profile": {
                "checked": True, "launcher_lines": [shlex.join(owner["command"])],
                "configured_context": owner["context"],
                "active_slots": status["memory_plan"]["budget"]["maximum_batch_width"],
                "benchmark_active_slots": slots, "kv_pool_tokens": pool,
                "capacity_source": "/status.memory_plan.budget",
                "capacity_kind": "sparse virtual KV bounded by dynamic memory minus active state cells",
                "memory_plan": status["memory_plan"], "release": owner["release"],
                "prefix_caching": True, "speculative_decoding": "DFlash 2 defaults",
            },
        },
        provenance_files={
            "adapter": Path(__file__), "lifecycle": runtime.ROOT / "runtime.py",
            "model_config": runtime.config_path(tag),
            "package_manifest": runtime.model_path(values) / "manifest.json",
            "runtime_server": runtime.RELEASE / "server/server.py",
            "launcher": runtime.ROOT / "start.sh", "library": runtime.ROOT / "lib.sh",
            "makefile": runtime.ROOT.parent / "Makefile",
        },
    )


if __name__ == "__main__":
    raise SystemExit(main())
