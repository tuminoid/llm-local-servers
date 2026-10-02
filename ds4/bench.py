#!/usr/bin/env python3
"""Run AuditBench v2 against the managed ds4-server."""

import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.request

from audit_bench import OpenAIChatAdapter, Settings, openai_chat_fn, run_benchmark

ROOT = pathlib.Path(__file__).resolve().parent
KEYS = ("DS4_COMMIT", "DS4_PORT", "DS4_PIDFILE", "DS4_SERVED_NAME",
        "DS4_MODEL_REPO", "DS4_MODEL_REVISION", "DS4_MODEL_FILE", "DS4_MODEL_SHA256",
        "DS4_CTX", "DS4_SAMPLING", "DS4_CAP_REASONING", "DS4_CAP_TOOLS",
        "DS4_CAP_REASONING_MODE", "DS4_CAP_DISABLE_MODE", "DS4_CAP_SYSTEM_PROMPT")


def config(tag):
    conf = ROOT / "models" / f"{tag}.conf"
    if not conf.is_file():
        raise ValueError(f"unknown model config {tag}")
    # lib.sh first, so its defaults resolve exactly as the launcher's do.
    printers = "".join(f'printf "%s\\0" "${{{key}:-}}"\n' for key in KEYS)
    done = subprocess.run(
        ["bash", "-c", f'set -euo pipefail\nsource "$1"\nsource "$2"\n{printers}',
         "bash", str(ROOT / "lib.sh"), str(conf)],
        capture_output=True, check=False)
    if done.returncode:
        raise RuntimeError(f"failed to resolve {conf}: {done.stderr.decode().strip()}")
    return conf, dict(zip(KEYS, done.stdout.decode().split("\0")))


def evidence(tag):
    """Tie the live server to the pidfile, the pinned GGUF and the served id."""
    conf, values = config(tag)
    gguf = subprocess.run(
        ["bash", "-c", 'source "$1"; source "$2"; ds4_gguf', "bash",
         str(ROOT / "lib.sh"), str(conf)],
        capture_output=True, text=True, check=False)
    if gguf.returncode:
        raise RuntimeError(gguf.stderr.strip())
    pidfile = pathlib.Path(values["DS4_PIDFILE"])
    if not pidfile.exists():
        raise RuntimeError("no managed ds4 server; run make ds4-start")
    pid = int(pidfile.read_text())
    command = subprocess.run(["ps", "-o", "command=", "-p", str(pid)],
                             capture_output=True, text=True, check=False).stdout.strip()
    if gguf.stdout.strip() not in command:
        raise RuntimeError(f"pid {pid} is not serving {values['DS4_MODEL_FILE']}")
    base = f"http://127.0.0.1:{values['DS4_PORT']}"
    # /v1/models lists compatibility aliases beside the loaded GGUF (V4 Flash
    # also answers as deepseek-v4-pro); the first entry is the loaded model.
    with urllib.request.urlopen(f"{base}/v1/models", timeout=30) as response:
        cards = json.load(response)["data"]
    card = dict(cards[0], aliases=[entry["id"] for entry in cards[1:]])
    if card["id"] != values["DS4_SERVED_NAME"]:
        raise RuntimeError(f"server answers as {card['id']}, the config serves "
                           f"{values['DS4_SERVED_NAME']}")
    match = re.search(r"--batched-session (\d+)", command)
    slots = int(match.group(1)) if match else 1
    identity = {
        "checked": True, "matched": True, "managed_pid": pid,
        "repo": values["DS4_MODEL_REPO"], "revision": values["DS4_MODEL_REVISION"],
        "file": values["DS4_MODEL_FILE"], "sha256": values["DS4_MODEL_SHA256"],
        "source": "HF cache blob name", "live_model": card,
    }
    return conf, values, base, card, command, slots, identity


def main():
    tag = sys.argv[1]
    conf, values, base, card, command, slots, identity = evidence(tag)
    context = int(values["DS4_CTX"])
    # Each session slot preallocates its own full-context KV state.
    pool = context * slots
    os.environ["AUDIT_BENCH_SAMPLING"] = values["DS4_SAMPLING"]
    settings = Settings.from_env()
    timeout = int(os.environ.get("AUDIT_BENCH_TIMEOUT", "7200"))
    model = card["id"]
    return run_benchmark(
        runtime="ds4", tag=tag, model=model, context=context,
        active_slots=slots, kv_pool_tokens=pool,
        request=OpenAIChatAdapter(base, model, timeout,
                                  reasoning_effort=settings.reasoning_effort,
                                  system_prompt=settings.system_prompt),
        openai_chat=openai_chat_fn(f"{base}/v1", model, timeout,
                                   reasoning_effort=settings.reasoning_effort,
                                   system_prompt=settings.system_prompt),
        runtime_metadata={
            "model_identity": identity,
            "runtime_profile": {
                "checked": True, "launcher_lines": [command],
                "configured_context": context, "active_slots": slots,
                "kv_pool_tokens": pool, "capacity_source": "--ctx x --batched-session",
                "capacity_kind": "per-slot preallocated KV state",
                "commit": values["DS4_COMMIT"], "ssd_streaming": "--ssd-streaming" in command,
                "prefix_caching": "live per-slot token prefix" + (
                    " plus disk KV checkpoints" if "--kv-disk-dir" in command else ""),
                "speculative_decoding": "MTP, exact sampling" if "--mtp" in command else False,
            },
        },
        provenance_files={
            "adapter": pathlib.Path(__file__), "model_config": conf,
            "launcher": ROOT / "start.sh", "library": ROOT / "lib.sh",
            "makefile": ROOT.parent / "Makefile",
        },
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        raise SystemExit(f"error: {error}") from error
