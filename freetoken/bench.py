"""FreeToken transport and admission evidence for the shared AuditBench v3."""

import json
import os
from pathlib import Path
import shlex
import sys

from audit_bench import OpenAIChatAdapter, Settings, openai_chat_fn, run_benchmark
import runtime


def capacity(owner):
    """Admission is the launch's --max-running-requests; the KV pool is what
    FreeToken reports it allocated, shared by the running requests."""
    slots, pool = owner["parallel"], owner["engine"]["kv_pool_tokens"]
    if not pool:
        raise RuntimeError("FreeToken did not report its KV pool; see the server log")
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
        raise RuntimeError("no managed FreeToken server; run make freetoken-start")
    owner = json.loads(runtime.PIDFILE.read_text())
    receipt = runtime.verify_install()
    if owner["receipt"] != receipt:
        raise RuntimeError("installed FreeToken differs from the running server")
    identity = runtime.verify_model(values)
    base = runtime.check_live(values, owner, identity)
    identity = {**identity, "checked": True, "matched": True, "managed_pid": owner["pid"],
                "configured_context": int(values["FREETOKEN_CTX"]), "receipt": receipt}
    return values, owner, base, identity


def main():
    tag = sys.argv[1]
    values, owner, base, identity = evidence(tag)
    slots, pool = capacity(owner)
    model = values["FREETOKEN_SERVED_NAME"]
    context = int(values["FREETOKEN_CTX"])
    # The checkpoint's sampling, a model fact; the harness decodes at it.
    os.environ["AUDIT_BENCH_SAMPLING"] = values["FREETOKEN_SAMPLING"]
    settings = Settings.from_env()
    timeout = int(os.environ.get("AUDIT_BENCH_TIMEOUT", "7200"))
    return run_benchmark(
        runtime="freetoken", tag=tag, model=model,
        context=context, active_slots=slots, kv_pool_tokens=pool,
        request=OpenAIChatAdapter(base, model, timeout, reasoning_effort=settings.reasoning_effort,
                                  system_prompt=settings.system_prompt),
        openai_chat=openai_chat_fn(f"{base}/v1", model, timeout,
                                   reasoning_effort=settings.reasoning_effort,
                                   system_prompt=settings.system_prompt),
        runtime_metadata={
            "model_identity": identity,
            "runtime_profile": {
                "checked": True, "launcher_lines": [shlex.join(owner["command"])],
                "configured_context": context, "active_slots": owner["parallel"],
                "benchmark_active_slots": slots, "kv_pool_tokens": pool,
                "capacity_source": "launch --max-running-requests; server log KV allocation",
                "capacity_kind": "one KV pool shared by the running requests",
                "moe_strategy": owner["engine"]["moe_strategy"], "receipt": owner["receipt"],
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
